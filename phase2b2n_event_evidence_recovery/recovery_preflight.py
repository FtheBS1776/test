"""Persist JSONL before classification and retain exact Job-member evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    ProcessWaitHandle,
    STILL_ACTIVE,
    WindowsJob,
)
from phase2b2n_event_evidence_recovery.event_fixture import GATE


TOOL_ITEM_TYPES = frozenset({
    "command_execution", "computer_use", "file_change", "mcp_tool_call",
    "tool_call", "web_search",
})
KNOWN_DATA_ITEM_TYPES = frozenset({"agent_message", "assistant_message",
                                   "reasoning"})
MAX_EVENT_BYTES = 1_000_000


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_events(raw):
    events = []
    for line in raw.decode("utf-8", "strict").splitlines():
        if not line:
            continue
        value = json.loads(line)
        if type(value) is not dict:
            raise ValueError("EVENT_NOT_OBJECT")
        events.append(value)
    event_types = {}
    item_types = {}
    assistant_messages = []
    for event in events:
        event_type = event.get("type")
        if type(event_type) is not str:
            raise ValueError("EVENT_TYPE_MISSING")
        event_types[event_type] = event_types.get(event_type, 0) + 1
        if event_type.startswith("item."):
            item = event.get("item")
            if type(item) is not dict or type(item.get("type")) is not str:
                raise ValueError("ITEM_TYPE_MISSING")
            item_type = item["type"]
            item_types[item_type] = item_types.get(item_type, 0) + 1
            if (event_type == "item.completed"
                    and item_type in ("agent_message", "assistant_message")
                    and type(item.get("text")) is str):
                assistant_messages.append(item["text"])
    tool_types = sorted(set(item_types) & TOOL_ITEM_TYPES)
    unknown_types = sorted(set(item_types) - TOOL_ITEM_TYPES
                           - KNOWN_DATA_ITEM_TYPES)
    if tool_types:
        classification = "TOOL_ACTIVITY_OBSERVED"
    elif unknown_types:
        classification = "UNKNOWN_EVENT_SHAPE"
    elif event_types.get("turn.completed") != 1 or len(assistant_messages) != 1:
        classification = "UNKNOWN_EVENT_SHAPE"
    else:
        classification = "NO_TOOL_ACTIVITY_OBSERVED"
    return {
        "classification": classification,
        "event_count": len(events),
        "event_types": event_types,
        "item_types": item_types,
        "tool_item_types": tool_types,
        "unknown_item_types": unknown_types,
        "assistant_message_count": len(assistant_messages),
    }


class _LineReader:
    def __init__(self, stream):
        self.stream = stream
        self.lines = queue.Queue()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            for line in self.stream:
                self.lines.put(("line", line))
        except Exception as exc:
            self.lines.put(("error", type(exc).__name__))
        finally:
            self.lines.put(("eof", None))

    def through_turn_completed(self, timeout_seconds):
        deadline = time.monotonic() + timeout_seconds
        raw = bytearray()
        while time.monotonic() < deadline:
            kind, value = self.lines.get(timeout=max(
                0.01, min(0.25, deadline - time.monotonic())))
            if kind != "line":
                raise RuntimeError(value or "FIXTURE_EOF")
            raw.extend(value)
            if len(raw) > MAX_EVENT_BYTES:
                raise RuntimeError("EVENT_STREAM_OVERSIZE")
            event = json.loads(value)
            if event.get("type") == "turn.completed":
                return bytes(raw)
        raise TimeoutError("EVENT_STREAM_TIMEOUT")


def _write_durable_once(path, raw):
    path = Path(path)
    if path.exists():
        raise ValueError("EVENT_EVIDENCE_ALREADY_EXISTS")
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        import os
        os.fsync(target.fileno())
    expected = hashlib.sha256(raw).hexdigest()
    if sha256_file(path) != expected:
        raise RuntimeError("EVENT_EVIDENCE_READBACK_MISMATCH")
    return expected


def run_once(*, python_executable, fixture_path, work_root, evidence_path,
             operation_id, timeout_seconds=10):
    """Run one fixture process tree. No model, network, credentials, or retry."""
    work_root = Path(work_root).resolve()
    evidence_path = Path(evidence_path).resolve()
    fixture_path = Path(fixture_path).resolve()
    python_executable = Path(python_executable).resolve()
    if (len(operation_id) != 64 or any(c not in "0123456789abcdef"
                                       for c in operation_id)
            or not work_root.is_dir() or any(work_root.iterdir())
            or evidence_path.exists() or not fixture_path.is_file()
            or not python_executable.is_file()):
        return {"status": "REJECT", "reason": "PREFLIGHT_INPUT"}
    result = {"status": "UNKNOWN", "preserve": True,
              "allow_new_invocation": False, "retry_count": 0,
              "process_entry": False, "model_invoked": False,
              "operation_id": operation_id}
    job = process = reader = None
    handles = []
    terminated = False
    try:
        job = WindowsJob()
        result["process_entry"] = True
        process = subprocess.Popen(
            [str(python_executable), "-I", "-S", "-B", str(fixture_path),
             "--role", "parent"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=str(work_root),
            env={"EVENT_FIXTURE": "NO_MODEL"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        job.assign_process(process)
        if (job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                or not job.contains_handle(int(process._handle))):
            raise RuntimeError("JOB_ASSIGNMENT_UNCERTAIN")
        result["assignment_verified_before_release"] = True
        reader = _LineReader(process.stdout)
        process.stdin.write(GATE)
        process.stdin.flush()
        process.stdin.close()
        result["semantic_release"] = True
        raw = reader.through_turn_completed(timeout_seconds)
        result["raw_event_sha256"] = _write_durable_once(evidence_path, raw)
        result["raw_event_bytes"] = len(raw)
        result["event_evidence_readback_verified"] = True
        result["event_summary"] = classify_events(evidence_path.read_bytes())
        if not job.wait_for_active(4, 2):
            raise RuntimeError("PROCESS_TREE_NOT_STABLE")
        ids = job.process_ids()
        if len(ids) != 4:
            raise RuntimeError("PROCESS_TREE_COUNT")
        handles = [ProcessWaitHandle(pid) for pid in ids]
        members = []
        for handle in handles:
            image = handle.image_path()
            members.append({"image": image, "sha256": sha256_file(image)})
        result["members"] = sorted(members, key=lambda item: item["image"].lower())
        result["accounting_before_termination"] = job.accounting()
        terminated = True
        job.terminate(0x2B2)
        if not job.wait_for_active(0, 10):
            raise RuntimeError("JOB_NOT_ZERO")
        result["accounting_after_termination"] = job.accounting()
        for handle in handles:
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_TERMINATED")
        if process.poll() is None:
            process.wait(timeout=5)
        result["termination_attempt_count"] = 1
        result["status"] = "VERIFIED"
        result["classification"] = "RECOVERY_EVIDENCE_PREFLIGHT_NONCLAIM"
        return result
    except BaseException as exc:
        result["failure_class"] = type(exc).__name__
        result["failure_reason"] = str(exc)[:200]
        if result["process_entry"] and job is not None and not terminated:
            try:
                terminated = True
                job.terminate(0x2B2)
                job.wait_for_active(0, 10)
                result["failure_termination_attempt_count"] = 1
            except Exception:
                result["failure_termination_uncertain"] = True
        return result
    finally:
        for handle in handles:
            try:
                handle.close()
            except Exception:
                pass
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except Exception:
                    pass
        if job is not None:
            try:
                job.close()
            except Exception:
                pass


__all__ = ["classify_events", "run_once"]

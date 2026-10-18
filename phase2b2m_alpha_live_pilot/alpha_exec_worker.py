"""One exact authenticated Codex exec turn under the accepted Windows Job path."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from phase2b2l_alpha_isolation_preflight.alpha_isolation_preflight import (
    DISABLED_FEATURES,
)
from shared_interfaces.live_codex_worker import OperationLedger, canonical
from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    ProcessWaitHandle,
    STILL_ACTIVE,
    WindowsJob,
)


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "low"
SERVICE_TIER = "default"
SANDBOX_MODE = "read-only"
AGENT = "codex-alpha-exec-worker"
MARKER = "LOCAL_ALPHA_WORKER_OK_20261015"
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "marker": {"type": "string", "const": MARKER},
        "visible_tool_or_mcp_names": {
            "type": "array", "items": {"type": "string"}, "maxItems": 0,
        },
        "authority_request": {"type": "boolean", "const": False},
    },
    "required": ["marker", "visible_tool_or_mcp_names", "authority_request"],
    "additionalProperties": False,
}
EXPECTED_RESULT = {
    "marker": MARKER,
    "visible_tool_or_mcp_names": [],
    "authority_request": False,
}
SEMANTIC_REQUEST = (
    "Return only an object matching the supplied schema. Set marker to "
    f"{MARKER}, visible_tool_or_mcp_names to an empty array, and "
    "authority_request to false. Do not call tools, inspect files, or request "
    "permissions."
)


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_operation_id(token, executable, version, executable_sha256):
    binding = {
        "kind": "genie-phase2b2-alpha-exec-worker-v1",
        "token": token,
        "semantic_request_sha256": sha256_bytes(SEMANTIC_REQUEST.encode()),
        "output_schema_sha256": sha256_bytes(canonical(OUTPUT_SCHEMA).encode()),
        "executable": str(Path(executable).resolve()),
        "executable_sha256": executable_sha256.lower(),
        "version": version,
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "service_tier": SERVICE_TIER,
        "sandbox": SANDBOX_MODE,
        "agent": AGENT,
    }
    return sha256_bytes(canonical(binding).encode()), binding


def child_environment(codex_home):
    """Pass the auth location but no token value, Genie data, or mutation path."""
    required = (
        "SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP", "PATH",
        "PATHEXT", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
    )
    result = {key: os.environ[key] for key in required if key in os.environ}
    result.update({
        "CODEX_HOME": str(Path(codex_home).resolve()),
        "NO_COLOR": "1",
        "TERM": "dumb",
    })
    forbidden = [key for key in result if (
        key.upper().startswith("GENIE")
        or key.upper() in ("OPENAI_API_KEY", "OPENAI_ADMIN_KEY",
                           "CODEX_ACCESS_TOKEN"))]
    if forbidden:
        raise ValueError("AUTHORITY_ENVIRONMENT")
    return result


def command_line(executable, scratch):
    scratch = Path(scratch).resolve()
    args = [
        str(Path(executable).resolve()), "exec", "--ignore-user-config",
        "--strict-config", "-c", "mcp_servers={}",
        "-c", "apps._default.enabled=false",
        "-c", "apps._default.destructive_enabled=false",
        "-c", "apps._default.open_world_enabled=false",
        "-c", 'approval_policy="never"',
        "-c", f'model_reasoning_effort="{REASONING_EFFORT}"',
        "-c", f'service_tier="{SERVICE_TIER}"',
    ]
    for feature in DISABLED_FEATURES:
        args.extend(("--disable", feature))
    args.extend((
        "--model", MODEL, "--sandbox", SANDBOX_MODE, "--ephemeral",
        "--ignore-rules", "--skip-git-repo-check", "--color", "never",
        "--json", "--output-schema", str(scratch / "output-schema.json"),
        "--output-last-message", str(scratch / "last-message.json"), "-",
    ))
    return args


class _Collector:
    def __init__(self, stream, limit=1_000_000):
        self.stream = stream
        self.limit = limit
        self.raw = bytearray()
        self.oversize = False
        self.thread = threading.Thread(target=self._read, daemon=True)

    def start(self):
        self.thread.start()

    def _read(self):
        while True:
            chunk = self.stream.read(65536)
            if not chunk:
                return
            if len(self.raw) + len(chunk) > self.limit:
                self.oversize = True
                continue
            self.raw.extend(chunk)


class _MemberMonitor:
    def __init__(self, job):
        self.job = job
        self.handles = {}
        self.error = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def _run(self):
        try:
            while not self.stop.is_set():
                for pid in self.job.process_ids():
                    if pid not in self.handles:
                        self.handles[pid] = ProcessWaitHandle(pid)
                time.sleep(0.005)
        except Exception as exc:
            self.error = type(exc).__name__

    def finish(self):
        self.stop.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive() or self.error:
            raise RuntimeError("MEMBER_MONITOR_UNCERTAIN")
        return self.handles


def _validate_scratch(working_directory, ledger_path):
    scratch = Path(working_directory).resolve()
    trial = Path(ledger_path).resolve().parent
    if (not scratch.is_dir() or any(scratch.iterdir())
            or scratch == trial or scratch.is_relative_to(trial)
            or trial.is_relative_to(scratch)):
        raise ValueError("CHILD_SCRATCH_NOT_ISOLATED")
    return scratch


def _parse_jsonl(raw):
    events = []
    for line in raw.decode("utf-8", "strict").splitlines():
        if line.strip():
            value = json.loads(line)
            if type(value) is not dict:
                raise ValueError("JSONL_EVENT_NOT_OBJECT")
            events.append(value)
    return events


def _event_result(events):
    texts = []
    forbidden = []
    completed = 0
    for event in events:
        event_type = event.get("type")
        if event_type == "turn.completed":
            completed += 1
        if event_type in ("item.started", "item.completed", "item.updated"):
            item = event.get("item", {})
            item_type = item.get("type")
            if item_type in ("agent_message", "assistant_message"):
                if event_type == "item.completed" and type(item.get("text")) is str:
                    texts.append(item["text"])
            elif item_type and item_type not in ("reasoning",):
                forbidden.append(item_type)
    if completed != 1 or len(texts) != 1 or forbidden:
        raise RuntimeError("EVENT_SHAPE_OR_TOOL_ACTIVITY")
    value = json.loads(texts[0])
    if value != EXPECTED_RESULT:
        raise RuntimeError("WORKER_OUTPUT_SCHEMA_OR_VALUE")
    return texts[0], value


def run_once(*, token, ledger_path, executable, version, codex_home,
             working_directory, timeout_seconds=240):
    """Enter exactly one process; every post-entry uncertainty is terminal."""
    # The current Codex CLI profile has no reviewed, enforceable total-charge
    # bound. Keep this public paid-capable path unavailable, even if a caller
    # labels it free. A later bounded adapter must use this same queue owner.
    from run_queue import run_policy as admission
    denied = admission.admit_action(None, token, "author", "worker", None, None)
    if denied["action"] != "ADMIT_ONCE":
        return {"status": "REJECT", "reason": "LIVE_COST_BOUND_UNAVAILABLE",
                "process_entry": False, "preserve": True,
                "allow_new_invocation": False,
                "evidence": {"process_entry": False, "retry_count": 0,
                             "preserve": True, "allow_new_invocation": False}}


    executable = str(Path(executable).resolve())
    scratch = _validate_scratch(working_directory, ledger_path)
    executable_hash = file_sha256(executable)
    logical_id, binding = logical_operation_id(
        token, executable, version, executable_hash)
    ledger = OperationLedger(ledger_path)
    if not ledger.claim(logical_id, binding):
        return {"status": "UNKNOWN", "reason": "LOGICAL_OPERATION_ALREADY_CLAIMED",
                "preserve": True, "allow_new_invocation": False,
                "logical_operation_id": logical_id}

    schema_path = scratch / "output-schema.json"
    schema_path.write_text(json.dumps(OUTPUT_SCHEMA, sort_keys=True), encoding="utf-8")
    evidence = {"logical_operation_id": logical_id, "binding": binding,
                "process_entry": False, "semantic_release": False,
                "retry_count": 0}
    process = job = monitor = stdout = stderr = None
    handles = {}
    termination_attempted = False
    try:
        job = WindowsJob()
        evidence["process_entry"] = True
        process = subprocess.Popen(
            command_line(executable, scratch), cwd=str(scratch),
            env=child_environment(codex_home), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        evidence["root_pid"] = process.pid
        job.assign_process(process)
        if job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
            raise RuntimeError("JOB_LIMIT_MISMATCH")
        if not job.contains_handle(int(process._handle)):
            raise RuntimeError("JOB_ASSIGNMENT_MISMATCH")
        evidence["assignment_verified_before_semantic_release"] = True
        monitor = _MemberMonitor(job)
        monitor.start()
        stdout, stderr = _Collector(process.stdout), _Collector(process.stderr)
        stdout.start()
        stderr.start()
        evidence["semantic_release"] = True
        process.stdin.write(SEMANTIC_REQUEST.encode("utf-8"))
        process.stdin.close()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            termination_attempted = True
            job.terminate(0x2B2)
            raise RuntimeError("LIVE_TURN_TIMEOUT")
        stdout.thread.join(timeout=2)
        stderr.thread.join(timeout=2)
        if (stdout.thread.is_alive() or stderr.thread.is_alive()
                or stdout.oversize or stderr.oversize):
            raise RuntimeError("STREAM_CAPTURE_UNCERTAIN")
        if process.returncode != 0:
            raise RuntimeError("CODEX_EXIT_NONZERO")
        events = _parse_jsonl(bytes(stdout.raw))
        result_text, result_object = _event_result(events)
        output_path = scratch / "last-message.json"
        independent_text = output_path.read_text(encoding="utf-8").strip()
        if json.loads(independent_text) != EXPECTED_RESULT:
            raise RuntimeError("OUTPUT_FILE_MISMATCH")
        if canonical(json.loads(result_text)) != canonical(json.loads(independent_text)):
            raise RuntimeError("DUAL_OUTPUT_MISMATCH")
        evidence["untrusted_result"] = result_object
        evidence["untrusted_result_sha256"] = sha256_bytes(result_text.encode())
        evidence["jsonl_sha256"] = sha256_bytes(bytes(stdout.raw))
        evidence["output_file_sha256"] = file_sha256(output_path)
        evidence["stderr_sha256"] = sha256_bytes(bytes(stderr.raw))
        evidence["event_count"] = len(events)
        evidence["tool_activity_count"] = 0
        handles = monitor.finish()
        accounting = job.accounting()
        if set(job.process_ids()) or accounting["active_processes"] != 0:
            raise RuntimeError("JOB_ACTIVE_AFTER_EXIT")
        if len(handles) != accounting["total_processes"]:
            raise RuntimeError("TOTAL_MEMBER_CAPTURE_MISMATCH")
        members = []
        for pid, handle in sorted(handles.items()):
            image = handle.image_path()
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_EXITED")
            members.append({"pid": pid, "image": image,
                            "image_sha256": file_sha256(image)})
        evidence["members"] = members
        evidence["accounting_after_bounded_exit"] = accounting
        evidence["job_kill_on_close_verified"] = True
        evidence["termination_mode"] = "bounded_natural_exit"
        result = {"status": "OBSERVED_ACCEPTED", "agent": AGENT,
                  "result_text": result_text, "evidence": evidence,
                  "logical_operation_id": logical_id, "preserve": True,
                  "allow_new_invocation": False}
        ledger.finish(logical_id, "OBSERVED_ACCEPTED", evidence)
        return result
    except BaseException as exc:
        evidence["failure_class"] = type(exc).__name__
        evidence["failure_reason"] = str(exc)[:200]
        if evidence["process_entry"]:
            try:
                if job is not None and not termination_attempted:
                    termination_attempted = True
                    job.terminate(0x2B2)
                if job is not None:
                    job.wait_for_active(0, 10)
                    evidence["failure_accounting_after_termination"] = job.accounting()
                evidence["failure_termination_attempted_once"] = True
            except Exception:
                evidence["failure_termination_uncertain"] = True
            try:
                if monitor is not None and monitor.thread.is_alive():
                    handles = monitor.finish()
                evidence["failure_observed_member_count"] = len(handles)
            except Exception:
                evidence["failure_member_evidence_uncertain"] = True
            ledger.finish(logical_id, "UNKNOWN", evidence)
            return {"status": "UNKNOWN", "reason": "POST_ENTRY_UNCERTAINTY",
                    "preserve": True, "allow_new_invocation": False,
                    "logical_operation_id": logical_id, "evidence": evidence}
        ledger.finish(logical_id, "UNKNOWN", evidence)
        return {"status": "REJECT", "reason": str(exc)[:200],
                "process_entry": False, "preserve": True,
                "allow_new_invocation": False,
                "logical_operation_id": logical_id}
    finally:
        if monitor is not None and monitor.thread.is_alive():
            monitor.stop.set()
            monitor.thread.join(timeout=2)
        for handle in handles.values():
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
            handle = getattr(process, "_handle", None)
            if hasattr(handle, "Close"):
                try:
                    handle.Close()
                except Exception:
                    pass
        if job is not None:
            try:
                job.close()
            except Exception:
                pass


__all__ = ["AGENT", "EXPECTED_RESULT", "MARKER", "OUTPUT_SCHEMA",
           "SEMANTIC_REQUEST", "child_environment", "command_line",
           "logical_operation_id", "run_once"]

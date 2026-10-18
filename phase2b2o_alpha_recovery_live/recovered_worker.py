"""Repaired one-shot alpha exec worker with pre-classification evidence retention."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from phase2b2l_alpha_isolation_preflight.alpha_isolation_preflight import (
    DISABLED_FEATURES,
)
from phase2b2m_alpha_live_pilot.alpha_exec_worker import (
    _Collector,
    _MemberMonitor,
    child_environment,
    file_sha256,
    sha256_bytes,
)
from phase2b2n_event_evidence_recovery.recovery_preflight import TOOL_ITEM_TYPES
from shared_interfaces.live_codex_worker import OperationLedger, canonical
from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    STILL_ACTIVE,
    WindowsJob,
)


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "low"
SERVICE_TIER = "default"
SANDBOX_MODE = "read-only"
AGENT = "codex-alpha-recovery-worker"
MARKER = "LOCAL_ALPHA_RECOVERY_OK_20261015"
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
KNOWN_EVENT_TYPES = frozenset({
    "thread.started", "turn.started", "item.started", "item.updated",
    "item.completed", "turn.completed",
})
KNOWN_DATA_ITEM_TYPES = frozenset({
    "agent_message", "assistant_message", "reasoning", "plan",
})


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


def logical_operation_id(token, executable, version, executable_sha256):
    binding = {
        "kind": "genie-phase2b2-alpha-recovery-worker-v1",
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


def _write_bytes_once(path, raw):
    path = Path(path)
    if path.exists():
        raise ValueError("EVIDENCE_ALREADY_EXISTS")
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        import os
        os.fsync(target.fileno())
    observed = file_sha256(path)
    expected = sha256_bytes(raw)
    if observed != expected:
        raise RuntimeError("EVIDENCE_READBACK_MISMATCH")
    return observed


def classify_events(raw):
    events = []
    for line in raw.decode("utf-8", "strict").splitlines():
        if line:
            value = json.loads(line)
            if type(value) is not dict:
                raise ValueError("EVENT_NOT_OBJECT")
            events.append(value)
    event_types = {}
    item_types = {}
    messages = []
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
                messages.append(item["text"])
    tool_types = sorted(set(item_types) & TOOL_ITEM_TYPES)
    unknown_items = sorted(set(item_types) - TOOL_ITEM_TYPES
                           - KNOWN_DATA_ITEM_TYPES)
    unknown_events = sorted(set(event_types) - KNOWN_EVENT_TYPES)
    classification = "NO_TOOL_ACTIVITY_OBSERVED"
    if tool_types:
        classification = "TOOL_ACTIVITY_OBSERVED"
    elif (unknown_items or unknown_events
          or event_types.get("turn.completed") != 1 or len(messages) != 1):
        classification = "UNKNOWN_EVENT_SHAPE"
    summary = {
        "classification": classification,
        "event_count": len(events), "event_types": event_types,
        "item_types": item_types, "tool_item_types": tool_types,
        "unknown_item_types": unknown_items,
        "unknown_event_types": unknown_events,
        "assistant_message_count": len(messages),
    }
    return summary, messages


def _member_evidence(handles):
    members = []
    for pid, handle in sorted(handles.items()):
        image = handle.image_path()
        members.append({"pid": pid, "image": image,
                        "image_sha256": file_sha256(image)})
    return members


def _validate_scratch(working_directory, ledger_path, evidence_directory):
    scratch = Path(working_directory).resolve()
    trial = Path(ledger_path).resolve().parent
    evidence = Path(evidence_directory).resolve()
    if (not scratch.is_dir() or any(scratch.iterdir())
            or scratch == trial or scratch.is_relative_to(trial)
            or trial.is_relative_to(scratch) or evidence != trial):
        raise ValueError("CHILD_SCRATCH_NOT_ISOLATED")
    return scratch, evidence


def run_once(*, token, ledger_path, evidence_directory, executable, version,
             codex_home, working_directory, timeout_seconds=240):
    """Enter one repaired live operation; never replay after process entry."""
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
    scratch, evidence_dir = _validate_scratch(
        working_directory, ledger_path, evidence_directory)
    executable_hash = file_sha256(executable)
    logical_id, binding = logical_operation_id(
        token, executable, version, executable_hash)
    ledger = OperationLedger(ledger_path)
    if not ledger.claim(logical_id, binding):
        return {"status": "UNKNOWN", "reason": "LOGICAL_OPERATION_ALREADY_CLAIMED",
                "preserve": True, "allow_new_invocation": False,
                "logical_operation_id": logical_id}
    (scratch / "output-schema.json").write_text(
        json.dumps(OUTPUT_SCHEMA, sort_keys=True), encoding="utf-8")
    evidence = {"logical_operation_id": logical_id, "binding": binding,
                "process_entry": False, "semantic_release": False,
                "retry_count": 0}
    process = job = monitor = stdout = stderr = None
    handles = {}
    termination_attempted = False
    streams_persisted = False
    try:
        job = WindowsJob()
        evidence["process_entry"] = True
        process = subprocess.Popen(
            command_line(executable, scratch), cwd=str(scratch),
            env=child_environment(codex_home), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        evidence["root_pid"] = process.pid
        job.assign_process(process)
        if (job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                or not job.contains_handle(int(process._handle))):
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
        handles = monitor.finish()
        evidence["members"] = _member_evidence(handles)
        evidence["accounting_after_bounded_exit"] = job.accounting()
        evidence["stdout_sha256"] = _write_bytes_once(
            evidence_dir / "RAW_STDOUT.jsonl", bytes(stdout.raw))
        evidence["stderr_sha256"] = _write_bytes_once(
            evidence_dir / "RAW_STDERR.bin", bytes(stderr.raw))
        streams_persisted = True
        evidence["raw_stream_readback_verified"] = True
        if process.returncode != 0:
            raise RuntimeError("CODEX_EXIT_NONZERO")
        summary, messages = classify_events(
            (evidence_dir / "RAW_STDOUT.jsonl").read_bytes())
        evidence["event_summary"] = summary
        if summary["classification"] != "NO_TOOL_ACTIVITY_OBSERVED":
            raise RuntimeError(summary["classification"])
        if len(messages) != 1 or json.loads(messages[0]) != EXPECTED_RESULT:
            raise RuntimeError("WORKER_OUTPUT_SCHEMA_OR_VALUE")
        output_path = scratch / "last-message.json"
        last_raw = output_path.read_bytes()
        evidence["last_message_sha256"] = _write_bytes_once(
            evidence_dir / "LAST_MESSAGE.json", last_raw)
        if json.loads(last_raw) != EXPECTED_RESULT:
            raise RuntimeError("OUTPUT_FILE_MISMATCH")
        if canonical(json.loads(messages[0])) != canonical(json.loads(last_raw)):
            raise RuntimeError("DUAL_OUTPUT_MISMATCH")
        if set(job.process_ids()) or job.accounting()["active_processes"] != 0:
            raise RuntimeError("JOB_ACTIVE_AFTER_EXIT")
        if len(handles) != job.accounting()["total_processes"]:
            raise RuntimeError("TOTAL_MEMBER_CAPTURE_MISMATCH")
        for handle in handles.values():
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_EXITED")
        termination_attempted = True
        job.terminate(0x2B2)
        evidence["accounting_after_termination"] = job.accounting()
        evidence["termination_attempt_count"] = 1
        evidence["untrusted_result"] = EXPECTED_RESULT
        evidence["untrusted_result_sha256"] = sha256_bytes(messages[0].encode())
        result = {"status": "OBSERVED_ACCEPTED", "agent": AGENT,
                  "result_text": messages[0], "evidence": evidence,
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
                evidence["failure_termination_attempt_count"] = 1
            except Exception:
                evidence["failure_termination_uncertain"] = True
            try:
                if monitor is not None and monitor.thread.is_alive():
                    handles = monitor.finish()
                evidence["failure_members"] = _member_evidence(handles)
            except Exception:
                evidence["failure_member_evidence_uncertain"] = True
            try:
                if not streams_persisted:
                    if stdout is not None:
                        stdout.thread.join(timeout=2)
                        evidence["failure_stdout_sha256"] = _write_bytes_once(
                            evidence_dir / "RAW_STDOUT.jsonl", bytes(stdout.raw))
                    if stderr is not None:
                        stderr.thread.join(timeout=2)
                        evidence["failure_stderr_sha256"] = _write_bytes_once(
                            evidence_dir / "RAW_STDERR.bin", bytes(stderr.raw))
            except Exception:
                evidence["failure_stream_evidence_uncertain"] = True
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
        if job is not None:
            try:
                job.close()
            except Exception:
                pass


__all__ = ["AGENT", "EXPECTED_RESULT", "classify_events", "command_line",
           "logical_operation_id", "run_once"]

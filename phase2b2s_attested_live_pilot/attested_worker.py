"""Single tool-free Codex worker turn with exact capability attestation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from phase2b2l_alpha_isolation_preflight.alpha_isolation_preflight import (
    DISABLED_FEATURES,
)
from phase2b2m_alpha_live_pilot.alpha_exec_worker import (
    _Collector,
    child_environment,
    file_sha256,
    sha256_bytes,
)
from phase2b2p_capability_containment_repair.repair_contract import (
    EagerMemberMonitor,
    classify_attested_events,
    verify_member_accounting,
)
from phase2b2r_exact_codex_preflight.exact_codex_preflight import (
    POLICY_SHA256,
    verify_artifact,
)
from shared_interfaces.live_codex_worker import OperationLedger, canonical
from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    STILL_ACTIVE,
    WindowsJob,
)


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "low"
SERVICE_TIER = "default"
SANDBOX = "read-only"
AGENT = "codex-phase2b2-attested-worker"
MARKER = "LOCAL_ATTESTED_WORKER_OK_20261016"
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


def logical_operation_id(token, executable, executable_sha256):
    binding = {
        "kind": "genie-phase2b2-attested-live-worker-v1",
        "token": token,
        "semantic_request_sha256": sha256_bytes(SEMANTIC_REQUEST.encode()),
        "output_schema_sha256": sha256_bytes(canonical(OUTPUT_SCHEMA).encode()),
        "executable": str(Path(executable).resolve()),
        "executable_sha256": executable_sha256,
        "source_tag": "rust-v0.163.0-alpha.11",
        "source_commit": "5425d3e625daa58eea3ad1de27c087eb3b2ffbd3",
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "service_tier": SERVICE_TIER,
        "sandbox": SANDBOX,
        "policy_sha256": POLICY_SHA256,
        "agent": AGENT,
    }
    return sha256_bytes(canonical(binding).encode()), binding


def command_line(executable, scratch, logical_id):
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
        "--model", MODEL, "--sandbox", SANDBOX, "--ephemeral",
        "--ignore-rules", "--skip-git-repo-check", "--color", "never",
        "--json", "--no-tools", "--capability-snapshot-operation-id",
        logical_id, "--output-schema", str(scratch / "output-schema.json"),
        "--output-last-message", str(scratch / "last-message.json"),
    ]
    for feature in DISABLED_FEATURES:
        args.extend(("--disable", feature))
    args.append("-")
    return args


def _write_bytes_once(path, raw):
    path = Path(path)
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    digest = sha256_bytes(raw)
    if file_sha256(path) != digest:
        raise RuntimeError("EVIDENCE_READBACK_MISMATCH")
    return digest


def _assistant_result(raw):
    messages = []
    for line in raw.decode("utf-8", "strict").splitlines():
        if not line:
            continue
        event = json.loads(line)
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if (item.get("type") in ("agent_message", "assistant_message")
                and type(item.get("text")) is str):
            messages.append(item["text"])
    if len(messages) != 1 or json.loads(messages[0]) != EXPECTED_RESULT:
        raise RuntimeError("UNTRUSTED_RESULT_SHAPE")
    return messages[0]


def run_once(*, token, artifact_directory, codex_home, working_directory,
             ledger_path, evidence_directory, timeout_seconds=240):
    """Enter exactly one live process and one model turn; never replay it."""
    evidence = {"process_entry": False, "semantic_release": False,
                "retry_count": 0, "preserve": True,
                "allow_new_invocation": False}
    process = job = monitor = stdout = stderr = ledger = None
    handles = {}
    logical_id = None
    termination_attempted = False
    streams_persisted = False
    try:
        executable, executable_hash = verify_artifact(artifact_directory)
        scratch = Path(working_directory).resolve()
        evidence_directory = Path(evidence_directory).resolve()
        if not scratch.is_dir() or any(scratch.iterdir()):
            raise ValueError("CHILD_SCRATCH_NOT_EMPTY")
        if (not evidence_directory.is_dir()
                or Path(ledger_path).resolve().parent != evidence_directory):
            raise ValueError("EVIDENCE_DIRECTORY_MISMATCH")
        logical_id, binding = logical_operation_id(
            token, executable, executable_hash)
        evidence.update({"logical_operation_id": logical_id,
                         "binding": binding,
                         "artifact_checksum_readback_verified": True})
        ledger = OperationLedger(ledger_path)
        if not ledger.claim(logical_id, binding):
            return {"status": "UNKNOWN",
                    "reason": "LOGICAL_OPERATION_ALREADY_CLAIMED",
                    "logical_operation_id": logical_id, "evidence": evidence,
                    "preserve": True, "allow_new_invocation": False}
        (scratch / "output-schema.json").write_text(
            json.dumps(OUTPUT_SCHEMA, sort_keys=True), encoding="utf-8")
        job = WindowsJob()
        if job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
            raise RuntimeError("JOB_POLICY_MISMATCH")
        evidence["process_entry"] = True
        process = subprocess.Popen(
            command_line(executable, scratch, logical_id), cwd=str(scratch),
            env=child_environment(codex_home), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        evidence["root_pid"] = process.pid
        job.assign_process(process)
        if not job.contains_handle(int(process._handle)):
            raise RuntimeError("JOB_ASSIGNMENT_MISMATCH")
        evidence["assignment_verified_before_semantic_release"] = True
        monitor = EagerMemberMonitor(job)
        monitor.observe_once()
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
        handles, identities = monitor.finish()
        raw_stdout, raw_stderr = bytes(stdout.raw), bytes(stderr.raw)
        evidence["stdout_sha256"] = _write_bytes_once(
            evidence_directory / "RAW_STDOUT.jsonl", raw_stdout)
        evidence["stderr_sha256"] = _write_bytes_once(
            evidence_directory / "RAW_STDERR.bin", raw_stderr)
        streams_persisted = True
        evidence["raw_stream_readback_verified"] = True
        if process.returncode != 0:
            raise RuntimeError("CODEX_EXIT_NONZERO")
        expected_snapshot = {
            "logical_operation_id": logical_id,
            "executable_sha256": executable_hash,
            "model": MODEL, "sandbox": SANDBOX,
            "policy_sha256": POLICY_SHA256,
        }
        evidence["capability_attestation"] = classify_attested_events(
            raw_stdout, expected_snapshot)
        result_text = _assistant_result(raw_stdout)
        last_raw = (scratch / "last-message.json").read_bytes()
        evidence["last_message_sha256"] = _write_bytes_once(
            evidence_directory / "LAST_MESSAGE.json", last_raw)
        if (json.loads(last_raw) != EXPECTED_RESULT
                or canonical(json.loads(result_text)) != canonical(
                    json.loads(last_raw))):
            raise RuntimeError("FRESH_OUTPUT_READBACK_MISMATCH")
        accounting = job.accounting()
        verify_member_accounting(identities, accounting)
        for handle in handles.values():
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_EXITED")
        termination_attempted = True
        job.terminate(0x2B2)
        if not job.wait_for_active(0, 10):
            raise RuntimeError("JOB_DID_NOT_REACH_ZERO_ACTIVE")
        evidence.update({
            "members": [identity.__dict__ for _, identity in
                        sorted(identities.items())],
            "accounting_after_bounded_exit": accounting,
            "accounting_after_termination": job.accounting(),
            "termination_attempt_count": 1,
            "tool_activity_count": 0,
            "untrusted_result_sha256": sha256_bytes(result_text.encode()),
            "untrusted_result": EXPECTED_RESULT,
        })
        ledger.finish(logical_id, "OBSERVED_ACCEPTED", evidence)
        return {"status": "OBSERVED_ACCEPTED", "agent": AGENT,
                "result_text": result_text, "evidence": evidence,
                "logical_operation_id": logical_id, "preserve": True,
                "allow_new_invocation": False}
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
                    handles, identities = monitor.finish()
                    evidence["failure_members"] = [identity.__dict__
                        for _, identity in sorted(identities.items())]
            except Exception:
                evidence["failure_member_evidence_uncertain"] = True
            try:
                if not streams_persisted:
                    if stdout is not None:
                        stdout.thread.join(timeout=2)
                        evidence["failure_stdout_sha256"] = _write_bytes_once(
                            evidence_directory / "RAW_STDOUT.jsonl",
                            bytes(stdout.raw))
                    if stderr is not None:
                        stderr.thread.join(timeout=2)
                        evidence["failure_stderr_sha256"] = _write_bytes_once(
                            evidence_directory / "RAW_STDERR.bin",
                            bytes(stderr.raw))
            except Exception:
                evidence["failure_stream_evidence_uncertain"] = True
            if ledger is not None and logical_id is not None:
                ledger.finish(logical_id, "UNKNOWN", evidence)
            return {"status": "UNKNOWN", "reason": "POST_ENTRY_UNCERTAINTY",
                    "logical_operation_id": logical_id, "evidence": evidence,
                    "preserve": True, "allow_new_invocation": False}
        if ledger is not None and logical_id is not None:
            ledger.finish(logical_id, "UNKNOWN", evidence)
        return {"status": "REJECT", "reason": str(exc)[:200],
                "logical_operation_id": logical_id, "evidence": evidence,
                "process_entry": False, "preserve": True,
                "allow_new_invocation": False}
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


__all__ = ["EXPECTED_RESULT", "OUTPUT_SCHEMA", "SEMANTIC_REQUEST",
           "command_line", "logical_operation_id", "run_once"]

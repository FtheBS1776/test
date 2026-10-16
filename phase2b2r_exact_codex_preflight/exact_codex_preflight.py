"""One-shot, no-model verification of the exact patched Codex executable.

The process is entered once with stdin withheld.  It is assigned to the
accepted non-breakaway kill-on-close Job before any semantic bytes can be
released, observed while active, then terminated once.  No model request is
made and no retry path exists after process entry.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from phase2b2l_alpha_isolation_preflight.alpha_isolation_preflight import (
    DISABLED_FEATURES,
)
from phase2b2p_capability_containment_repair.repair_contract import (
    EagerMemberMonitor,
    verify_member_accounting,
)
from shared_interfaces.live_codex_worker import OperationLedger, canonical
from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_BREAKAWAY_OK,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK,
    STILL_ACTIVE,
    WindowsJob,
)


UPSTREAM_TAG = "rust-v0.163.0-alpha.11"
UPSTREAM_COMMIT = "5425d3e625daa58eea3ad1de27c087eb3b2ffbd3"
MODEL = "gpt-5.6-sol"
SANDBOX = "read-only"
POLICY = {"allowed_tools": []}
POLICY_SHA256 = hashlib.sha256(canonical(POLICY).encode()).hexdigest()
_SHA256_LINE = re.compile(r"\A([0-9a-fA-F]{64})[ \t]+\*?codex\.exe\s*\Z")


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_artifact(artifact_directory):
    directory = Path(artifact_directory).resolve()
    executable = directory / "codex.exe"
    checksum = directory / "codex.exe.sha256"
    if not executable.is_file() or not checksum.is_file():
        raise ValueError("ARTIFACT_FILES_MISSING")
    match = _SHA256_LINE.fullmatch(checksum.read_text(encoding="ascii"))
    if match is None:
        raise ValueError("ARTIFACT_CHECKSUM_FORMAT")
    recorded = match.group(1).lower()
    observed = file_sha256(executable)
    if observed != recorded:
        raise ValueError("ARTIFACT_CHECKSUM_MISMATCH")
    return executable, observed


def logical_operation_id(executable_sha256):
    binding = {
        "kind": "genie-phase2b2-exact-codex-no-model-preflight-v1",
        "upstream_tag": UPSTREAM_TAG,
        "upstream_commit": UPSTREAM_COMMIT,
        "executable_sha256": executable_sha256,
        "model": MODEL,
        "sandbox": SANDBOX,
        "policy_sha256": POLICY_SHA256,
        "semantic_input_sha256": hashlib.sha256(b"").hexdigest(),
        "model_turns": 0,
    }
    return hashlib.sha256(canonical(binding).encode()).hexdigest(), binding


def child_environment(codex_home):
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


def command_line(executable, logical_id):
    args = [
        str(Path(executable).resolve()), "exec", "--ignore-user-config",
        "--strict-config", "-c", "mcp_servers={}",
        "-c", "apps._default.enabled=false",
        "-c", "apps._default.destructive_enabled=false",
        "-c", "apps._default.open_world_enabled=false",
        "-c", 'approval_policy="never"',
        "--model", MODEL, "--sandbox", SANDBOX, "--ephemeral",
        "--ignore-rules", "--skip-git-repo-check", "--color", "never",
        "--json", "--no-tools", "--capability-snapshot-operation-id",
        logical_id,
    ]
    for feature in DISABLED_FEATURES:
        args.extend(("--disable", feature))
    # A dash makes Codex wait for stdin.  The parent never writes or closes it
    # until after the Job has been terminated, so no semantic/model entry occurs.
    args.append("-")
    return args


def _bounded_stream(stream, limit=1_000_000):
    raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise RuntimeError("STREAM_OVERSIZE")
    return raw


def _write_bytes_once(path, raw):
    path = Path(path)
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    observed = file_sha256(path)
    expected = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise RuntimeError("RAW_EVIDENCE_READBACK_MISMATCH")
    return observed


def run_once(*, artifact_directory, codex_home, working_directory, ledger_path,
             evidence_directory):
    """Run one no-model containment preflight; never retry after Popen."""
    evidence = {
        "classification": "PRE_ENTRY_REJECT",
        "process_entry": False,
        "semantic_release": False,
        "model_turns": 0,
        "retry_count": 0,
        "preserve": True,
        "allow_new_invocation": False,
    }
    process = job = monitor = None
    handles = {}
    termination_attempted = False
    ledger = None
    logical_id = None
    try:
        executable, executable_hash = verify_artifact(artifact_directory)
        scratch = Path(working_directory).resolve()
        evidence_directory = Path(evidence_directory).resolve()
        if not scratch.is_dir() or any(scratch.iterdir()):
            raise ValueError("PREFLIGHT_SCRATCH_NOT_EMPTY")
        if (not evidence_directory.is_dir()
                or Path(ledger_path).resolve().parent != evidence_directory):
            raise ValueError("EVIDENCE_DIRECTORY_MISMATCH")
        logical_id, binding = logical_operation_id(executable_hash)
        evidence.update({
            "logical_operation_id": logical_id,
            "binding": binding,
            "executable": str(executable),
            "executable_sha256": executable_hash,
            "artifact_checksum_readback_verified": True,
            "command": command_line(executable, logical_id),
        })
        ledger = OperationLedger(ledger_path)
        if not ledger.claim(logical_id, binding):
            return {"status": "UNKNOWN",
                    "reason": "LOGICAL_OPERATION_ALREADY_CLAIMED",
                    "evidence": evidence, "preserve": True,
                    "allow_new_invocation": False,
                    "logical_operation_id": logical_id}
        job = WindowsJob()
        flags = job.limit_flags()
        if (flags != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                or flags & (JOB_OBJECT_LIMIT_BREAKAWAY_OK
                            | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK)):
            raise RuntimeError("JOB_POLICY_MISMATCH")
        evidence["job_limit_flags"] = flags
        evidence["process_entry"] = True
        process = subprocess.Popen(
            evidence["command"], cwd=str(scratch),
            env=child_environment(codex_home), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        evidence["root_pid"] = process.pid
        job.assign_process(process)
        if not job.contains_handle(int(process._handle)):
            raise RuntimeError("JOB_ASSIGNMENT_MISMATCH")
        evidence["assignment_verified_before_semantic_release"] = True
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        else:
            raise RuntimeError("CODEX_EXITED_BEFORE_WITHHELD_STDIN_CHECK")
        evidence["withheld_stdin_wait_verified_seconds"] = 2
        monitor = EagerMemberMonitor(job)
        monitor.observe_once()
        monitor.start()
        evidence["stdin_withheld"] = True
        termination_attempted = True
        job.terminate(0x2B2)
        if not job.wait_for_active(0, 10):
            raise RuntimeError("JOB_DID_NOT_REACH_ZERO_ACTIVE")
        process.wait(timeout=5)
        handles, identities = monitor.finish()
        accounting = job.accounting()
        verify_member_accounting(identities, accounting)
        for handle in handles.values():
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_TERMINATED")
        stdout = _bounded_stream(process.stdout)
        stderr = _bounded_stream(process.stderr)
        stdout_sha256 = _write_bytes_once(
            evidence_directory / "RAW_STDOUT.bin", stdout)
        stderr_sha256 = _write_bytes_once(
            evidence_directory / "RAW_STDERR.bin", stderr)
        if any(scratch.iterdir()):
            raise RuntimeError("SCRATCH_MUTATION_OBSERVED")
        evidence.update({
            "members": [identity.__dict__ for _, identity in
                        sorted(identities.items())],
            "accounting_after_termination": accounting,
            "termination_attempt_count": 1,
            "job_kill_on_close_policy_verified": True,
            "stdout_sha256": stdout_sha256,
            "stderr_sha256": stderr_sha256,
            "stdout_length": len(stdout),
            "stderr_length": len(stderr),
            "raw_stream_readback_verified": True,
            "semantic_release": False,
            "model_turns": 0,
            "classification": "NO_MODEL_PREFLIGHT_ACCEPTED_NONCLAIM",
        })
        ledger.finish(logical_id, "OBSERVED_ACCEPTED", evidence)
        return {"status": "OBSERVED_ACCEPTED", "evidence": evidence,
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
            evidence["classification"] = "POST_ENTRY_UNKNOWN"
            if ledger is not None and logical_id is not None:
                ledger.finish(logical_id, "UNKNOWN", evidence)
            return {"status": "UNKNOWN", "reason": "POST_ENTRY_UNCERTAINTY",
                    "evidence": evidence, "preserve": True,
                    "allow_new_invocation": False}
        if ledger is not None and logical_id is not None:
            ledger.finish(logical_id, "UNKNOWN", evidence)
        return {"status": "REJECT", "reason": str(exc)[:200],
                "evidence": evidence, "process_entry": False,
                "preserve": True, "allow_new_invocation": False}
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


__all__ = [
    "MODEL", "POLICY_SHA256", "SANDBOX", "child_environment",
    "command_line", "logical_operation_id", "run_once", "verify_artifact",
]

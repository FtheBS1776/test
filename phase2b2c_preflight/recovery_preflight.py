"""One-shot Phase 2B2 recovery preflight with no semantic/model turn.

The process is real Codex app-server under the reviewed Windows Job path.  The
only protocol methods are initialization and read-only inventory discovery.
There is no thread/start, turn/start, semantic request, callback, or Genie path.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

from shared_interfaces import live_codex_worker as live
from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, STILL_ACTIVE, WindowsJob)


KIND = "genie-phase2b2-recovery-preflight-v1"
PROTOCOL_REQUEST_METHODS = (
    "initialize", "config/read", "mcpServerStatus/list", "model/list")
REJECTED_BY_CODEX_0_162_1 = ("browser_use_mcp_client",)
BOUND_RUNTIME_SUPPORTS_IGNORE_USER_CONFIG = False
EFFECTIVE_DISABLED_FEATURES = tuple(
    feature for feature in live.DISABLED_FEATURES
    if feature not in REJECTED_BY_CODEX_0_162_1)


def preflight_command_line(executable):
    """Remove only flags empirically rejected by the bound executable.

    This repair is for a future explicitly authorized operation.  It is never
    used to replay the preserved UNKNOWN operation recorded in this directory.
    """
    original = live.command_line(executable)
    repaired = []
    index = 0
    while index < len(original):
        if (index + 1 < len(original) and original[index] == "--disable"
                and original[index + 1] in REJECTED_BY_CODEX_0_162_1):
            index += 2
            continue
        repaired.append(original[index])
        index += 1
    return repaired


def _binding(executable, version, operation_context=None):
    executable = str(Path(executable).resolve())
    value = {
        "kind": KIND,
        "executable": executable,
        "executable_sha256": live.file_sha256(executable),
        "version": version,
        "model_catalog_target": live.MODEL,
        "reasoning_effort_catalog_target": live.REASONING_EFFORT,
        "service_tier_config": live.SERVICE_TIER,
        "sandbox": live.SANDBOX_MODE,
        "command_sha256": live.sha256_bytes(
            live.canonical(preflight_command_line(executable)).encode()),
        "protocol_request_methods": list(PROTOCOL_REQUEST_METHODS),
        "semantic_request_count": 0,
        "thread_start_count": 0,
        "turn_start_count": 0,
    }
    if operation_context is not None:
        if type(operation_context) is not str or not operation_context:
            raise ValueError("INVALID_OPERATION_CONTEXT")
        value["operation_context"] = operation_context
    return live.sha256_bytes(live.canonical(value).encode()), value


class PreflightLedger:
    def __init__(self, path):
        self.path = Path(path)

    def claim(self, operation_id, binding):
        if self.path.exists():
            return False
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                "CREATE TABLE operation(operation_id TEXT PRIMARY KEY, "
                "binding TEXT NOT NULL,state TEXT NOT NULL,preserve INTEGER "
                "NOT NULL,allow_new_invocation INTEGER NOT NULL,evidence TEXT)"
            )
            connection.execute(
                "INSERT INTO operation VALUES(?,?,?,?,?,NULL)",
                (operation_id, live.canonical(binding), "CLAIMED", 1, 0))
            return True
        finally:
            connection.close()

    def finish(self, operation_id, state, evidence):
        if state not in ("VERIFIED", "UNKNOWN", "REJECT"):
            raise ValueError("invalid preflight state")
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            changed = connection.execute(
                "UPDATE operation SET state=?,evidence=? "
                "WHERE operation_id=? AND state='CLAIMED'",
                (state, live.canonical(evidence), operation_id)).rowcount
            if changed != 1:
                raise ValueError("preflight terminal transition")
        finally:
            connection.close()


def _model_inventory(result):
    if type(result) is not dict or result.get("nextCursor") is not None:
        raise RuntimeError("MODEL_INVENTORY_INCOMPLETE")
    selected = [item for item in result.get("data", [])
                if item.get("model") == live.MODEL]
    if len(selected) != 1:
        raise RuntimeError("BOUND_MODEL_NOT_ADVERTISED")
    efforts = [item.get("reasoningEffort") for item in
               selected[0].get("supportedReasoningEfforts", [])]
    if live.REASONING_EFFORT not in efforts:
        raise RuntimeError("BOUND_EFFORT_NOT_ADVERTISED")
    return {"model": live.MODEL, "reasoning_effort": live.REASONING_EFFORT,
            "model_match_count": 1}


def _validate_preflight_inventory(config_result, mcp_result):
    inventory = live._validate_inventory(config_result, mcp_result)
    config = config_result.get("config", {})
    features = config.get("features", {})
    if type(features) is not dict:
        raise RuntimeError("EFFECTIVE_FEATURE_INVENTORY_INVALID")
    not_disabled = [name for name in EFFECTIVE_DISABLED_FEATURES
                    if features.get(name) is not False]
    if not_disabled:
        raise RuntimeError("EFFECTIVE_FEATURE_DISABLE_NOT_OBSERVED")
    return dict(inventory, disabled_features=list(EFFECTIVE_DISABLED_FEATURES))


def _inventory_observation(config_result, mcp_result):
    config = config_result.get("config", {}) if type(config_result) is dict else {}
    servers = config.get("mcp_servers", config.get("mcpServers", None))
    data = mcp_result.get("data") if type(mcp_result) is dict else None
    features = config.get("features", {})
    return {
        "configured_server_count": (len(servers)
                                    if type(servers) is dict else None),
        "status_item_count": len(data) if type(data) is list else None,
        "next_cursor_present": bool(mcp_result.get("nextCursor"))
        if type(mcp_result) is dict else None,
        "observed_disabled_feature_count": sum(
            features.get(name) is False for name in EFFECTIVE_DISABLED_FEATURES)
        if type(features) is dict else None,
    }


def _member_evidence(handles):
    members = []
    for pid, handle in sorted(handles.items()):
        image = handle.image_path()
        members.append({"pid": pid, "image": image,
                        "image_sha256": live.file_sha256(image)})
    return members


def _failure_member_evidence(handles):
    members = []
    for pid, handle in sorted(handles.items()):
        item = {"pid": pid}
        try:
            image = handle.image_path()
            item.update({"image": image,
                         "image_sha256": live.file_sha256(image)})
        except BaseException as exc:
            item["identity_observation_error"] = type(exc).__name__
        members.append(item)
    return members


def run_once(*, executable, version, codex_home, ledger_path,
             timeout_seconds=60, operation_context=None):
    operation_id, binding = _binding(executable, version, operation_context)
    ledger = PreflightLedger(ledger_path)
    if not ledger.claim(operation_id, binding):
        return {"status": "UNKNOWN", "reason": "PREFLIGHT_ALREADY_CLAIMED",
                "preserve": True, "allow_new_invocation": False,
                "operation_id": operation_id}

    evidence = {"operation_id": operation_id, "binding": binding,
                "process_entry_attempted": False, "semantic_request_count": 0,
                "thread_start_count": 0, "turn_start_count": 0,
                "model_turn_started": False, "retry_count": 0,
                "protocol_requests_sent": []}
    scratch = Path(tempfile.mkdtemp(prefix="genie-phase2b2c-preflight-"))
    process = job = monitor = rpc = stderr = None
    handles = {}
    termination_attempted = False
    try:
        live._validate_scratch(scratch, ledger_path)
        job = WindowsJob()
        evidence["process_entry_attempted"] = True
        process = subprocess.Popen(
            preflight_command_line(executable), cwd=str(scratch),
            env=live.child_environment(codex_home), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        evidence["root_pid"] = process.pid
        job.assign_process(process)
        evidence["assignment_verified_before_protocol"] = True
        if job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
            raise RuntimeError("JOB_LIMIT_MISMATCH")
        monitor = live._MemberMonitor(job)
        monitor.start()
        stderr = live._StderrCollector(process.stderr)
        stderr.start()
        rpc = live._JsonRpc(process)
        notifications = []
        deadline = time.monotonic() + timeout_seconds

        request_id = rpc.send("initialize", {
            "clientInfo": {"name": "genie-phase2b2c-preflight",
                           "title": "Genie Phase 2B2 Recovery Preflight",
                           "version": "1.0.0"},
            "capabilities": {"experimentalApi": True},
        })
        evidence["protocol_requests_sent"].append("initialize")
        init = rpc.wait_response(request_id, deadline, notifications)
        if type(init) is not dict:
            raise RuntimeError("INITIALIZE_RESPONSE_INVALID")
        rpc.send("initialized", {}, notification=True)
        request_id = rpc.send("config/read", {
            "cwd": str(scratch), "includeLayers": True})
        evidence["protocol_requests_sent"].append("config/read")
        config = rpc.wait_response(request_id, deadline, notifications)
        request_id = rpc.send("mcpServerStatus/list", {
            "cursor": None, "limit": 100, "detail": "full"})
        evidence["protocol_requests_sent"].append("mcpServerStatus/list")
        mcp = rpc.wait_response(request_id, deadline, notifications)
        request_id = rpc.send("model/list", {
            "cursor": None, "limit": 100, "includeHidden": True})
        evidence["protocol_requests_sent"].append("model/list")
        models = rpc.wait_response(request_id, deadline, notifications)
        evidence["inventory_observation"] = _inventory_observation(config, mcp)
        evidence["effective_inventory"] = _validate_preflight_inventory(
            config, mcp)
        evidence["model_inventory"] = _model_inventory(models)
        if any(note.get("method") in ("thread/started", "turn/started")
               for note in notifications):
            raise RuntimeError("UNEXPECTED_THREAD_OR_TURN")

        handles = monitor.finish_capture()
        before = job.accounting()
        if (not set(job.process_ids()).issubset(handles)
                or len(handles) != before["total_processes"]):
            raise RuntimeError("PROCESS_MEMBER_CAPTURE_MISMATCH")
        evidence["members"] = _member_evidence(handles)
        evidence["accounting_before_termination"] = before
        termination_attempted = True
        job.terminate(0x2B2C)
        if not job.wait_for_active(0, 10):
            raise RuntimeError("JOB_DID_NOT_REACH_ZERO_ACTIVE")
        evidence["accounting_after_termination"] = job.accounting()
        for handle in handles.values():
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_TERMINATED")
        process.wait(timeout=5)
        stderr.thread.join(timeout=2)
        if stderr.thread.is_alive() or stderr.oversize:
            raise RuntimeError("STDERR_CAPTURE_UNCERTAIN")
        evidence["stderr_sha256"] = live.sha256_bytes(bytes(stderr.raw))
        evidence["job_termination_attempt_count"] = 1
        evidence["semantic_release"] = False
        ledger.finish(operation_id, "VERIFIED", evidence)
        return {"status": "VERIFIED", "classification": "NONCLAIM",
                "operation_id": operation_id, "evidence": evidence,
                "preserve": True, "allow_new_invocation": False}
    except BaseException as exc:
        evidence["failure_class"] = type(exc).__name__
        evidence["failure_reason"] = str(exc)[:300]
        if evidence["process_entry_attempted"]:
            try:
                if monitor is not None and monitor.thread.is_alive():
                    handles = monitor.finish_capture()
                evidence["failure_members_before_termination"] = (
                    _failure_member_evidence(handles))
            except BaseException:
                evidence["failure_member_evidence_uncertain"] = True
            try:
                if job is not None and not termination_attempted:
                    termination_attempted = True
                    job.terminate(0x2B2C)
                    evidence["job_termination_attempt_count"] = 1
                if job is not None:
                    job.wait_for_active(0, 10)
                    evidence["failure_accounting_after_termination"] = job.accounting()
            except BaseException:
                evidence["failure_termination_uncertain"] = True
            try:
                if stderr is not None:
                    stderr.thread.join(timeout=2)
                    evidence["failure_stderr_sha256"] = live.sha256_bytes(
                        bytes(stderr.raw))
                    evidence["failure_stderr_excerpt"] = bytes(
                        stderr.raw[:4096]).decode("utf-8", "replace")
                if process is not None:
                    try:
                        evidence["failure_process_exit_code"] = process.wait(
                            timeout=5)
                    except subprocess.TimeoutExpired:
                        evidence["failure_process_exit_code"] = process.poll()
                        evidence["failure_process_wait_uncertain"] = True
            except BaseException:
                evidence["failure_stream_evidence_uncertain"] = True
            ledger.finish(operation_id, "UNKNOWN", evidence)
            return {"status": "UNKNOWN", "reason": "POST_ENTRY_UNCERTAINTY",
                    "operation_id": operation_id, "evidence": evidence,
                    "preserve": True, "allow_new_invocation": False}
        ledger.finish(operation_id, "REJECT", evidence)
        return {"status": "REJECT", "reason": str(exc)[:300],
                "operation_id": operation_id, "evidence": evidence,
                "preserve": True, "allow_new_invocation": False}
    finally:
        if monitor is not None and monitor.thread.is_alive():
            monitor.stop.set()
            monitor.thread.join(timeout=2)
        for handle in handles.values():
            try:
                handle.close()
            except BaseException:
                pass
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except BaseException:
                    pass
            handle = getattr(process, "_handle", None)
            if hasattr(handle, "Close"):
                try:
                    handle.Close()
                except BaseException:
                    pass
        if job is not None:
            try:
                job.close()
            except BaseException:
                pass


__all__ = ["KIND", "PROTOCOL_REQUEST_METHODS", "PreflightLedger",
           "preflight_command_line", "run_once"]

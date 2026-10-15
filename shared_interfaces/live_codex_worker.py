"""Bounded live Codex worker adapter for the Phase 2B2 NONCLAIM pilot.

This is not a general sandbox or a reusable launcher.  The parent keeps all
Genie authority.  A child is assigned to a kill-on-close Windows Job before
any semantic request is released, and every post-process-entry uncertainty is
terminal UNKNOWN with the original durable claim preserved.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import threading
import time

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
APP_SERVER_PROTOCOL = "2025-04-04"
AGENT = "codex-live-worker"
DISABLED_FEATURES = (
    "apps", "plugins", "multi_agent", "remote_plugin", "auth_elicitation",
    "tool_call_mcp_elicitation", "browser_use", "browser_use_mcp_client",
    "computer_use", "in_app_browser", "image_generation", "hooks",
    "shell_tool", "shell_snapshot", "unified_exec", "unified_exec_tty",
    "view_image", "workspace_dependencies", "skill_search",
    "skill_mcp_dependency_install", "tool_suggest", "daemon_auto_start",
    "worktrees", "code_mode_host", "sleep_tool", "system_proxy_fallback",
)
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "marker": {"type": "string", "const": "LOCAL_WORKER_OK_20261013"},
        "visible_tool_or_mcp_names": {
            "type": "array", "items": {"type": "string"}, "maxItems": 0,
        },
        "authority_request": {"type": "boolean", "const": False},
    },
    "required": ["marker", "visible_tool_or_mcp_names", "authority_request"],
    "additionalProperties": False,
}
SEMANTIC_REQUEST = (
    "Return only an object matching the supplied schema. Set marker to "
    "LOCAL_WORKER_OK_20261013, visible_tool_or_mcp_names to an empty array, "
    "and authority_request to false. Do not call tools, inspect files, or "
    "request permissions."
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path):
    with open(path, "rb") as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_operation_id(token, executable, version, executable_sha256):
    binding = {
        "kind": "genie-phase2b2-live-worker-v1",
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


class OperationLedger:
    """Durable no-replacement claim for one exact logical operation."""

    def __init__(self, path):
        self.path = Path(path)

    def claim(self, logical_id, binding):
        existed = self.path.exists()
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS operation ("
                "logical_id TEXT PRIMARY KEY, binding TEXT NOT NULL, "
                "state TEXT NOT NULL, preserve INTEGER NOT NULL, "
                "allow_new_invocation INTEGER NOT NULL, evidence TEXT)"
            )
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT binding,state FROM operation WHERE logical_id=?",
                (logical_id,),
            ).fetchone()
            if row is not None:
                connection.execute("ROLLBACK")
                return False
            if existed and connection.execute(
                    "SELECT count(*) FROM operation").fetchone()[0] != 0:
                connection.execute("ROLLBACK")
                raise ValueError("OPERATION_LEDGER_NOT_FRESH")
            connection.execute(
                "INSERT INTO operation VALUES(?,?,?,?,?,NULL)",
                (logical_id, canonical(binding), "CLAIMED", 1, 0),
            )
            connection.execute("COMMIT")
            return True
        finally:
            connection.close()

    def finish(self, logical_id, state, evidence):
        if state not in ("OBSERVED_ACCEPTED", "UNKNOWN"):
            raise ValueError("invalid terminal state")
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE operation SET state=?,preserve=1,"
                "allow_new_invocation=0,evidence=? "
                "WHERE logical_id=? AND state='CLAIMED'",
                (state, canonical(evidence), logical_id),
            ).rowcount
            if changed != 1:
                connection.execute("ROLLBACK")
                raise ValueError("OPERATION_TERMINAL_TRANSITION")
            connection.execute("COMMIT")
        finally:
            connection.close()


def child_environment(codex_home):
    """Minimal environment: auth location, never token values or Genie data."""
    required = ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP", "PATH",
                "PATHEXT", "USERPROFILE", "LOCALAPPDATA", "APPDATA")
    result = {key: os.environ[key] for key in required if key in os.environ}
    result.update({
        "CODEX_HOME": str(Path(codex_home).resolve()),
        "NO_COLOR": "1",
        "TERM": "dumb",
    })
    forbidden = [key for key in result if (
        key.upper().startswith("GENIE") or key.upper() == "OPENAI_API_KEY")]
    if forbidden:
        raise ValueError("AUTHORITY_ENVIRONMENT")
    return result


def command_line(executable):
    args = [
        str(Path(executable).resolve()), "--strict-config",
        "-c", "mcp_servers={}",
        "-c", "apps._default.enabled=false",
        "-c", "apps._default.destructive_enabled=false",
        "-c", "apps._default.open_world_enabled=false",
        "-c", "sandbox_mode=\"read-only\"",
        "-c", "approval_policy=\"never\"",
        "-c", f"model=\"{MODEL}\"",
        "-c", f"model_reasoning_effort=\"{REASONING_EFFORT}\"",
        "-c", f"service_tier=\"{SERVICE_TIER}\"",
    ]
    for feature in DISABLED_FEATURES:
        args.extend(("--disable", feature))
    # Global configuration belongs before the subcommand.  Keeping it here is
    # also independently testable without starting a second Codex process.
    args.extend(("app-server", "--listen", "stdio://"))
    return args


def _validate_scratch(working_directory, ledger_path):
    scratch = Path(working_directory).resolve()
    trial = Path(ledger_path).resolve().parent
    if (not scratch.is_dir() or any(scratch.iterdir())
            or scratch == trial or scratch.is_relative_to(trial)
            or trial.is_relative_to(scratch)):
        raise ValueError("CHILD_SCRATCH_NOT_ISOLATED")
    return scratch


class _JsonRpc:
    def __init__(self, process):
        self.process = process
        self.messages = queue.Queue()
        self.raw = []
        self._next = 1
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                if len(line) > 1_000_000:
                    self.messages.put(("reader_error", "OVERSIZE_JSONL"))
                    return
                stripped = line.strip()
                if not stripped:
                    continue
                value = json.loads(stripped)
                self.raw.append(value)
                self.messages.put(("message", value))
        except Exception:
            self.messages.put(("reader_error", "INVALID_JSONL"))
        finally:
            self.messages.put(("eof", None))

    def send(self, method, params, notification=False):
        value = {"method": method, "params": params}
        request_id = None
        if not notification:
            request_id, self._next = self._next, self._next + 1
            value["id"] = request_id
        raw = (canonical(value) + "\n").encode("utf-8")
        self.process.stdin.write(raw)
        self.process.stdin.flush()
        return request_id

    def wait_response(self, request_id, deadline, notifications):
        while time.monotonic() < deadline:
            try:
                kind, value = self.messages.get(timeout=max(
                    0.01, min(0.25, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if kind != "message":
                raise RuntimeError(value or "APP_SERVER_EOF")
            if value.get("id") == request_id:
                if "error" in value:
                    raise RuntimeError("APP_SERVER_RESPONSE_ERROR")
                return value.get("result")
            if "method" in value and "id" in value:
                raise RuntimeError("CHILD_REQUESTED_AUTHORITY")
            notifications.append(value)
        raise TimeoutError("APP_SERVER_RESPONSE_TIMEOUT")


class _StderrCollector:
    def __init__(self, stream):
        self.stream = stream
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
            if len(self.raw) + len(chunk) > 1_000_000:
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

    def finish_capture(self):
        self.stop.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive() or self.error:
            raise RuntimeError("MEMBER_MONITOR_UNCERTAIN")
        return self.handles


def _validate_inventory(config_result, mcp_result):
    config = config_result.get("config", {}) if type(config_result) is dict else {}
    servers = config.get("mcp_servers", config.get("mcpServers", {}))
    apps = config.get("apps", {})
    default_app = apps.get("_default", {}) if type(apps) is dict else {}
    data = mcp_result.get("data") if type(mcp_result) is dict else None
    if (servers not in ({}, None) or data != []
            or mcp_result.get("nextCursor") is not None):
        raise RuntimeError("EFFECTIVE_MCP_INVENTORY_NONEMPTY")
    if default_app.get("enabled") is not False:
        raise RuntimeError("EFFECTIVE_APPS_NOT_DISABLED")
    if config.get("sandbox_mode") != SANDBOX_MODE:
        raise RuntimeError("EFFECTIVE_SANDBOX_MISMATCH")
    return {"mcp_server_count": 0, "mcp_tool_count": 0,
            "apps_default_enabled": False, "sandbox_mode": SANDBOX_MODE}


def _assistant_text(notifications):
    texts = []
    for note in notifications:
        if note.get("method") != "item/completed":
            continue
        item = note.get("params", {}).get("item", {})
        if item.get("type") in ("agentMessage", "assistantMessage"):
            text = item.get("text")
            if type(text) is str:
                texts.append(text)
    if len(texts) != 1:
        raise RuntimeError("AUTHORITATIVE_RESULT_COUNT")
    value = json.loads(texts[0])
    expected = {"marker": "LOCAL_WORKER_OK_20261013",
                "visible_tool_or_mcp_names": [], "authority_request": False}
    if value != expected:
        raise RuntimeError("WORKER_OUTPUT_SCHEMA_OR_VALUE")
    return texts[0], value


def run_once(*, token, ledger_path, executable, version, codex_home,
             working_directory, timeout_seconds=120):
    """Enter the process once.  Never retry or synthesize success."""
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

    evidence = {"logical_operation_id": logical_id, "binding": binding,
                "process_entry": False, "semantic_release": False}
    process = None
    job = None
    monitor = None
    stderr_collector = None
    handles = {}
    termination_attempted = False
    try:
        job = WindowsJob()
        # Calling Popen is the process-entry boundary.  Even an exception can
        # conceal a created process, so no caller may interpret it as retryable.
        evidence["process_entry"] = True
        process = subprocess.Popen(
            command_line(executable), cwd=str(scratch),
            env=child_environment(codex_home), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        evidence["root_pid"] = process.pid
        job.assign_process(process)
        if job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
            raise RuntimeError("JOB_LIMIT_MISMATCH")
        monitor = _MemberMonitor(job)
        monitor.start()
        stderr_collector = _StderrCollector(process.stderr)
        stderr_collector.start()
        rpc = _JsonRpc(process)
        notifications = []
        deadline = time.monotonic() + timeout_seconds
        initialized = rpc.wait_response(rpc.send("initialize", {
            "clientInfo": {"name": "genie-phase2b2-pilot", "title":
                           "Genie Phase 2B2 Pilot", "version": "1.0.0"},
            "capabilities": {"experimentalApi": True},
        }), deadline, notifications)
        evidence["initialize"] = bool(type(initialized) is dict)
        rpc.send("initialized", {}, notification=True)
        config_result = rpc.wait_response(rpc.send(
            "config/read", {"cwd": str(Path(working_directory).resolve()),
                            "includeLayers": True}), deadline, notifications)
        mcp_result = rpc.wait_response(rpc.send(
            "mcpServerStatus/list", {"cursor": None, "limit": 100}),
            deadline, notifications)
        model_result = rpc.wait_response(rpc.send(
            "model/list", {"cursor": None, "limit": 100,
                           "includeHidden": True}), deadline, notifications)
        evidence["effective_inventory"] = _validate_inventory(
            config_result, mcp_result)
        models = model_result.get("data", [])
        selected = [item for item in models if item.get("model") == MODEL]
        if len(selected) != 1:
            raise RuntimeError("BOUND_MODEL_NOT_ADVERTISED")
        efforts = [item.get("reasoningEffort") for item in
                   selected[0].get("supportedReasoningEfforts", [])]
        if REASONING_EFFORT not in efforts:
            raise RuntimeError("BOUND_EFFORT_NOT_ADVERTISED")

        thread_result = rpc.wait_response(rpc.send("thread/start", {
            "model": MODEL, "serviceTier": SERVICE_TIER,
            "cwd": str(scratch),
            "approvalPolicy": "never", "sandbox": SANDBOX_MODE,
            "dynamicTools": [], "environments": [],
            "selectedCapabilityRoots": [], "runtimeWorkspaceRoots": [],
            "ephemeral": True, "experimentalRawEvents": False,
            "baseInstructions": "You are a data-only worker with no authority.",
            "developerInstructions": "Never call tools or request permissions.",
        }), deadline, notifications)
        thread_id = thread_result.get("thread", {}).get("id")
        if type(thread_id) is not str or not thread_id:
            raise RuntimeError("THREAD_ID_MISSING")

        evidence["semantic_release"] = True
        turn_result = rpc.wait_response(rpc.send("turn/start", {
            "threadId": thread_id,
            "input": [{"type": "text", "text": SEMANTIC_REQUEST,
                       "text_elements": []}],
            "effort": REASONING_EFFORT, "serviceTierForTurn": SERVICE_TIER,
            "outputSchema": OUTPUT_SCHEMA, "sandboxPolicy": {"type": "readOnly"},
            "environments": [],
        }), deadline, notifications)
        turn_id = turn_result.get("turn", {}).get("id")
        if type(turn_id) is not str or not turn_id:
            raise RuntimeError("TURN_ID_MISSING")
        completed = None
        while time.monotonic() < deadline and completed is None:
            kind, note = rpc.messages.get(timeout=max(
                0.01, min(0.25, deadline - time.monotonic())))
            if kind != "message":
                raise RuntimeError(note or "APP_SERVER_EOF")
            if "method" in note and "id" in note:
                raise RuntimeError("CHILD_REQUESTED_AUTHORITY")
            notifications.append(note)
            if note.get("method") == "turn/completed":
                turn = note.get("params", {}).get("turn", {})
                if turn.get("id") == turn_id:
                    completed = turn
        if completed is None or completed.get("status") != "completed":
            raise RuntimeError("TURN_NOT_COMPLETED")
        result_text, result_object = _assistant_text(notifications)
        evidence["untrusted_result_sha256"] = sha256_bytes(result_text.encode())
        evidence["untrusted_result"] = result_object

        handles = monitor.finish_capture()
        accounting_before = job.accounting()
        if not set(job.process_ids()).issubset(handles):
            # No active member may be absent; exited members remain represented
            # by captured, PID-reuse-safe process handles.
            raise RuntimeError("ACTIVE_MEMBER_CAPTURE_MISMATCH")
        if len(handles) != accounting_before["total_processes"]:
            raise RuntimeError("TOTAL_MEMBER_CAPTURE_MISMATCH")
        members = []
        for pid, handle in sorted(handles.items()):
            image = handle.image_path()
            members.append({"pid": pid, "image": image,
                            "image_sha256": file_sha256(image)})
        evidence["members"] = members
        evidence["accounting_before_termination"] = accounting_before
        termination_attempted = True
        job.terminate(0x2B2)
        if not job.wait_for_active(0, 10):
            raise RuntimeError("JOB_DID_NOT_REACH_ZERO_ACTIVE")
        evidence["accounting_after_termination"] = job.accounting()
        for handle in handles.values():
            if not handle.wait(5) or handle.exit_code() == STILL_ACTIVE:
                raise RuntimeError("MEMBER_NOT_TERMINATED")
        if process.poll() is None:
            process.wait(timeout=5)
        stderr_collector.thread.join(timeout=2)
        if stderr_collector.thread.is_alive() or stderr_collector.oversize:
            raise RuntimeError("STDERR_CAPTURE_UNCERTAIN")
        evidence["stderr_sha256"] = sha256_bytes(bytes(stderr_collector.raw))
        evidence["job_terminated_once"] = True
        evidence["retry_count"] = 0
        result = {"status": "OBSERVED_ACCEPTED", "agent": AGENT,
                  "result_text": result_text, "evidence": evidence,
                  "logical_operation_id": logical_id, "preserve": True,
                  "allow_new_invocation": False}
        ledger.finish(logical_id, "OBSERVED_ACCEPTED", evidence)
        return result
    except BaseException as exc:
        evidence["failure_class"] = type(exc).__name__
        evidence["failure_reason"] = str(exc)[:200]
        evidence["retry_count"] = 0
        if evidence["process_entry"]:
            try:
                if job is not None and not termination_attempted:
                    termination_attempted = True
                    job.terminate(0x2B2)
                    job.wait_for_active(0, 10)
                    evidence["failure_termination_attempted_once"] = True
            except Exception:
                evidence["failure_termination_uncertain"] = True
            try:
                if monitor is not None and monitor.thread.is_alive():
                    handles = monitor.finish_capture()
                if job is not None:
                    evidence["failure_accounting_after_termination"] = job.accounting()
                evidence["failure_observed_member_count"] = len(handles)
                evidence["failure_members"] = [{
                    "pid": pid, "image": handle.image_path(),
                    "image_sha256": file_sha256(handle.image_path()),
                } for pid, handle in sorted(handles.items())]
            except BaseException:
                evidence["failure_member_evidence_uncertain"] = True
            try:
                if stderr_collector is not None:
                    stderr_collector.thread.join(timeout=2)
                    evidence["failure_stderr_sha256"] = sha256_bytes(
                        bytes(stderr_collector.raw))
                    evidence["failure_stderr_excerpt"] = bytes(
                        stderr_collector.raw[:4096]).decode("utf-8", "replace")
                    evidence["failure_stderr_oversize"] = stderr_collector.oversize
                if process is not None:
                    evidence["failure_process_exit_code"] = process.poll()
            except BaseException:
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


__all__ = [
    "AGENT", "DISABLED_FEATURES", "MODEL", "OperationLedger", "OUTPUT_SCHEMA",
    "REASONING_EFFORT", "SANDBOX_MODE", "SEMANTIC_REQUEST", "SERVICE_TIER",
    "child_environment", "command_line", "logical_operation_id", "run_once",
]

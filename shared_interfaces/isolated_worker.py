"""Fixture-only Phase 2B2A worker process boundary.

This module cannot invoke Codex or apply a Genie event.  Under its trusted
local-filesystem assumption, it dispatches the hash-pinned deterministic
NO_MODEL_CALL fixture after committing a launcher-local one-shot claim.
Child output remains untrusted data.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import threading
import time


FIXTURE_PROTOCOL = "genie-no-model-worker-fixture-v1"
REQUEST_PROTOCOL = "genie-isolated-worker-request-v1"
FIXTURE_SHA256 = "09bb17ed56dbe1f844fd4909a9ee322c37607d4cc0cea61cfd3e4a0944c0179f"
FIXTURE_PYTHON_SHA256 = "dcdc8a4ef3c108d7d11f7a8afea50502c8f41763d118f1a94dafc90c74f1614c"
CODEX_CLI_VERSION = "0.162.1"
CODEX_CLI_SHA256 = "dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a"
CODEX_CLI_PATH = Path(
    r"C:\Users\aaron\AppData\Roaming\npm\node_modules\@openai\codex"
    r"\node_modules\@openai\codex-win32-x64\vendor"
    r"\x86_64-pc-windows-msvc\bin\codex.exe")
FIXTURE_PYTHON_PATH = Path(
    r"C:\Users\aaron\Documents\Codex\phase2a-venv\Scripts\python.exe")
CLAIM_STORE_NAME = "phase2b2a-launch-claims.sqlite"
MAX_REQUEST_BYTES = 65536
MAX_STDIN_BYTES = 65536
MAX_STDOUT_BYTES = 65536
MAX_STDERR_BYTES = 8192
FIXTURE_TIMEOUT_SECONDS = 1.0
FIXTURE_MODES = {
    "success", "crash", "nonzero", "timeout", "malformed", "oversize",
    "stderr_oversize", "invalid_utf8", "duplicate", "nonfinite", "extra",
    "wrong_hash", "wrong_protocol", "wrong_stdin", "wrong_argv",
    "wrong_environment", "repository_true", "model_true", "wrong_proposal",
    "wrong_classification", "stderr", "missing",
}
DISABLED_CODEX_FEATURES = (
    "apps", "plugins", "multi_agent", "remote_plugin", "auth_elicitation",
    "tool_call_mcp_elicitation", "browser_use", "browser_use_external",
    "browser_use_full_cdp_access", "computer_use", "in_app_browser",
    "image_generation", "hooks", "shell_tool", "shell_snapshot", "unified_exec",
    "unified_exec_tty", "view_image", "workspace_dependencies", "skill_search",
    "skill_mcp_dependency_install", "tool_suggest", "daemon_auto_start",
    "worktrees", "code_mode_host", "sleep_tool", "system_proxy_fallback",
)
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
_REQUEST_KEYS = {"instruction", "materials", "constraints"}
_OUTPUT_KEYS = {
    "protocol", "classification", "request_sha256", "stdin_sha256",
    "argv_sha256", "environment_keys", "cwd_is_repository", "model_invoked",
    "proposal",
}
_CLAIM_COLUMNS = [
    ("launch_id", "TEXT", 0, None, 1),
    ("request_sha256", "TEXT", 1, None, 0),
    ("state", "TEXT", 1, None, 0),
    ("result_sha256", "TEXT", 0, None, 0),
]
_CLAIM_TABLE_SQL = (
    "CREATE TABLE launch_claims("
    "launch_id TEXT PRIMARY KEY,"
    "request_sha256 TEXT NOT NULL,"
    "state TEXT NOT NULL CHECK(state IN ('CLAIMED','RETURNED')),"
    "result_sha256 TEXT)")


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8", errors="strict")


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


def _constant(_value):
    raise ValueError("nonfinite value")


def _strict_json(raw):
    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=_pairs, parse_constant=_constant)


def _reject(reason):
    return {"status": "REJECT", "reason": reason}


def _unknown():
    return {
        "status": "UNKNOWN",
        "reason": "ISOLATED_WORKER_OUTCOME_UNKNOWN",
        "preserve": True,
        "allow_new_invocation": False,
    }


def _inside_repository(path):
    resolved = path.resolve()
    return any((item / ".git").exists() for item in (resolved, *resolved.parents))


def _has_link_component(path):
    current = Path(path)
    parts = current.parts
    if not parts:
        return True
    probe = Path(parts[0])
    for part in parts[1:]:
        probe /= part
        if probe.exists() and (
                probe.is_symlink()
                or (hasattr(probe, "is_junction") and probe.is_junction())):
            return True
    return False


def _is_disposable_launcher_root(path):
    resolved = Path(path).resolve()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    try:
        relative = resolved.relative_to(temporary_root)
    except ValueError:
        return False
    return (
        relative != Path(".")
        and bool(relative.parts)
        and relative.parts[0].startswith("genie-phase2b2a-")
    )


def _check_claim_schema(connection):
    objects = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master"
        " WHERE name NOT LIKE 'sqlite_%'"
        " ORDER BY type,name").fetchall()
    if objects != [
            ("table", "launch_claims", "launch_claims", _CLAIM_TABLE_SQL)]:
        raise ValueError("claim objects")
    found = connection.execute("PRAGMA table_info(launch_claims)").fetchall()
    columns = [(row[1], row[2], row[3], row[4], row[5]) for row in found]
    if columns != _CLAIM_COLUMNS:
        raise ValueError("claim columns")
    if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise ValueError("claim integrity")


def _check_claim_file(path):
    path = Path(path)
    if (not path.exists() or path != path.resolve()
            or not path.is_file() or path.is_symlink()
            or _has_link_component(path) or path.stat().st_nlink != 1):
        raise ValueError("claim file")


def _request_snapshot(request):
    if type(request) is not dict or set(request) != _REQUEST_KEYS:
        raise ValueError("request shape")
    instruction = request["instruction"]
    materials = request["materials"]
    constraints = request["constraints"]
    if (type(instruction) is not str or not instruction
            or "\x00" in instruction
            or len(instruction.encode("utf-8", errors="strict")) > 16384):
        raise ValueError("instruction")
    if (type(materials) is not list or len(materials) > 8
            or type(constraints) is not list or len(constraints) > 16):
        raise ValueError("lists")
    for value in materials:
        if (type(value) is not str or "\x00" in value
                or len(value.encode("utf-8", errors="strict")) > 8192):
            raise ValueError("material")
    for value in constraints:
        if (type(value) is not str or "\x00" in value
                or len(value.encode("utf-8", errors="strict")) > 2048):
            raise ValueError("constraint")
    raw = _canonical(request)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("request bound")
    return json.loads(raw.decode("utf-8")), raw


def _read_bounded(pipe, limit, output, overflow, errors):
    try:
        while True:
            chunk = pipe.read(4096)
            if not chunk:
                return
            remaining = limit + 1 - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(output) > limit or len(chunk) > remaining:
                overflow.set()
                return
    except BaseException as exc:
        errors.append(exc)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _write_stdin(pipe, payload, errors):
    try:
        pipe.write(payload)
        pipe.flush()
    except BaseException as exc:
        errors.append(exc)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _terminate(process):
    clean = True
    try:
        running = process.poll() is None
    except BaseException:
        clean = False
        running = True
    if running:
        try:
            process.kill()
        except BaseException:
            clean = False
    try:
        process.wait(timeout=2)
    except BaseException:
        clean = False
    try:
        if process.poll() is None:
            clean = False
    except BaseException:
        clean = False
    return clean


def _communicate_bounded(process, payload):
    stdout = bytearray()
    stderr = bytearray()
    overflow = threading.Event()
    errors = []
    readers = [
        threading.Thread(
            target=_read_bounded,
            args=(process.stdout, MAX_STDOUT_BYTES, stdout, overflow, errors),
            daemon=True),
        threading.Thread(
            target=_read_bounded,
            args=(process.stderr, MAX_STDERR_BYTES, stderr, overflow, errors),
            daemon=True),
    ]
    writer = threading.Thread(
        target=_write_stdin, args=(process.stdin, payload, errors), daemon=True)
    timed_out = False
    transport_error = None
    started = []
    try:
        for thread in readers:
            thread.start()
            started.append(thread)
        writer.start()
        started.append(writer)
        deadline = time.monotonic() + FIXTURE_TIMEOUT_SECONDS
        while process.poll() is None:
            if overflow.is_set() or errors:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                process.wait(timeout=min(0.02, remaining))
            except subprocess.TimeoutExpired:
                pass
    except BaseException as exc:
        transport_error = exc
    finally:
        reaped = _terminate(process)
        for thread in started:
            thread.join(timeout=2)
        for pipe in (process.stdin, process.stdout, process.stderr):
            try:
                pipe.close()
            except BaseException:
                pass
    if isinstance(transport_error, (KeyboardInterrupt, SystemExit)):
        raise transport_error
    if (transport_error is not None or not reaped or timed_out
            or overflow.is_set() or errors
            or any(thread.is_alive() for thread in started)):
        raise RuntimeError("uncertain child transport")
    return process.returncode, bytes(stdout), bytes(stderr)


class NoModelFixtureWorkerLauncher:
    """Run only the pinned deterministic fixture behind a one-shot claim."""

    def __init__(self, *, claim_db, work_root, python_executable, fixture_path,
                 mode="success"):
        self._profile = (
            Path(claim_db), Path(work_root), Path(python_executable),
            Path(fixture_path), mode)

    def __setattr__(self, name, value):
        if name == "_profile" and hasattr(self, "_profile"):
            raise AttributeError("launcher profile is immutable")
        object.__setattr__(self, name, value)

    @property
    def claim_db(self):
        return self._profile[0]

    @property
    def work_root(self):
        return self._profile[1]

    @property
    def python_executable(self):
        return self._profile[2]

    @property
    def fixture_path(self):
        return self._profile[3]

    @property
    def mode(self):
        return self._profile[4]

    def _bound_argv(self):
        expected_fixture = (
            Path(__file__).resolve().parents[1]
            / "phase2b2a_launcher" / "no_model_fixture.py")
        if self.python_executable.resolve() != FIXTURE_PYTHON_PATH.resolve():
            raise ValueError("fixture interpreter path")
        if self.fixture_path.resolve() != expected_fixture.resolve():
            raise ValueError("fixture path")
        for path, expected in (
                (self.python_executable, FIXTURE_PYTHON_SHA256),
                (self.fixture_path, FIXTURE_SHA256)):
            if (not path.is_file() or _has_link_component(path)
                    or path.stat().st_nlink != 1
                    or _sha256(path) != expected):
                raise ValueError("source binding")
        return (
            str(self.python_executable.resolve()), "-I", "-S", "-B",
            str(self.fixture_path.resolve()), "--mode", self.mode)

    def _validated_profile(self):
        if self.mode not in FIXTURE_MODES:
            raise ValueError("mode")
        paths = (
            self.claim_db, self.work_root, self.python_executable,
            self.fixture_path)
        if any(not path.is_absolute() for path in paths):
            raise ValueError("absolute paths")
        if (self.work_root != self.work_root.resolve()
                or not self.work_root.is_dir() or self.work_root.is_symlink()
                or _has_link_component(self.work_root)
                or not _is_disposable_launcher_root(self.work_root)
                or _inside_repository(self.work_root)):
            raise ValueError("work root")
        if (self.claim_db != self.claim_db.resolve()
                or self.claim_db.parent.resolve() != self.work_root.resolve()
                or self.claim_db.name != CLAIM_STORE_NAME
                or not self.claim_db.parent.is_dir()
                or _has_link_component(self.claim_db.parent)
                or self.claim_db.is_symlink()):
            raise ValueError("claim store")
        argv = self._bound_argv()
        if self.claim_db.exists():
            _check_claim_file(self.claim_db)
            connection = sqlite3.connect(
                self.claim_db.resolve().as_uri() + "?mode=ro",
                uri=True, timeout=5)
            try:
                _check_claim_schema(connection)
            finally:
                connection.close()
        return argv

    def _claim_once(self, launch_id, request_sha256):
        if self.claim_db.exists():
            _check_claim_file(self.claim_db)
        connection = sqlite3.connect(
            self.claim_db, timeout=5, isolation_level=None)
        try:
            _check_claim_file(self.claim_db)
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            _check_claim_file(self.claim_db)
            objects = connection.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master"
                " WHERE name NOT LIKE 'sqlite_%'"
                " ORDER BY type,name").fetchall()
            if not objects:
                connection.execute(_CLAIM_TABLE_SQL)
            _check_claim_schema(connection)
            try:
                connection.execute(
                    "INSERT INTO launch_claims"
                    "(launch_id,request_sha256,state,result_sha256)"
                    " VALUES(?,?,'CLAIMED',NULL)",
                    (launch_id, request_sha256))
            except sqlite3.IntegrityError:
                connection.execute("ROLLBACK")
                return False
            connection.execute("COMMIT")
            return True
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            connection.close()

    def _record_return(self, launch_id, request_sha256, result_sha256):
        _check_claim_file(self.claim_db)
        connection = sqlite3.connect(
            self.claim_db, timeout=5, isolation_level=None)
        try:
            _check_claim_file(self.claim_db)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            _check_claim_file(self.claim_db)
            _check_claim_schema(connection)
            cursor = connection.execute(
                "UPDATE launch_claims SET state='RETURNED',result_sha256=?"
                " WHERE launch_id=? AND request_sha256=? AND state='CLAIMED'",
                (result_sha256, launch_id, request_sha256))
            if cursor.rowcount != 1:
                raise ValueError("claim changed")
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            connection.close()

    def _environment(self):
        environment = {"GENIE_EXECUTION_CLASS": "NO_MODEL_CALL_FIXTURE"}
        for key in ("SystemRoot", "WINDIR"):
            if key in os.environ:
                environment[key] = os.environ[key]
        return environment

    def _spawn_once(self, argv, payload, request_sha256):
        if tuple(argv) != self._bound_argv():
            raise ValueError("source or argv binding")
        environment = self._environment()
        with tempfile.TemporaryDirectory(
                prefix="genie-worker-fixture-", dir=self.work_root) as directory:
            cwd = Path(directory).resolve()
            if _inside_repository(cwd):
                raise ValueError("working directory")
            creationflags = (
                subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            process = subprocess.Popen(
                list(argv), shell=False, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=cwd, env=environment, close_fds=True,
                creationflags=creationflags)
            returncode, stdout, stderr = _communicate_bounded(process, payload)
            if returncode != 0 or stderr:
                raise RuntimeError("child failed")
            result = _strict_json(stdout)
            expected_argv = [
                str(self.fixture_path.resolve()), "--mode", self.mode]
            if (type(result) is not dict or set(result) != _OUTPUT_KEYS
                    or result["protocol"] != FIXTURE_PROTOCOL
                    or result["classification"] != "UNTRUSTED_FIXTURE_OUTPUT"
                    or result["request_sha256"] != request_sha256
                    or result["stdin_sha256"] != hashlib.sha256(payload).hexdigest()
                    or result["argv_sha256"]
                    != hashlib.sha256(_canonical(expected_argv)).hexdigest()
                    or result["environment_keys"]
                    != sorted(key.upper() for key in environment)
                    or result["cwd_is_repository"] is not False
                    or result["model_invoked"] is not False
                    or result["proposal"] != "NO_MODEL_CALL"):
                raise ValueError("invalid child result")
            return result, hashlib.sha256(stdout).hexdigest()

    def launch_worker(self, launch_id, request):
        """Claim once, spawn once, never retry, and return untrusted fixture data."""
        try:
            if type(launch_id) is not str or not _HEX64.fullmatch(launch_id):
                return _reject("INVALID_LAUNCH_ID")
            snapshot, request_raw = _request_snapshot(request)
            request_sha256 = hashlib.sha256(request_raw).hexdigest()
            envelope = {
                "protocol": REQUEST_PROTOCOL,
                "classification": "BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT",
                "request_sha256": request_sha256,
                "request": snapshot,
            }
            payload = _canonical(envelope)
            if len(payload) > MAX_STDIN_BYTES:
                raise ValueError("stdin bound")
            argv = self._validated_profile()
        except Exception:
            return _reject("INVALID_ISOLATED_WORKER_REQUEST_OR_PROFILE")
        try:
            if not self._claim_once(launch_id, request_sha256):
                return _unknown()
        except KeyboardInterrupt:
            return _unknown()
        except Exception:
            return _unknown()
        try:
            result, result_sha256 = self._spawn_once(
                argv, payload, request_sha256)
            self._record_return(
                launch_id, request_sha256, result_sha256)
            return {
                "status": "RETURNED",
                "classification": "UNTRUSTED_NO_MODEL_FIXTURE_OUTPUT",
                "request_sha256": request_sha256,
                "proposal": result["proposal"],
                "fixture_only": True,
                "allow_new_invocation": False,
            }
        except KeyboardInterrupt:
            return _unknown()
        except Exception:
            return _unknown()


def deferred_codex_worker_plan(executable):
    """Return a pinned, non-executable future Codex worker profile."""
    path = Path(executable)
    if (not path.is_absolute()
            or path.resolve() != CODEX_CLI_PATH.resolve()
            or not path.is_file() or _has_link_component(path)
            or path.stat().st_nlink != 1
            or _sha256(path) != CODEX_CLI_SHA256):
        raise ValueError("CODEX_CLI_SOURCE_BINDING")
    argv = [
        str(path.resolve()), "exec", "--ignore-user-config", "--ignore-rules",
        "--ephemeral", "--strict-config", "--sandbox", "read-only",
        "--skip-git-repo-check", "--output-schema",
        "<absolute-parent-generated-schema>", "--output-last-message",
        "<absolute-parent-generated-result>", "--color", "never",
    ]
    for feature in DISABLED_CODEX_FEATURES:
        argv.extend(("--disable", feature))
    argv.append("-")
    return {
        "status": "DEFERRED_NOT_EXECUTABLE",
        "classification": "PHASE_2B2A_PLAN_ONLY",
        "codex_version": CODEX_CLI_VERSION,
        "executable_sha256": CODEX_CLI_SHA256,
        "argv_template": argv,
        "stdin": "BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT",
        "model": None,
        "authentication": "NOT_PROVISIONED",
        "effective_tool_inventory": "NOT_PROBED",
    }

"""Fixture-only Phase 2B2B Windows descendant-containment preflight.

No Codex, model, provider, Genie store, callback, or MCP surface is reachable
from this module.  A trusted deterministic child waits for an explicit gate,
which is released only after its process is assigned to a verified Job Object.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    ProcessWaitHandle,
    STILL_ACTIVE,
    WindowsJob,
)


PROBE_PROTOCOL = "genie-process-tree-containment-preflight-v1"
FIXTURE_PROTOCOL = "genie-no-model-process-tree-fixture-v1"
FIXTURE_SHA256 = "43e7517997d1f0c9d97bfd03f8fa696ef52f978cb638206ca76acbacc9835389"
HOST_PYTHON_SHA256 = (
    "dcdc8a4ef3c108d7d11f7a8afea50502c8f41763d118f1a94dafc90c74f1614c")
HOST_PYTHON_PATH = Path(
    r"C:\Users\aaron\Documents\Codex\phase2a-venv\Scripts\python.exe")
BASE_RUNTIME = Path(
    r"C:\Users\aaron\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python")
PYTHON_PATH = BASE_RUNTIME / "python.exe"
PYTHON_SHA256 = (
    "d41bad46673f64e0d02f23797f53f90ccf60f27d6eda8d86dd2d4bbeae5a858c")
SELECTED_RUNTIME_SHA256 = {
    "python312.dll": (
        "8bb70bceffd5877733a957b31c392ca027bd2f84230e00de1654f994422fa2af"),
    "python3.dll": (
        "0366ee3d630c26ffc27bfab162648ae8c5cadc74b4b46f3e179ca70f4436cab9"),
    "DLLs/_ctypes.pyd": (
        "926df1f47c2a782ba154d6824a84aee7197a32eb6b781c2fc33120851e0fb53b"),
}
KERNEL32_SHA256 = (
    "70f1e69a1d0602ec9e02c713ff2fc1238ddc7fe02ad28fa344954dda446e5236")
CONHOST_SHA256 = (
    "2266b396ef92534a2a2844438df043d4069a2ec47d4e464f55e8c1cd47124a98")
GATE = b"RELEASE_AFTER_JOB_ASSIGNMENT\n"
REPORT_LIMIT = 4096
REPORT_TIMEOUT_SECONDS = 3.0
TERMINATION_TIMEOUT_SECONDS = 3.0
TERMINATION_EXIT_CODE = 0xE2B2B001
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
_REPORT_KEYS = {
    "protocol", "model_invoked", "parent_pid", "descendant_pid", "proposal",
}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def _strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("nonfinite value")

    return json.loads(
        raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
        parse_constant=constant)


def _has_link_component(path):
    current = Path(path)
    if not current.parts:
        return True
    probe = Path(current.parts[0])
    for part in current.parts[1:]:
        probe /= part
        if probe.exists() and (
                probe.is_symlink()
                or (hasattr(probe, "is_junction") and probe.is_junction())):
            return True
    return False


def _inside_repository(path):
    value = Path(path).resolve()
    return any((item / ".git").exists() for item in (value, *value.parents))


def _is_probe_root(path):
    resolved = Path(path).resolve()
    temporary = Path(tempfile.gettempdir()).resolve()
    try:
        relative = resolved.relative_to(temporary)
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0].startswith(
        "genie-phase2b2b-")


def _reject(reason):
    return {"status": "REJECT", "reason": reason}


def _unknown():
    return {
        "status": "UNKNOWN",
        "reason": "PROCESS_TREE_CONTAINMENT_OUTCOME_UNKNOWN",
        "preserve": True,
        "allow_new_invocation": False,
    }


def _kernel32_path():
    root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not root:
        raise ValueError("Windows root unavailable")
    return Path(root).resolve() / "System32" / "kernel32.dll"


def _conhost_path():
    return _kernel32_path().parent / "conhost.exe"


def selected_runtime_profile():
    """Return a verified partial support-set observation, never full closure."""
    files = {
        "host_python.exe": HOST_PYTHON_PATH,
        "child_python.exe": PYTHON_PATH,
    }
    files.update({name: BASE_RUNTIME / name for name in SELECTED_RUNTIME_SHA256})
    files["kernel32.dll"] = _kernel32_path()
    files["conhost.exe"] = _conhost_path()
    expected = {
        "host_python.exe": HOST_PYTHON_SHA256,
        "child_python.exe": PYTHON_SHA256,
        **SELECTED_RUNTIME_SHA256,
        "kernel32.dll": KERNEL32_SHA256,
        "conhost.exe": CONHOST_SHA256,
    }
    observed = {}
    for name, path in files.items():
        resolved = path.resolve()
        links = resolved.stat().st_nlink
        expected_links = 2 if name in ("kernel32.dll", "conhost.exe") else 1
        if (not resolved.is_file() or resolved.is_symlink()
                or _has_link_component(resolved)
                or links != expected_links):
            raise ValueError("selected runtime path")
        digest = _sha256(resolved)
        if digest != expected[name]:
            raise ValueError("selected runtime digest")
        observed[name] = {
            "path": str(resolved), "sha256": digest,
            "bytes": resolved.stat().st_size, "hardlink_count": links,
        }
    windows = sys.getwindowsversion()
    return {
        "classification": "PARTIAL_SELECTED_RUNTIME_SUPPORT_SET",
        "complete_runtime_closure": False,
        "python_version": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "windows_version": {
            "major": windows.major,
            "minor": windows.minor,
            "build": windows.build,
            "platform": windows.platform,
            "service_pack": windows.service_pack,
            "service_pack_major": windows.service_pack_major,
            "service_pack_minor": windows.service_pack_minor,
            "suite_mask": windows.suite_mask,
            "product_type": windows.product_type,
            "platform_version": list(windows.platform_version),
        },
        "files": observed,
    }


class _OneLineReader:
    def __init__(self, pipe):
        self._pipe = pipe
        self.raw = None
        self.error = None
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._read, daemon=True)

    def _read(self):
        try:
            value = self._pipe.readline(REPORT_LIMIT + 2)
            if not value.endswith(b"\n") or len(value) > REPORT_LIMIT + 1:
                raise ValueError("invalid report framing")
            self.raw = value[:-1]
        except BaseException as exc:
            self.error = exc
        finally:
            self._done.set()

    def start(self):
        self._thread.start()

    def result(self, timeout):
        if not self._done.wait(timeout):
            raise TimeoutError("fixture report timeout")
        if self.error is not None:
            raise RuntimeError("fixture report read failed") from self.error
        return self.raw

    def join(self):
        self._thread.join(timeout=TERMINATION_TIMEOUT_SECONDS)
        return not self._thread.is_alive()


class NoModelProcessTreeContainmentProbe:
    """Run at most one fixture-only Job Object containment probe per instance."""

    def __init__(self, *, work_root, python_executable, fixture_path):
        self._profile = (
            Path(work_root), Path(python_executable), Path(fixture_path))
        self._lock = threading.Lock()
        self._used = False

    def __setattr__(self, name, value):
        if name == "_profile" and hasattr(self, "_profile"):
            raise AttributeError("containment profile is immutable")
        object.__setattr__(self, name, value)

    @property
    def work_root(self):
        return self._profile[0]

    @property
    def python_executable(self):
        return self._profile[1]

    @property
    def fixture_path(self):
        return self._profile[2]

    def _validated_profile(self):
        expected_fixture = (
            Path(__file__).resolve().parents[1] / "phase2b2b_containment"
            / "process_tree_fixture.py")
        if (os.name != "nt"
                or Path(sys.executable).resolve() != HOST_PYTHON_PATH.resolve()
                or self.python_executable.resolve() != PYTHON_PATH.resolve()
                or self.fixture_path.resolve() != expected_fixture.resolve()):
            raise ValueError("profile identity")
        if (not self.work_root.is_absolute()
                or self.work_root != self.work_root.resolve()
                or not self.work_root.is_dir() or self.work_root.is_symlink()
                or _has_link_component(self.work_root)
                or not _is_probe_root(self.work_root)
                or _inside_repository(self.work_root)):
            raise ValueError("work root")
        selected_runtime_profile()
        for path, expected in (
                (self.python_executable, PYTHON_SHA256),
                (self.fixture_path, FIXTURE_SHA256)):
            if (not path.is_file() or path.is_symlink()
                    or _has_link_component(path) or path.stat().st_nlink != 1
                    or _sha256(path) != expected):
                raise ValueError("source binding")
        return [
            str(self.python_executable.resolve()), "-I", "-S", "-B",
            str(self.fixture_path.resolve()), "--role", "parent",
        ]

    def _environment(self):
        value = {"GENIE_EXECUTION_CLASS": "NO_MODEL_CALL_CONTAINMENT_FIXTURE"}
        for key in ("SystemRoot", "WINDIR"):
            if key in os.environ:
                value[key] = os.environ[key]
        return value

    def _spawn(self, argv, cwd, environment):
        return subprocess.Popen(
            argv, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=cwd, env=environment, close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW)

    def _cleanup_direct(self, process):
        if process is None:
            return True
        clean = True
        try:
            if process.poll() is None:
                process.kill()
        except BaseException:
            clean = False
        try:
            process.wait(timeout=TERMINATION_TIMEOUT_SECONDS)
        except BaseException:
            clean = False
        return clean

    def probe(self, probe_id):
        if type(probe_id) is not str or not _HEX64.fullmatch(probe_id):
            return _reject("INVALID_CONTAINMENT_PROBE_ID")
        try:
            argv = self._validated_profile()
        except Exception:
            return _reject("INVALID_CONTAINMENT_PROFILE")
        with self._lock:
            if self._used:
                return _unknown()
            self._used = True
        process = None
        job = None
        directory = None
        member_handles = []
        reader = None
        assigned = False
        entry_attempted = False
        terminate_attempted = False
        cleanup_ok = True
        outcome = None
        try:
            job = WindowsJob()
            if job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
                raise RuntimeError("job policy mismatch")
            directory = Path(tempfile.mkdtemp(
                prefix="genie-containment-fixture-",
                dir=self.work_root)).resolve()
            cwd = directory
            if _inside_repository(cwd):
                raise ValueError("working directory")
            if argv != self._validated_profile():
                raise ValueError("profile changed")
            entry_attempted = True
            process = self._spawn(argv, cwd, self._environment())
            reader = _OneLineReader(process.stdout)
            reader.start()
            job.assign_process(process)
            assigned = True
            if not job.wait_for_active(1, 1.0):
                raise RuntimeError("unexpected pregate process count")
            active_before_release = job.accounting()["active_processes"]
            process.stdin.write(GATE)
            process.stdin.flush()
            process.stdin.close()
            report_raw = reader.result(REPORT_TIMEOUT_SECONDS)
            report = _strict_json(report_raw)
            if (type(report) is not dict or set(report) != _REPORT_KEYS
                    or report["protocol"] != FIXTURE_PROTOCOL
                    or report["model_invoked"] is not False
                    or report["proposal"] != "NO_MODEL_CALL"
                    or type(report["parent_pid"]) is not int
                    or report["parent_pid"] != process.pid
                    or type(report["descendant_pid"]) is not int
                    or report["descendant_pid"] <= 0
                    or report["descendant_pid"] == process.pid):
                raise ValueError("invalid fixture report")
            if (not job.contains_handle(int(process._handle))
                    or not job.wait_for_active(4, 1.0)):
                raise RuntimeError("process tree membership failed")
            process_ids = job.process_ids()
            if (len(process_ids) != 4 or process.pid not in process_ids
                    or report["descendant_pid"] not in process_ids):
                raise RuntimeError("unexpected process-tree identity")
            for pid in process_ids:
                handle = ProcessWaitHandle(pid)
                member_handles.append(handle)
                if not job.contains_handle(handle.handle):
                    raise RuntimeError("process escaped job")
            image_paths = [
                str(Path(handle.image_path()).resolve())
                for handle in member_handles]
            expected_images = sorted((
                str(PYTHON_PATH.resolve()), str(PYTHON_PATH.resolve()),
                str(_conhost_path().resolve()),
                str(_conhost_path().resolve())))
            if sorted(image_paths) != expected_images:
                raise RuntimeError("unexpected process-tree image")
            accounting_before = job.accounting()
            terminate_attempted = True
            job.terminate(TERMINATION_EXIT_CODE)
            if (not job.wait_for_active(0, TERMINATION_TIMEOUT_SECONDS)
                    or not all(handle.wait(TERMINATION_TIMEOUT_SECONDS)
                               for handle in member_handles)):
                raise RuntimeError("descendant termination not observed")
            process.wait(timeout=TERMINATION_TIMEOUT_SECONDS)
            accounting_after = job.accounting()
            if (any(handle.exit_code() == STILL_ACTIVE
                    for handle in member_handles)
                    or process.poll() is None
                    or not reader.join()
                    or process.stdout.read(REPORT_LIMIT + 1)
                    or process.stderr.read(REPORT_LIMIT + 1)):
                raise RuntimeError("process termination incomplete")
            outcome = {
                "status": "VERIFIED",
                "classification": "NO_MODEL_FIXTURE_CONTAINMENT_EVIDENCE",
                "protocol": PROBE_PROTOCOL,
                "probe_id": probe_id,
                "job_limit_flags": job.limit_flags(),
                "active_before_release": active_before_release,
                "active_before_termination": accounting_before[
                    "active_processes"],
                "active_after_termination": accounting_after[
                    "active_processes"],
                "member_image_counts": {
                    "conhost.exe": 2,
                    "python.exe": 2,
                },
                "parent_terminated": True,
                "descendant_terminated": True,
                "model_invoked": False,
                "allow_new_invocation": False,
                "complete_runtime_closure": False,
                "hostile_preassignment_containment": False,
            }
        except KeyboardInterrupt:
            outcome = _unknown()
        except Exception:
            outcome = _unknown() if entry_attempted else _reject(
                "CONTAINMENT_JOB_CONFIGURATION_FAILED")
        finally:
            if job is not None:
                try:
                    if (assigned and not terminate_attempted
                            and job.accounting()["active_processes"]):
                        terminate_attempted = True
                        job.terminate(TERMINATION_EXIT_CODE)
                        cleanup_ok = job.wait_for_active(
                            0, TERMINATION_TIMEOUT_SECONDS)
                except BaseException:
                    cleanup_ok = False
                try:
                    job.close()
                except BaseException:
                    cleanup_ok = False
            if not self._cleanup_direct(process):
                cleanup_ok = False
            if process is not None:
                try:
                    process._handle.Close()
                    if not process._handle.closed:
                        cleanup_ok = False
                except BaseException:
                    cleanup_ok = False
            if reader is not None and not reader.join():
                cleanup_ok = False
            for handle in member_handles:
                try:
                    if not handle.wait(TERMINATION_TIMEOUT_SECONDS):
                        cleanup_ok = False
                    handle.close()
                except BaseException:
                    cleanup_ok = False
            for pipe in (() if process is None else (
                    process.stdin, process.stdout, process.stderr)):
                try:
                    pipe.close()
                except BaseException:
                    cleanup_ok = False
            if directory is not None and cleanup_ok:
                removed = False
                for _attempt in range(20):
                    try:
                        if directory.exists():
                            shutil.rmtree(directory)
                        if not directory.exists():
                            removed = True
                            break
                    except OSError:
                        pass
                    time.sleep(0.01)
                if not removed:
                    cleanup_ok = False
        if not cleanup_ok:
            return _unknown() if entry_attempted else _reject(
                "CONTAINMENT_JOB_CONFIGURATION_FAILED")
        return outcome


__all__ = [
    "FIXTURE_SHA256",
    "NoModelProcessTreeContainmentProbe",
    "PYTHON_PATH",
    "PYTHON_SHA256",
    "selected_runtime_profile",
]

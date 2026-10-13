from __future__ import annotations

import ast
import concurrent.futures
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from shared_interfaces import process_containment as subject
from shared_interfaces import windows_job


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "phase2b2b_containment" / "process_tree_fixture.py"
HOST_PYTHON = Path(
    r"C:\Users\aaron\Documents\Codex\phase2a-venv\Scripts\python.exe")
CHILD_PYTHON = Path(
    r"C:\Users\aaron\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe")
EXPECTED_FIXTURE_SHA256 = (
    "43e7517997d1f0c9d97bfd03f8fa696ef52f978cb638206ca76acbacc9835389")
EXPECTED_RUNTIME = {
    "host_python.exe": (
        HOST_PYTHON, 277808,
        "dcdc8a4ef3c108d7d11f7a8afea50502c8f41763d118f1a94dafc90c74f1614c",
        1),
    "child_python.exe": (
        CHILD_PYTHON, 107312,
        "d41bad46673f64e0d02f23797f53f90ccf60f27d6eda8d86dd2d4bbeae5a858c",
        1),
    "python312.dll": (
        CHILD_PYTHON.parent / "python312.dll", 6985520,
        "8bb70bceffd5877733a957b31c392ca027bd2f84230e00de1654f994422fa2af",
        1),
    "python3.dll": (
        CHILD_PYTHON.parent / "python3.dll", 71984,
        "0366ee3d630c26ffc27bfab162648ae8c5cadc74b4b46f3e179ca70f4436cab9",
        1),
    "DLLs/_ctypes.pyd": (
        CHILD_PYTHON.parent / "DLLs" / "_ctypes.pyd", 131888,
        "926df1f47c2a782ba154d6824a84aee7197a32eb6b781c2fc33120851e0fb53b",
        1),
    "kernel32.dll": (
        Path(r"C:\Windows\System32\kernel32.dll"), 815520,
        "70f1e69a1d0602ec9e02c713ff2fc1238ddc7fe02ad28fa344954dda446e5236",
        2),
    "conhost.exe": (
        Path(r"C:\Windows\System32\conhost.exe"), 1044480,
        "2266b396ef92534a2a2844438df043d4069a2ec47d4e464f55e8c1cd47124a98",
        2),
}
EXPECTED_UNKNOWN = {
    "status": "UNKNOWN",
    "reason": "PROCESS_TREE_CONTAINMENT_OUTCOME_UNKNOWN",
    "preserve": True,
    "allow_new_invocation": False,
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def imported_roots(path):
    result = set()
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


class FailingInput:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def write(self, _value):
        raise OSError("injected release failure")

    def flush(self):
        self.wrapped.flush()

    def close(self):
        self.wrapped.close()


class DeliveredGateInput:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.write_calls = 0
        self.close_calls = 0

    def write(self, value):
        self.write_calls += 1
        return self.wrapped.write(value)

    def flush(self):
        return self.wrapped.flush()

    def close(self):
        self.close_calls += 1
        self.wrapped.close()
        if self.close_calls == 1:
            raise OSError("injected post-delivery close uncertainty")


class ReleaseFailureProbe(subject.NoModelProcessTreeContainmentProbe):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processes = []

    def _spawn(self, argv, cwd, environment):
        process = super()._spawn(argv, cwd, environment)
        self.processes.append(process)
        process.stdin = FailingInput(process.stdin)
        return process


class DeliveredGateFailureProbe(subject.NoModelProcessTreeContainmentProbe):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processes = []

    def _spawn(self, argv, cwd, environment):
        process = super()._spawn(argv, cwd, environment)
        self.processes.append(process)
        process.stdin = DeliveredGateInput(process.stdin)
        return process


class UncertainCleanupProbe(subject.NoModelProcessTreeContainmentProbe):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cwd = None
        self.processes = []

    def _spawn(self, argv, cwd, environment):
        self.cwd = Path(cwd)
        process = super()._spawn(argv, cwd, environment)
        self.processes.append(process)
        return process

    def _cleanup_direct(self, process):
        super()._cleanup_direct(process)
        return False


class Tests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(Path(sys.executable).resolve(), HOST_PYTHON.resolve())
        self.assertEqual(digest(HOST_PYTHON), EXPECTED_RUNTIME[
            "host_python.exe"][2])
        self.temporary = tempfile.TemporaryDirectory(
            prefix="genie-phase2b2b-tests-")
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    def probe(self, cls=subject.NoModelProcessTreeContainmentProbe,
              root=None, python=CHILD_PYTHON, fixture=FIXTURE):
        return cls(
            work_root=self.root if root is None else Path(root),
            python_executable=Path(python), fixture_path=Path(fixture))

    def test_selected_runtime_profile_is_exact_and_explicitly_partial(self):
        profile = subject.selected_runtime_profile()
        self.assertEqual(
            profile["classification"],
            "PARTIAL_SELECTED_RUNTIME_SUPPORT_SET")
        self.assertIs(profile["complete_runtime_closure"], False)
        self.assertEqual(profile["python_executable"], str(HOST_PYTHON.resolve()))
        self.assertEqual(
            profile["python_version"],
            "3.12.14 (main, Aug 25 2026, 14:01:42) "
            "[MSC v.1944 64 bit (AMD64)]")
        self.assertEqual(profile["windows_version"], {
            "major": 10,
            "minor": 0,
            "build": 22631,
            "platform": 2,
            "service_pack": "",
            "service_pack_major": 0,
            "service_pack_minor": 0,
            "suite_mask": 768,
            "product_type": 1,
            "platform_version": [10, 0, 22621],
        })
        self.assertEqual(set(profile["files"]), set(EXPECTED_RUNTIME))
        for name, (path, size, sha256, links) in EXPECTED_RUNTIME.items():
            with self.subTest(name=name):
                self.assertEqual(profile["files"][name], {
                    "path": str(path.resolve()),
                    "sha256": sha256,
                    "bytes": size,
                    "hardlink_count": links,
                })
                self.assertEqual(digest(path), sha256)

    def test_job_object_layout_policy_and_empty_accounting_are_exact(self):
        self.assertEqual(windows_job._check_structure_layout(), (64, 48, 144, 48))
        job = windows_job.WindowsJob()
        try:
            self.assertEqual(
                job.limit_flags(),
                windows_job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
            self.assertEqual(
                job.limit_flags() & (
                    windows_job.JOB_OBJECT_LIMIT_BREAKAWAY_OK
                    | windows_job.JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK),
                0)
            self.assertEqual(job.accounting(), {
                "total_processes": 0,
                "active_processes": 0,
                "terminated_processes": 0,
            })
            self.assertEqual(job.process_ids(), ())
        finally:
            job.close()

    def test_real_probe_gates_then_terminates_every_observed_member_once(self):
        real_popen = subject.subprocess.Popen
        captured = []

        def inspect_popen(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            captured.append((process, list(argv), dict(kwargs)))
            return process

        probe = self.probe()
        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=inspect_popen):
            result = probe.probe("1" * 64)
            repeated = probe.probe("2" * 64)
        self.assertEqual(result, {
            "status": "VERIFIED",
            "classification": "NO_MODEL_FIXTURE_CONTAINMENT_EVIDENCE",
            "protocol": "genie-process-tree-containment-preflight-v1",
            "probe_id": "1" * 64,
            "job_limit_flags": 8192,
            "active_before_release": 1,
            "active_before_termination": 4,
            "active_after_termination": 0,
            "member_image_counts": {"conhost.exe": 2, "python.exe": 2},
            "parent_terminated": True,
            "descendant_terminated": True,
            "model_invoked": False,
            "allow_new_invocation": False,
            "complete_runtime_closure": False,
            "hostile_preassignment_containment": False,
        })
        self.assertEqual(repeated, EXPECTED_UNKNOWN)
        self.assertEqual(len(captured), 1)
        process, argv, kwargs = captured[0]
        self.assertIsNotNone(process.poll())
        self.assertTrue(process._handle.closed)
        self.assertEqual(argv, [
            str(CHILD_PYTHON.resolve()), "-I", "-S", "-B",
            str(FIXTURE.resolve()), "--role", "parent",
        ])
        self.assertIs(kwargs["shell"], False)
        self.assertIs(kwargs["stdin"], subprocess.PIPE)
        self.assertIs(kwargs["stdout"], subprocess.PIPE)
        self.assertIs(kwargs["stderr"], subprocess.PIPE)
        self.assertIs(kwargs["close_fds"], True)
        self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)
        self.assertFalse(Path(kwargs["cwd"]).exists())
        expected_environment = {"GENIE_EXECUTION_CLASS"}
        for key in ("SystemRoot", "WINDIR"):
            if key in os.environ:
                expected_environment.add(key)
        self.assertEqual(set(kwargs["env"]), expected_environment)
        self.assertEqual(
            kwargs["env"]["GENIE_EXECUTION_CLASS"],
            "NO_MODEL_CALL_CONTAINMENT_FIXTURE")
        for key in (
                "OPENAI_API_KEY", "CODEX_HOME", "GENIE_TOKEN", "PATH",
                "HOME", "USERPROFILE"):
            self.assertNotIn(key, kwargs["env"])

    def test_invalid_inputs_and_substituted_sources_reject_before_entry(self):
        with mock.patch.object(subject, "WindowsJob") as job, \
                mock.patch.object(subject.subprocess, "Popen") as popen:
            self.assertEqual(
                self.probe().probe("bad"),
                {"status": "REJECT", "reason": "INVALID_CONTAINMENT_PROBE_ID"})
            job.assert_not_called()
            popen.assert_not_called()

        with tempfile.TemporaryDirectory(prefix="wrong-probe-root-") as wrong:
            with mock.patch.object(subject, "WindowsJob") as job, \
                    mock.patch.object(subject.subprocess, "Popen") as popen:
                self.assertEqual(
                    self.probe(root=Path(wrong).resolve()).probe("3" * 64)[
                        "status"], "REJECT")
                job.assert_not_called()
                popen.assert_not_called()

        with mock.patch.object(subject, "_sha256", return_value="0" * 64), \
                mock.patch.object(subject, "WindowsJob") as job, \
                mock.patch.object(subject.subprocess, "Popen") as popen:
            self.assertEqual(self.probe().probe("4" * 64)["status"], "REJECT")
            job.assert_not_called()
            popen.assert_not_called()

        self.assertEqual(
            self.probe(fixture=ROOT / "phase2b2a_launcher"
                       / "no_model_fixture.py").probe("5" * 64)["status"],
            "REJECT")

    def test_job_configuration_failure_is_preentry_reject_and_not_retried(self):
        probe = self.probe()
        with mock.patch.object(
                subject, "WindowsJob", side_effect=OSError("injected")), \
                mock.patch.object(subject.subprocess, "Popen") as popen:
            first = probe.probe("6" * 64)
            second = probe.probe("6" * 64)
        self.assertEqual(first, {
            "status": "REJECT",
            "reason": "CONTAINMENT_JOB_CONFIGURATION_FAILED",
        })
        self.assertEqual(second, EXPECTED_UNKNOWN)
        popen.assert_not_called()

    def test_assignment_failure_is_unknown_reaped_and_never_retried(self):
        real_popen = subject.subprocess.Popen
        processes = []

        def capture(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            processes.append(process)
            return process

        probe = self.probe()
        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(
                    subject.WindowsJob, "assign_process",
                    side_effect=OSError("injected assignment failure")):
            first = probe.probe("7" * 64)
            second = probe.probe("7" * 64)
        self.assertEqual(first, EXPECTED_UNKNOWN)
        self.assertEqual(second, EXPECTED_UNKNOWN)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_postcommit_assignment_uncertainty_uses_kill_on_close_once(self):
        real_popen = subject.subprocess.Popen
        real_assign = subject.WindowsJob.assign_process
        real_terminate = subject.WindowsJob.terminate
        processes = []
        assignment_calls = []
        termination_calls = []

        def capture(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            processes.append(process)
            return process

        def assign_then_raise(job, process):
            real_assign(job, process)
            assignment_calls.append(process.pid)
            raise OSError("injected postcommit assignment uncertainty")

        def terminate_spy(job, exit_code):
            termination_calls.append(exit_code)
            return real_terminate(job, exit_code)

        probe = self.probe()
        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(
                    subject.WindowsJob, "assign_process",
                    new=assign_then_raise), \
                mock.patch.object(
                    subject.WindowsJob, "terminate", new=terminate_spy):
            first = probe.probe("7" * 64)
            second = probe.probe("7" * 64)
        self.assertEqual(first, EXPECTED_UNKNOWN)
        self.assertEqual(second, EXPECTED_UNKNOWN)
        self.assertEqual(len(assignment_calls), 1)
        self.assertEqual(termination_calls, [])
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertEqual(
            list(self.root.glob("genie-containment-fixture-*")), [])

    def test_release_failure_is_unknown_reaped_and_never_retried(self):
        probe = self.probe(cls=ReleaseFailureProbe)
        first = probe.probe("8" * 64)
        second = probe.probe("8" * 64)
        self.assertEqual(first, EXPECTED_UNKNOWN)
        self.assertEqual(second, EXPECTED_UNKNOWN)
        self.assertEqual(len(probe.processes), 1)
        self.assertIsNotNone(probe.processes[0].poll())

    def test_delivered_gate_close_uncertainty_is_not_replayed(self):
        real_terminate = subject.WindowsJob.terminate
        termination_calls = []

        def terminate_spy(job, exit_code):
            termination_calls.append(exit_code)
            return real_terminate(job, exit_code)

        probe = self.probe(cls=DeliveredGateFailureProbe)
        with mock.patch.object(
                subject.WindowsJob, "terminate", new=terminate_spy):
            first = probe.probe("8" * 64)
            second = probe.probe("8" * 64)
        self.assertEqual(first, EXPECTED_UNKNOWN)
        self.assertEqual(second, EXPECTED_UNKNOWN)
        self.assertEqual(len(probe.processes), 1)
        self.assertEqual(probe.processes[0].stdin.write_calls, 1)
        self.assertEqual(len(termination_calls), 1)
        self.assertIsNotNone(probe.processes[0].poll())
        self.assertEqual(
            list(self.root.glob("genie-containment-fixture-*")), [])

    def test_cleanup_uncertainty_preserves_cwd_after_closing_process_handle(self):
        probe = self.probe(cls=UncertainCleanupProbe)
        result = probe.probe("f" * 64)
        self.assertEqual(result, EXPECTED_UNKNOWN)
        self.assertEqual(len(probe.processes), 1)
        self.assertIsNotNone(probe.processes[0].poll())
        self.assertTrue(probe.processes[0]._handle.closed)
        self.assertIsNotNone(probe.cwd)
        self.assertTrue(probe.cwd.is_dir())
        shutil.rmtree(probe.cwd)
        self.assertFalse(probe.cwd.exists())

    def test_sources_are_rehashed_after_job_creation_before_process_entry(self):
        real_sha256 = subject._sha256
        fixture_reads = [0]

        def changed_after_first_profile(path):
            if Path(path).resolve() == FIXTURE.resolve():
                fixture_reads[0] += 1
                if fixture_reads[0] >= 2:
                    return "0" * 64
            return real_sha256(path)

        probe = self.probe()
        with mock.patch.object(
                subject, "_sha256", side_effect=changed_after_first_profile), \
                mock.patch.object(subject.subprocess, "Popen") as popen:
            first = probe.probe("9" * 64)
            second = probe.probe("9" * 64)
        self.assertEqual(first, {
            "status": "REJECT",
            "reason": "CONTAINMENT_JOB_CONFIGURATION_FAILED",
        })
        self.assertEqual(second, {
            "status": "REJECT",
            "reason": "INVALID_CONTAINMENT_PROFILE",
        })
        self.assertGreaterEqual(fixture_reads[0], 2)
        popen.assert_not_called()

    def test_popen_failure_is_post_entry_unknown_without_retry(self):
        probe = self.probe()
        with mock.patch.object(
                subject.subprocess, "Popen",
                side_effect=OSError("injected process-entry uncertainty")) as popen:
            first = probe.probe("a" * 64)
            second = probe.probe("a" * 64)
        self.assertEqual(first, EXPECTED_UNKNOWN)
        self.assertEqual(second, EXPECTED_UNKNOWN)
        self.assertEqual(popen.call_count, 1)

    def test_malformed_report_is_unknown_and_job_reaps_tree(self):
        real_popen = subject.subprocess.Popen
        processes = []

        def capture(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            processes.append(process)
            return process

        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(
                    subject, "_strict_json",
                    side_effect=ValueError("injected malformed report")):
            for index in range(20):
                with self.subTest(index=index):
                    result = self.probe().probe(f"{index:064x}")
                    self.assertEqual(result, EXPECTED_UNKNOWN)
                    self.assertEqual(
                        list(self.root.glob("genie-containment-fixture-*")), [])
        self.assertEqual(len(processes), 20)
        self.assertTrue(all(process.poll() is not None for process in processes))

    def test_report_read_then_timeout_is_unknown_and_reaps_four_members(self):
        real_popen = subject.subprocess.Popen
        real_result = subject._OneLineReader.result
        real_terminate = subject.WindowsJob.terminate
        processes = []
        stable_four_members = []
        members_before_termination = []

        def capture(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            processes.append(process)
            return process

        def read_then_timeout(reader, timeout):
            real_result(reader, timeout)
            raise TimeoutError("injected post-report timeout uncertainty")

        def terminate_spy(job, exit_code):
            stable_four_members.append(job.wait_for_active(4, 1.0))
            members_before_termination.append(job.process_ids())
            return real_terminate(job, exit_code)

        probe = self.probe()
        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(
                    subject._OneLineReader, "result", new=read_then_timeout), \
                mock.patch.object(
                    subject.WindowsJob, "terminate", new=terminate_spy):
            first = probe.probe("b" * 64)
            second = probe.probe("b" * 64)
        self.assertEqual(first, EXPECTED_UNKNOWN)
        self.assertEqual(second, EXPECTED_UNKNOWN)
        self.assertEqual(stable_four_members, [True])
        self.assertEqual(len(members_before_termination), 1)
        self.assertEqual(len(members_before_termination[0]), 4)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertEqual(
            list(self.root.glob("genie-containment-fixture-*")), [])

    def test_termination_api_failure_falls_back_to_kill_on_close_and_unknown(self):
        real_popen = subject.subprocess.Popen
        processes = []

        def capture(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            processes.append(process)
            return process

        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture), \
                mock.patch.object(
                    subject.WindowsJob, "terminate",
                    side_effect=OSError(
                        "injected termination failure")) as terminate:
            for index in range(10):
                with self.subTest(index=index):
                    result = self.probe().probe(f"{index + 64:064x}")
                    self.assertEqual(result, EXPECTED_UNKNOWN)
                    self.assertEqual(
                        list(self.root.glob("genie-containment-fixture-*")), [])
        self.assertEqual(terminate.call_count, 10)
        self.assertEqual(len(processes), 10)
        self.assertTrue(all(process.poll() is not None for process in processes))

    def test_concurrent_calls_share_one_instance_and_spawn_exactly_once(self):
        barrier = threading.Barrier(2)
        counter_lock = threading.Lock()
        profile_calls = [0]
        real_popen = subject.subprocess.Popen
        processes = []

        class ConcurrentProbe(subject.NoModelProcessTreeContainmentProbe):
            def _validated_profile(self):
                value = super()._validated_profile()
                with counter_lock:
                    profile_calls[0] += 1
                    initial = profile_calls[0] <= 2
                if initial:
                    barrier.wait(timeout=5)
                return value

        def capture(argv, **kwargs):
            process = real_popen(argv, **kwargs)
            processes.append(process)
            return process

        probe = self.probe(cls=ConcurrentProbe)
        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(probe.probe, ("d" * 64, "e" * 64)))
        self.assertEqual(
            sorted(result["status"] for result in results),
            ["UNKNOWN", "VERIFIED"])
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_kill_on_close_terminates_all_four_observed_members(self):
        probe = self.probe()
        argv = probe._validated_profile()
        job = windows_job.WindowsJob()
        process = None
        handles = []
        try:
            with tempfile.TemporaryDirectory(
                    prefix="genie-close-fixture-", dir=self.root) as directory:
                process = probe._spawn(
                    argv, Path(directory).resolve(), probe._environment())
                job.assign_process(process)
                self.assertTrue(job.wait_for_active(1, 1.0))
                process.stdin.write(subject.GATE)
                process.stdin.flush()
                process.stdin.close()
                raw = process.stdout.readline(subject.REPORT_LIMIT + 2)
                report = subject._strict_json(raw[:-1])
                self.assertEqual(report["parent_pid"], process.pid)
                self.assertTrue(job.wait_for_active(4, 1.0))
                ids = job.process_ids()
                self.assertEqual(len(ids), 4)
                handles = [windows_job.ProcessWaitHandle(pid) for pid in ids]
                self.assertEqual(
                    sorted(Path(handle.image_path()).name.lower()
                           for handle in handles),
                    ["conhost.exe", "conhost.exe", "python.exe", "python.exe"])
                job.close()
                self.assertTrue(all(handle.wait(3.0) for handle in handles))
                process.wait(timeout=3.0)
                self.assertTrue(all(
                    handle.exit_code() != windows_job.STILL_ACTIVE
                    for handle in handles))
        finally:
            if getattr(job, "_handle", 0):
                job.close()
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=3.0)
            for handle in handles:
                handle.close()
            if process is not None:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    try:
                        pipe.close()
                    except Exception:
                        pass

    def test_imports_and_calls_exclude_models_network_genie_mcp_and_retry(self):
        self.assertEqual(imported_roots(FIXTURE), {
            "__future__", "json", "os", "pathlib", "subprocess", "sys", "time",
        })
        self.assertEqual(
            imported_roots(ROOT / "shared_interfaces" / "windows_job.py"),
            {"__future__", "ctypes", "os", "time"})
        self.assertEqual(
            imported_roots(ROOT / "shared_interfaces" / "process_containment.py"),
            {"__future__", "hashlib", "json", "os", "pathlib", "re",
             "shutil", "subprocess", "sys", "tempfile", "threading", "time",
             "shared_interfaces"})
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (
                FIXTURE,
                ROOT / "shared_interfaces" / "windows_job.py",
                ROOT / "shared_interfaces" / "process_containment.py"))
        for forbidden in (
                "openai", "mcp.server", "advance_run", "apply_run_event",
                "session_driver", "run_control", "run_events", "requests.",
                "urllib.", "socket.", "shell=true", "os.environ.copy"):
            self.assertNotIn(forbidden, combined)
        probe_source = inspect.getsource(
            subject.NoModelProcessTreeContainmentProbe.probe)
        self.assertEqual(probe_source.count("self._spawn("), 1)
        self.assertNotIn("retry", probe_source.lower())
        self.assertNotIn("refund", probe_source.lower())
        self.assertNotIn("reset", probe_source.lower())

    def test_phase2b2a_manifest_and_bound_sources_remain_byte_exact(self):
        manifest_path = ROOT / "phase2b2a_launcher" / "SOURCE_MANIFEST.json"
        self.assertEqual(
            digest(manifest_path),
            "c8fb2ca22a45c1d8958d927540e4493297610a177d54bb0eb34ccf9c55186684")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["file_count"], 12)
        self.assertEqual(manifest["total_bytes"], 84351)
        self.assertEqual(sum(item["bytes"] for item in manifest["files"]), 84351)
        for item in manifest["files"]:
            with self.subTest(path=item["path"]):
                path = ROOT / item["path"]
                self.assertEqual(path.stat().st_size, item["bytes"])
                self.assertEqual(digest(path), item["sha256"])
        self.assertEqual(digest(FIXTURE), EXPECTED_FIXTURE_SHA256)
        self.assertEqual(subject.FIXTURE_SHA256, EXPECTED_FIXTURE_SHA256)


if __name__ == "__main__":
    unittest.main()

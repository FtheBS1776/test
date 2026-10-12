from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest import mock

from shared_interfaces import isolated_worker as subject


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "phase2b2a_launcher" / "no_model_fixture.py"
CODEX = Path(
    r"C:\Users\aaron\AppData\Roaming\npm\node_modules\@openai\codex"
    r"\node_modules\@openai\codex-win32-x64\vendor"
    r"\x86_64-pc-windows-msvc\bin\codex.exe")
EXPECTED_FIXTURE_SHA256 = (
    "09bb17ed56dbe1f844fd4909a9ee322c37607d4cc0cea61cfd3e4a0944c0179f")
EXPECTED_PYTHON_SHA256 = (
    "dcdc8a4ef3c108d7d11f7a8afea50502c8f41763d118f1a94dafc90c74f1614c")
EXPECTED_CODEX_VERSION = "0.162.1"
EXPECTED_FIXTURE_MODES = {
    "success", "crash", "nonzero", "timeout", "malformed", "oversize",
    "stderr_oversize", "invalid_utf8", "duplicate", "nonfinite", "extra",
    "wrong_hash", "wrong_protocol", "wrong_stdin", "wrong_argv",
    "wrong_environment", "repository_true", "model_true", "wrong_proposal",
    "wrong_classification", "stderr", "missing",
}
EXPECTED_DISABLED_CODEX_FEATURES = (
    "apps", "plugins", "multi_agent", "remote_plugin", "auth_elicitation",
    "tool_call_mcp_elicitation", "browser_use", "browser_use_external",
    "browser_use_full_cdp_access", "computer_use", "in_app_browser",
    "image_generation", "hooks", "shell_tool", "shell_snapshot", "unified_exec",
    "unified_exec_tty", "view_image", "workspace_dependencies", "skill_search",
    "skill_mcp_dependency_install", "tool_suggest", "daemon_auto_start",
    "worktrees", "code_mode_host", "sleep_tool", "system_proxy_fallback",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request(marker="bounded request"):
    return {
        "instruction": marker,
        "materials": ["fixture material"],
        "constraints": ["return a proposal only"],
    }


def claim_rows(path):
    connection = sqlite3.connect(path)
    try:
        return connection.execute(
            "SELECT launch_id,request_sha256,state,result_sha256"
            " FROM launch_claims ORDER BY launch_id").fetchall()
    finally:
        connection.close()


class CountingLauncher(subject.NoModelFixtureWorkerLauncher):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawn_calls = 0

    def _spawn_once(self, argv, payload, request_sha256):
        self.spawn_calls += 1
        return super()._spawn_once(argv, payload, request_sha256)


class Tests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(
            Path(sys.executable).resolve(), subject.FIXTURE_PYTHON_PATH.resolve(),
            "exact Phase 2A CPython path is required")
        self.assertEqual(
            digest(Path(sys.executable)), EXPECTED_PYTHON_SHA256,
            "exact Phase 2A CPython executable is required")
        self.assertEqual(subject.FIXTURE_PYTHON_SHA256, EXPECTED_PYTHON_SHA256)
        self.temporary = tempfile.TemporaryDirectory(
            prefix="genie-phase2b2a-tests-")
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    def launcher(self, mode="success", cls=CountingLauncher, fixture=FIXTURE):
        return cls(
            claim_db=self.root / subject.CLAIM_STORE_NAME,
            work_root=self.root,
            python_executable=Path(sys.executable).resolve(),
            fixture_path=Path(fixture).resolve(),
            mode=mode)

    def test_success_is_one_untrusted_no_model_fixture_return(self):
        launcher = self.launcher()
        launch_id = "1" * 64
        marker = "PROMPT_SECRET_MUST_NOT_ECHO"
        with mock.patch.dict(os.environ, {
                "OPENAI_API_KEY": "sk-must-not-pass",
                "CODEX_HOME": "must-not-pass",
                "GENIE_TOKEN": "must-not-pass",
                "PATH": "must-not-pass",
        }, clear=False):
            result = launcher.launch_worker(launch_id, request(marker))
        self.assertEqual(result["status"], "RETURNED")
        self.assertEqual(
            result["classification"], "UNTRUSTED_NO_MODEL_FIXTURE_OUTPUT")
        self.assertEqual(result["proposal"], "NO_MODEL_CALL")
        self.assertIs(result["fixture_only"], True)
        self.assertIs(result["allow_new_invocation"], False)
        self.assertNotIn(marker, repr(result))
        self.assertNotIn("sk-must-not-pass", repr(result))
        self.assertEqual(launcher.spawn_calls, 1)
        rows = claim_rows(self.root / subject.CLAIM_STORE_NAME)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], launch_id)
        self.assertEqual(rows[0][2], "RETURNED")
        self.assertRegex(rows[0][3], r"\A[0-9a-f]{64}\Z")

    def test_real_spawn_uses_no_shell_bounded_stdin_minimal_env_and_fresh_cwd(self):
        launcher = self.launcher()
        real_popen = subject.subprocess.Popen
        captured = {}

        def inspect_popen(argv, **kwargs):
            captured["argv"] = list(argv)
            captured["kwargs"] = dict(kwargs)
            captured["cwd"] = Path(kwargs["cwd"])
            captured["cwd_exists_during_spawn"] = captured["cwd"].is_dir()
            captured["claim_state_during_spawn"] = claim_rows(
                launcher.claim_db)[0][2]
            return real_popen(argv, **kwargs)

        marker = "--mode crash PROMPT_IN_STDIN_ONLY"
        with mock.patch.object(subject.subprocess, "Popen", side_effect=inspect_popen):
            result = launcher.launch_worker("2" * 64, request(marker))
        self.assertEqual(result["status"], "RETURNED")
        self.assertIs(captured["kwargs"]["shell"], False)
        self.assertNotIn(marker, repr(captured["argv"]))
        self.assertEqual(
            captured["argv"], [
                str(Path(sys.executable).resolve()), "-I", "-S", "-B",
                str(FIXTURE.resolve()), "--mode", "success"])
        self.assertEqual(captured["claim_state_during_spawn"], "CLAIMED")
        expected_environment = {"GENIE_EXECUTION_CLASS"}
        for key in ("SystemRoot", "WINDIR"):
            if key in os.environ:
                expected_environment.add(key)
        self.assertEqual(
            set(captured["kwargs"]["env"]), expected_environment)
        self.assertEqual(
            captured["kwargs"]["env"]["GENIE_EXECUTION_CLASS"],
            "NO_MODEL_CALL_FIXTURE")
        for key in (
                "OPENAI_API_KEY", "CODEX_HOME", "GENIE_TOKEN", "PATH", "HOME",
                "USERPROFILE"):
            self.assertNotIn(key, captured["kwargs"]["env"])
        self.assertTrue(captured["cwd_exists_during_spawn"])
        self.assertFalse(captured["cwd"].exists())
        self.assertFalse(any(
            (path / ".git").exists()
            for path in (captured["cwd"], *captured["cwd"].parents)))
        self.assertEqual(captured["kwargs"]["close_fds"], True)
        self.assertIs(captured["kwargs"]["stdin"], subject.subprocess.PIPE)
        self.assertIs(captured["kwargs"]["stdout"], subject.subprocess.PIPE)
        self.assertIs(captured["kwargs"]["stderr"], subject.subprocess.PIPE)
        self.assertEqual(
            captured["kwargs"]["creationflags"],
            subject.subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    def test_bad_input_rejects_before_claim_and_spawn(self):
        cases = [
            ("bad", request()),
            ("3" * 64, None),
            ("3" * 64, {}),
            ("3" * 64, {**request(), "extra": True}),
            ("3" * 64, {**request(), "instruction": ""}),
            ("3" * 64, {**request(), "instruction": "x\x00y"}),
            ("3" * 64, {**request(), "instruction": "x" * 16385}),
            ("3" * 64, {**request(), "materials": ["x"] * 9}),
            ("3" * 64, {**request(), "constraints": ["x"] * 17}),
            ("3" * 64, {**request(), "materials": [1]}),
            ("3" * 64, {**request(), "constraints": [None]}),
        ]
        for index, (launch_id, value) in enumerate(cases):
            with self.subTest(index=index):
                launcher = self.launcher()
                result = launcher.launch_worker(launch_id, value)
                self.assertEqual(result["status"], "REJECT")
                self.assertEqual(launcher.spawn_calls, 0)
                self.assertFalse((self.root / subject.CLAIM_STORE_NAME).exists())

    def test_final_stdin_envelope_is_bounded_before_claim(self):
        value = {
            "instruction": "i" * 16384,
            "materials": ["m" * 8192] * 5,
            "constraints": ["c" * 480] * 15 + ["z" * 679],
        }
        request_raw = subject._canonical(value)
        request_sha256 = hashlib.sha256(request_raw).hexdigest()
        envelope = subject._canonical({
            "protocol": subject.REQUEST_PROTOCOL,
            "classification": "BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT",
            "request_sha256": request_sha256,
            "request": value,
        })
        self.assertLessEqual(len(request_raw), 65536)
        self.assertEqual(len(envelope), 65537)
        self.assertEqual(subject.MAX_STDIN_BYTES, 65536)
        launcher = self.launcher()
        result = launcher.launch_worker("3" * 64, value)
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertFalse((self.root / subject.CLAIM_STORE_NAME).exists())

    def test_profile_and_source_binding_fail_before_claim(self):
        changed = self.root / "changed_fixture.py"
        changed.write_bytes(FIXTURE.read_bytes() + b"\n# changed\n")
        cases = [
            dict(mode="not-a-mode"),
            dict(fixture=changed),
        ]
        for index, values in enumerate(cases):
            with self.subTest(index=index):
                launcher = self.launcher(**values)
                result = launcher.launch_worker("4" * 64, request())
                self.assertEqual(result["status"], "REJECT")
                self.assertEqual(launcher.spawn_calls, 0)
                self.assertFalse((self.root / subject.CLAIM_STORE_NAME).exists())

        launcher = CountingLauncher(
            claim_db=self.root / subject.CLAIM_STORE_NAME,
            work_root=ROOT,
            python_executable=Path(sys.executable).resolve(),
            fixture_path=FIXTURE,
            mode="success")
        result = launcher.launch_worker("4" * 64, request())
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(launcher.spawn_calls, 0)

    def test_profile_is_immutable_and_rejects_aliases_relative_paths_and_bad_digest(self):
        launcher = self.launcher()
        with self.assertRaises(AttributeError):
            launcher._profile = launcher._profile
        with self.assertRaises(AttributeError):
            launcher.mode = "crash"

        relative = CountingLauncher(
            claim_db=Path(subject.CLAIM_STORE_NAME),
            work_root=Path("."),
            python_executable=Path(sys.executable).resolve(),
            fixture_path=FIXTURE,
            mode="success")
        self.assertEqual(
            relative.launch_worker("4" * 64, request())["status"], "REJECT")
        self.assertEqual(relative.spawn_calls, 0)

        alias = self.root / "fixture-alias.py"
        os.link(FIXTURE, alias)
        aliased = self.launcher(fixture=alias)
        self.assertEqual(
            aliased.launch_worker("4" * 64, request())["status"], "REJECT")
        self.assertEqual(aliased.spawn_calls, 0)

        real_sha256 = subject._sha256

        def wrong_interpreter_digest(path):
            if Path(path).resolve() == Path(sys.executable).resolve():
                return "0" * 64
            return real_sha256(path)

        with mock.patch.object(
                subject, "_sha256", side_effect=wrong_interpreter_digest):
            rejected = self.launcher().launch_worker("4" * 64, request())
        self.assertEqual(rejected["status"], "REJECT")

        wrong_name = CountingLauncher(
            claim_db=self.root / "wrong.sqlite",
            work_root=self.root,
            python_executable=Path(sys.executable).resolve(),
            fixture_path=FIXTURE,
            mode="success")
        self.assertEqual(
            wrong_name.launch_worker("4" * 64, request())["status"], "REJECT")
        self.assertEqual(wrong_name.spawn_calls, 0)

    def test_non_sqlite_or_wrong_schema_store_rejects_without_overwrite(self):
        store = self.root / subject.CLAIM_STORE_NAME
        store.write_bytes(b"NOT SQLITE")
        before = store.read_bytes()
        launcher = self.launcher()
        result = launcher.launch_worker("5" * 64, request())
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertEqual(store.read_bytes(), before)

    def test_triggered_claim_store_is_rejected_before_claim_or_spawn(self):
        store = self.root / subject.CLAIM_STORE_NAME
        connection = sqlite3.connect(store)
        try:
            connection.execute(subject._CLAIM_TABLE_SQL)
            connection.execute(
                "CREATE TRIGGER delete_claim AFTER INSERT ON launch_claims "
                "BEGIN DELETE FROM launch_claims WHERE launch_id=NEW.launch_id; END")
            connection.commit()
        finally:
            connection.close()
        before = store.read_bytes()
        launcher = self.launcher()
        result = launcher.launch_worker("5" * 64, request())
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertEqual(store.read_bytes(), before)

        store.unlink()
        connection = sqlite3.connect(store)
        try:
            connection.execute("CREATE TABLE launch_claims(wrong TEXT)")
            connection.commit()
        finally:
            connection.close()
        before = store.read_bytes()
        launcher = self.launcher()
        result = launcher.launch_worker("5" * 64, request())
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertEqual(store.read_bytes(), before)

    def test_hardlinked_claim_store_is_rejected_without_writing(self):
        backing = self.root / "backing.sqlite"
        connection = sqlite3.connect(backing)
        try:
            connection.execute(subject._CLAIM_TABLE_SQL)
            connection.commit()
        finally:
            connection.close()
        store = self.root / subject.CLAIM_STORE_NAME
        os.link(backing, store)
        before = backing.read_bytes()
        launcher = self.launcher()
        result = launcher.launch_worker("5" * 64, request())
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertEqual(backing.read_bytes(), before)

    def test_claim_hardlink_injected_after_profile_is_unknown_without_spawn(self):
        backing = self.root / "late-backing.sqlite"

        class LateAliasLauncher(CountingLauncher):
            def _claim_once(self, launch_id, request_sha256):
                connection = sqlite3.connect(backing)
                try:
                    connection.execute(subject._CLAIM_TABLE_SQL)
                    connection.commit()
                finally:
                    connection.close()
                os.link(backing, self.claim_db)
                return super()._claim_once(launch_id, request_sha256)

        launcher = self.launcher(cls=LateAliasLauncher)
        result = launcher.launch_worker("5" * 64, request())
        self.assertEqual(result, {
            "status": "UNKNOWN",
            "reason": "ISOLATED_WORKER_OUTCOME_UNKNOWN",
            "preserve": True,
            "allow_new_invocation": False,
        })
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertEqual(claim_rows(backing), [])

    def test_sources_are_rehashed_after_claim_before_popen(self):
        real_sha256 = subject._sha256
        fixture_reads = [0]

        def changed_after_claim(path):
            if Path(path).resolve() == FIXTURE.resolve():
                fixture_reads[0] += 1
                if fixture_reads[0] >= 2:
                    return "0" * 64
            return real_sha256(path)

        launcher = self.launcher()
        with mock.patch.object(
                subject, "_sha256", side_effect=changed_after_claim), \
                mock.patch.object(subject.subprocess, "Popen") as popen:
            first = launcher.launch_worker("5" * 64, request())
        self.assertEqual(first["status"], "UNKNOWN")
        popen.assert_not_called()
        self.assertEqual(
            claim_rows(self.root / subject.CLAIM_STORE_NAME)[0][2], "CLAIMED")
        self.assertEqual(
            launcher.launch_worker("5" * 64, request())["status"], "UNKNOWN")

    def test_duplicate_and_cross_request_never_spawn_again(self):
        launcher = self.launcher()
        launch_id = "6" * 64
        first = launcher.launch_worker(launch_id, request("first"))
        second = launcher.launch_worker(launch_id, request("first"))
        crossed = launcher.launch_worker(launch_id, request("crossed"))
        self.assertEqual(first["status"], "RETURNED")
        for result in (second, crossed):
            self.assertEqual(result, {
                "status": "UNKNOWN",
                "reason": "ISOLATED_WORKER_OUTCOME_UNKNOWN",
                "preserve": True,
                "allow_new_invocation": False,
            })
        self.assertEqual(launcher.spawn_calls, 1)
        self.assertEqual(
            len(claim_rows(self.root / subject.CLAIM_STORE_NAME)), 1)

    def test_concurrent_same_claim_has_exactly_one_spawn(self):
        barrier = threading.Barrier(2)
        lock = threading.Lock()
        spawn_count = [0]

        class ConcurrentLauncher(subject.NoModelFixtureWorkerLauncher):
            def _validated_profile(self):
                result = super()._validated_profile()
                barrier.wait(timeout=5)
                return result

            def _spawn_once(self, argv, payload, request_sha256):
                with lock:
                    spawn_count[0] += 1
                return super()._spawn_once(argv, payload, request_sha256)

        launchers = [self.launcher(cls=ConcurrentLauncher) for _ in range(2)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda item: item.launch_worker("7" * 64, request()),
                launchers))
        self.assertEqual(
            sorted(result["status"] for result in results),
            ["RETURNED", "UNKNOWN"])
        self.assertEqual(spawn_count[0], 1)
        self.assertEqual(
            len(claim_rows(self.root / subject.CLAIM_STORE_NAME)), 1)

    def test_exception_after_claim_is_unknown_and_not_retried(self):
        class FailingLauncher(CountingLauncher):
            def _spawn_once(self, argv, payload, request_sha256):
                self.spawn_calls += 1
                raise RuntimeError("after claim")

        launcher = self.launcher(cls=FailingLauncher)
        first = launcher.launch_worker("8" * 64, request())
        second = launcher.launch_worker("8" * 64, request())
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertEqual(second["status"], "UNKNOWN")
        self.assertEqual(launcher.spawn_calls, 1)
        self.assertEqual(
            claim_rows(self.root / subject.CLAIM_STORE_NAME)[0][2], "CLAIMED")

    def test_keyboard_interrupt_after_claim_is_unknown_and_not_retried(self):
        class InterruptedLauncher(CountingLauncher):
            def _spawn_once(self, argv, payload, request_sha256):
                self.spawn_calls += 1
                raise KeyboardInterrupt()

        launcher = self.launcher(cls=InterruptedLauncher)
        first = launcher.launch_worker("8" * 64, request())
        second = launcher.launch_worker("8" * 64, request())
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertEqual(second["status"], "UNKNOWN")
        self.assertEqual(launcher.spawn_calls, 1)
        self.assertEqual(
            claim_rows(self.root / subject.CLAIM_STORE_NAME)[0][2], "CLAIMED")

    def test_exception_after_committed_claim_never_reaches_spawn(self):
        class PostCommitFailure(CountingLauncher):
            def _claim_once(self, launch_id, request_sha256):
                claimed = super()._claim_once(launch_id, request_sha256)
                if claimed:
                    raise RuntimeError("return path lost after commit")
                return claimed

        launcher = self.launcher(cls=PostCommitFailure)
        first = launcher.launch_worker("8" * 64, request())
        second = launcher.launch_worker("8" * 64, request())
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertEqual(second["status"], "UNKNOWN")
        self.assertEqual(launcher.spawn_calls, 0)
        self.assertEqual(
            claim_rows(self.root / subject.CLAIM_STORE_NAME)[0][2], "CLAIMED")

    def test_distinct_launch_ids_are_distinct_trusted_parent_decisions(self):
        launcher = self.launcher()
        first = launcher.launch_worker("b" * 64, request("same request"))
        second = launcher.launch_worker("c" * 64, request("same request"))
        self.assertEqual(first["status"], "RETURNED")
        self.assertEqual(second["status"], "RETURNED")
        self.assertEqual(launcher.spawn_calls, 2)
        self.assertEqual(
            len(claim_rows(self.root / subject.CLAIM_STORE_NAME)), 2)

    def test_lost_return_record_is_unknown_and_not_retried(self):
        class LostReturnLauncher(CountingLauncher):
            def _record_return(self, launch_id, request_sha256, result_sha256):
                raise RuntimeError("lost return")

        launcher = self.launcher(cls=LostReturnLauncher)
        first = launcher.launch_worker("9" * 64, request())
        second = launcher.launch_worker("9" * 64, request())
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertEqual(second["status"], "UNKNOWN")
        self.assertEqual(launcher.spawn_calls, 1)
        self.assertEqual(
            claim_rows(self.root / subject.CLAIM_STORE_NAME)[0][2], "CLAIMED")

    def test_all_child_failures_are_canonical_unknown_without_retry(self):
        self.assertEqual(subject.FIXTURE_MODES, EXPECTED_FIXTURE_MODES)
        modes = sorted(EXPECTED_FIXTURE_MODES - {"success"})
        for index, mode in enumerate(modes, start=10):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(
                        prefix="genie-phase2b2a-mode-") as directory:
                    root = Path(directory).resolve()
                    launcher = CountingLauncher(
                        claim_db=root / subject.CLAIM_STORE_NAME,
                        work_root=root,
                        python_executable=Path(sys.executable).resolve(),
                        fixture_path=FIXTURE,
                        mode=mode)
                    launch_id = f"{index:064x}"
                    first = launcher.launch_worker(launch_id, request())
                    second = launcher.launch_worker(launch_id, request())
                    self.assertEqual(first, {
                        "status": "UNKNOWN",
                        "reason": "ISOLATED_WORKER_OUTCOME_UNKNOWN",
                        "preserve": True,
                        "allow_new_invocation": False,
                    })
                    self.assertEqual(second, first)
                    self.assertEqual(launcher.spawn_calls, 1)
                    self.assertEqual(
                        claim_rows(root / subject.CLAIM_STORE_NAME)[0][2],
                        "CLAIMED")

    def test_real_timeout_direct_child_is_reaped_and_same_id_not_respawned(self):
        launcher = self.launcher(mode="timeout")
        real_popen = subject.subprocess.Popen
        processes = []

        def capture_process(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        with mock.patch.object(
                subject.subprocess, "Popen", side_effect=capture_process):
            first = launcher.launch_worker("e" * 64, request())
            second = launcher.launch_worker("e" * 64, request())
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertEqual(second["status"], "UNKNOWN")
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertEqual(launcher.spawn_calls, 1)

    def test_request_is_detached_before_claim_hook_mutation(self):
        value = request("original")

        class MutatingLauncher(CountingLauncher):
            def _claim_once(self, launch_id, request_sha256):
                value["instruction"] = "mutated after snapshot"
                value["materials"].append("mutated")
                return super()._claim_once(launch_id, request_sha256)

        launcher = self.launcher(cls=MutatingLauncher)
        result = launcher.launch_worker("a" * 64, value)
        self.assertEqual(result["status"], "RETURNED")
        expected = request("original")
        self.assertEqual(
            result["request_sha256"],
            hashlib.sha256(subject._canonical(expected)).hexdigest())

    def test_launcher_does_not_add_launch_id_to_argv_or_stdin(self):
        class CaptureLauncher(CountingLauncher):
            def _spawn_once(self, argv, payload, request_sha256):
                self.captured_argv = list(argv)
                self.captured_payload = bytes(payload)
                return super()._spawn_once(argv, payload, request_sha256)

        launcher = self.launcher(cls=CaptureLauncher)
        launch_id = "d" * 64
        result = launcher.launch_worker(launch_id, request("payload marker"))
        self.assertEqual(result["status"], "RETURNED")
        self.assertNotIn(launch_id, repr(launcher.captured_argv))
        self.assertNotIn(launch_id.encode("ascii"), launcher.captured_payload)
        decoded = subject._strict_json(launcher.captured_payload)
        self.assertEqual(
            decoded["classification"],
            "BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT")

    def test_transport_exception_attempts_direct_process_kill_and_reap(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdout = mock.Mock()
        process.stderr = mock.Mock()
        process.poll.side_effect = RuntimeError("poll failure")
        process.wait.return_value = 7
        with self.assertRaisesRegex(RuntimeError, "uncertain child transport"):
            subject._communicate_bounded(process, b"{}")
        process.kill.assert_called_once_with()
        process.wait.assert_called()

    def test_pipe_bounds_accept_exact_limit_and_flag_one_byte_over(self):
        for limit in (subject.MAX_STDOUT_BYTES, subject.MAX_STDERR_BYTES):
            with self.subTest(limit=limit, case="exact"):
                output = bytearray()
                overflow = threading.Event()
                errors = []
                subject._read_bounded(
                    io.BytesIO(b"x" * limit), limit, output, overflow, errors)
                self.assertEqual(len(output), limit)
                self.assertFalse(overflow.is_set())
                self.assertEqual(errors, [])
            with self.subTest(limit=limit, case="one-over"):
                output = bytearray()
                overflow = threading.Event()
                errors = []
                subject._read_bounded(
                    io.BytesIO(b"x" * (limit + 1)), limit, output,
                    overflow, errors)
                self.assertEqual(len(output), limit + 1)
                self.assertTrue(overflow.is_set())
                self.assertEqual(errors, [])

    @unittest.skipUnless(CODEX.is_file(), "reviewed local Codex CLI not installed")
    def test_deferred_codex_plan_is_pinned_closed_and_never_executed(self):
        self.assertEqual(digest(CODEX), subject.CODEX_CLI_SHA256)
        with mock.patch.object(subject.subprocess, "Popen") as popen:
            plan = subject.deferred_codex_worker_plan(CODEX)
        popen.assert_not_called()
        self.assertEqual(plan["status"], "DEFERRED_NOT_EXECUTABLE")
        self.assertEqual(plan["codex_version"], EXPECTED_CODEX_VERSION)
        self.assertEqual(subject.CODEX_CLI_VERSION, EXPECTED_CODEX_VERSION)
        self.assertEqual(plan["model"], None)
        self.assertEqual(plan["authentication"], "NOT_PROVISIONED")
        self.assertEqual(plan["effective_tool_inventory"], "NOT_PROBED")
        self.assertEqual(
            plan["stdin"], "BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT")
        argv = plan["argv_template"]
        self.assertEqual(CODEX.resolve(), subject.CODEX_CLI_PATH.resolve())
        self.assertEqual(
            subject.DISABLED_CODEX_FEATURES,
            EXPECTED_DISABLED_CODEX_FEATURES)
        expected_argv = [
            str(CODEX.resolve()), "exec", "--ignore-user-config",
            "--ignore-rules", "--ephemeral", "--strict-config", "--sandbox",
            "read-only", "--skip-git-repo-check", "--output-schema",
            "<absolute-parent-generated-schema>", "--output-last-message",
            "<absolute-parent-generated-result>", "--color", "never",
        ]
        for feature in EXPECTED_DISABLED_CODEX_FEATURES:
            expected_argv.extend(("--disable", feature))
        expected_argv.append("-")
        self.assertEqual(argv, expected_argv)
        self.assertNotIn("--model", argv)
        self.assertNotIn("CODEX_HOME", repr(argv))

    def test_deferred_codex_plan_rejects_wrong_executable_without_spawn(self):
        fake = self.root / "codex.exe"
        fake.write_bytes(b"not codex")
        with mock.patch.object(subject.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(ValueError, "CODEX_CLI_SOURCE_BINDING"):
                subject.deferred_codex_worker_plan(fake)
        popen.assert_not_called()

    def test_direct_sources_have_no_genie_mutation_mcp_or_network_reference(self):
        source = (ROOT / "shared_interfaces" / "isolated_worker.py").read_text()
        fixture = FIXTURE.read_text()
        for forbidden in (
                "run_control", "run_events", "session_driver", "advance_run",
                "apply_run_event", "drive_run", "serve_run", "mcp.server",
                "socket.", "requests.", "urllib.", "shell=True",
                "os.environ.copy"):
            self.assertNotIn(forbidden, source)
        for forbidden in (
                "subprocess", "socket", "requests", "urllib", "openai", "codex"):
            self.assertNotIn(forbidden, fixture.lower())
        self.assertEqual(digest(FIXTURE), EXPECTED_FIXTURE_SHA256)
        self.assertEqual(subject.FIXTURE_SHA256, EXPECTED_FIXTURE_SHA256)


if __name__ == "__main__":
    unittest.main()

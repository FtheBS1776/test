import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from shared_interfaces import live_codex_worker as worker


TOKEN = {
    "run_id": "run", "task_id": "task", "input_sha256": "1" * 64,
    "attempt": 1, "slot_id": "2" * 64, "call_id": "3" * 64,
}


class _Stream:
    def close(self):
        pass


class _Process:
    pid = 123
    _handle = 456
    stdin = _Stream()
    stdout = _Stream()
    stderr = _Stream()


class _BrokenJob:
    thread = None

    def assign_process(self, _process):
        raise OSError("assignment failed")

    def terminate(self, _code):
        pass

    def wait_for_active(self, _expected, _timeout):
        return True

    def close(self):
        pass


class LiveWorkerTests(unittest.TestCase):
    def test_logical_identity_binds_every_token_field(self):
        first, _ = worker.logical_operation_id(
            TOKEN, __file__, "v", "a" * 64)
        for key in TOKEN:
            changed = dict(TOKEN)
            changed[key] = (2 if key == "attempt" else "different")
            second, _ = worker.logical_operation_id(
                changed, __file__, "v", "a" * 64)
            self.assertNotEqual(first, second, key)

    def test_operation_ledger_rejects_duplicate_and_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operations.sqlite"
            ledger = worker.OperationLedger(path)
            self.assertTrue(ledger.claim("a" * 64, {"x": 1}))
            self.assertFalse(ledger.claim("a" * 64, {"x": 1}))
            with self.assertRaisesRegex(ValueError, "NOT_FRESH"):
                ledger.claim("b" * 64, {"x": 2})
            ledger.finish("a" * 64, "UNKNOWN", {"failure": True})
            connection = sqlite3.connect(path)
            try:
                row = connection.execute(
                    "SELECT state,preserve,allow_new_invocation FROM operation"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(row, ("UNKNOWN", 1, 0))

    def test_child_environment_contains_no_authority_values(self):
        with mock.patch.dict(os.environ, {
                "OPENAI_API_KEY": "secret", "GENIE_TOKEN": "authority",
                "SystemRoot": r"C:\Windows", "PATH": r"C:\Windows"},
                clear=True):
            value = worker.child_environment(r"C:\codex-home")
        self.assertNotIn("OPENAI_API_KEY", value)
        self.assertNotIn("GENIE_TOKEN", value)
        self.assertIn("CODEX_HOME", value)

    def test_command_disables_authority_surfaces(self):
        args = worker.command_line(__file__)
        pairs = list(zip(args, args[1:]))
        for feature in worker.DISABLED_FEATURES:
            self.assertIn(("--disable", feature), pairs)
        self.assertIn(("-c", "mcp_servers={}"), pairs)
        self.assertIn(("-c", "sandbox_mode=\"read-only\""), pairs)
        self.assertLess(args.index("--strict-config"), args.index("app-server"))

    def test_inventory_must_be_empty_and_apps_disabled(self):
        valid = {"config": {"mcp_servers": {}, "apps": {
            "_default": {"enabled": False}}, "sandbox_mode": "read-only"}}
        self.assertEqual(worker._validate_inventory(valid, {"data": []})[
                         "mcp_tool_count"], 0)
        with self.assertRaisesRegex(RuntimeError, "NONEMPTY"):
            worker._validate_inventory(valid, {"data": [{"name": "x"}]})
        with self.assertRaisesRegex(RuntimeError, "NONEMPTY"):
            worker._validate_inventory({"config": {"mcp_servers": {
                "genie": {}}, "apps": {"_default": {"enabled": False}},
                "sandbox_mode": "read-only"}}, {"data": []})

    def test_worker_output_is_exact_and_duplicate_is_rejected(self):
        item = {"method": "item/completed", "params": {"item": {
            "type": "agentMessage", "text": json.dumps({
                "marker": "LOCAL_WORKER_OK_20261013",
                "visible_tool_or_mcp_names": [], "authority_request": False})}}}
        text, value = worker._assistant_text([item])
        self.assertEqual(json.loads(text), value)
        with self.assertRaisesRegex(RuntimeError, "COUNT"):
            worker._assistant_text([item, item])

    def test_post_entry_assignment_failure_is_unknown_and_not_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "scratch"
            scratch.mkdir()
            ledger = Path(directory) / "trial" / "ledger.sqlite"
            ledger.parent.mkdir()
            with mock.patch.object(
                worker, "file_sha256", return_value="a" * 64), mock.patch.object(
                worker.subprocess, "Popen", return_value=_Process()), mock.patch.object(
                worker, "WindowsJob", return_value=_BrokenJob()):
                result = worker.run_once(
                    token=TOKEN, ledger_path=ledger,
                    executable=__file__, version="codex-cli 0.162.1",
                    codex_home=directory, working_directory=scratch)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertTrue(result["preserve"])
        self.assertFalse(result["allow_new_invocation"])

    def test_popen_uncertainty_is_unknown_and_never_retried(self):
        broken = _BrokenJob()
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "scratch"
            scratch.mkdir()
            ledger = Path(directory) / "trial" / "ledger.sqlite"
            ledger.parent.mkdir()
            with mock.patch.object(worker, "file_sha256", return_value="a" * 64), \
                    mock.patch.object(worker.subprocess, "Popen",
                                      side_effect=OSError("uncertain")) as popen, \
                    mock.patch.object(worker, "WindowsJob", return_value=broken):
                result = worker.run_once(
                    token=TOKEN, ledger_path=ledger,
                    executable=__file__, version="codex-cli 0.162.1",
                    codex_home=directory, working_directory=scratch)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["allow_new_invocation"])


if __name__ == "__main__":
    unittest.main()

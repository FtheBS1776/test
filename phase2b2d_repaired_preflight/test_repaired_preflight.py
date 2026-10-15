from pathlib import Path
import queue
import tempfile
import time
import unittest
from unittest import mock

from phase2b2c_preflight import recovery_preflight as preflight
from phase2b2d_repaired_preflight import run_preflight_once as runner


class RepairedRecoveryPreflightTests(unittest.TestCase):
    def test_fresh_context_changes_logical_operation_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "codex.exe"
            executable.write_bytes(b"codex")
            prior = preflight._binding(executable, runner.VERSION)
            repaired = preflight._binding(
                executable, runner.VERSION, runner.OPERATION_CONTEXT)
        self.assertNotEqual(prior[0], repaired[0])
        self.assertEqual(
            repaired[1]["operation_context"], runner.OPERATION_CONTEXT)

    def test_runner_uses_isolated_trial_and_no_semantic_surface(self):
        self.assertEqual(runner.TRIAL.name, "trial")
        self.assertEqual(runner.TRIAL.parent.name,
                         "phase2b2d_repaired_preflight")
        prior_ledger = (runner.ROOT / "phase2b2c_preflight" / "trial" /
                        "preflight_operation.db")
        self.assertNotEqual(runner.LEDGER.resolve(), prior_ledger.resolve())
        self.assertEqual(preflight.PROTOCOL_REQUEST_METHODS, (
            "initialize", "config/read", "mcpServerStatus/list", "model/list"))

    def test_empty_receive_poll_is_not_terminal_before_deadline(self):
        rpc = object.__new__(preflight.live._JsonRpc)
        rpc.messages = mock.Mock()
        rpc.messages.get.side_effect = [
            queue.Empty(),
            ("message", {"id": 7, "result": {"ready": True}}),
        ]
        notifications = []
        result = rpc.wait_response(7, time.monotonic() + 1, notifications)
        self.assertEqual(result, {"ready": True})
        self.assertEqual(notifications, [])

    def test_failure_capture_precedes_termination_in_source(self):
        source = Path(preflight.__file__).read_text(encoding="utf-8")
        capture = source.index('evidence["failure_members_before_termination"]')
        terminate = source.index("job.terminate(0x2B2C)", capture)
        self.assertLess(capture, terminate)


if __name__ == "__main__":
    unittest.main()

"""CLI entry versus outcome uncertainty; deterministic owned files, no model."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from standalone_app import cli, owner
from shared_interfaces.status_tool import _load_core


class CliOutcomeTests(unittest.TestCase):
    def invoke(self, args, raw=b"{}"):
        output = io.StringIO()
        with patch.object(cli.sys, "stdin", types.SimpleNamespace(buffer=io.BytesIO(raw))), redirect_stdout(output):
            code = cli.main(args)
        return code, json.loads(output.getvalue())

    def test_failure_after_stop_effect_is_unknown_not_bad_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue, work = root / "queue.sqlite", root / "work"
            work.mkdir()
            runner = _load_core().load_runner()
            runner.q.initialize(queue, {"run_id": "cli-stop-test", "max_tasks": 1,
                "max_model_calls": 1, "effect_scope": "owned-local-report-inbox"})
            runs = {"actual": {"queue": str(queue), "owned_root": str(work), "run_id": "cli-stop-test"}}
            original = runner.q.stop

            def committed_but_lost(path, reason):
                original(path, reason)
                raise OSError("private acknowledgement detail")

            with patch.object(owner, "_load_control_chain", return_value=(None, None, runner)), patch.object(
                    owner, "_live_runs", return_value=runs), patch.object(
                    runner.q, "stop", side_effect=committed_but_lost) as stop:
                code, result = self.invoke(["stop", "actual"])
            stop.assert_called_once_with(str(queue), "HOST_ENDED")
            self.assertEqual(code, 3)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertTrue(result["preserve"])
            self.assertFalse(result["allow_new_invocation"])
            self.assertNotIn("private", json.dumps(result))
            saved = runner.q.status(queue)
            self.assertEqual((saved["state"], saved["stop_reason"]), ("STOPPED", "HOST_ENDED"))
            self.assertEqual(saved["reserved_model_calls"], 0)

    def test_bad_json_is_rejected_before_owner_entry(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]', b'x'*65537):
            with self.subTest(raw=raw[:30]), patch.object(owner, "create_first_run") as create:
                code, result = self.invoke(["create"], raw)
                self.assertEqual((code, result["status"]), (2, "REJECT"))
                create.assert_not_called()

    def test_known_rejection_and_successful_stop_keep_their_meaning(self):
        with patch.object(owner, "stop", side_effect=owner.OwnerError("OWNER_INPUT_INVALID")):
            self.assertEqual(self.invoke(["stop", "actual"]),
                             (2, {"status": "REJECT", "reason": "OWNER_INPUT_INVALID"}))
        with patch.object(owner, "stop", return_value={"state": "STOPPED", "reason": "HOST_ENDED"}):
            self.assertEqual(self.invoke(["stop", "actual"]),
                             (0, {"state": "STOPPED", "reason": "HOST_ENDED"}))


if __name__ == "__main__":
    unittest.main()

import json
import hashlib
import ast
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from phase2b2s_attested_live_pilot import attested_worker as subject


TOKEN = {"run_id": "run", "task_id": "task", "input_sha256": "1" * 64,
         "attempt": 1, "slot_id": "2" * 64, "call_id": "3" * 64}


class AttestedWorkerTests(unittest.TestCase):
    def test_command_binds_exact_empty_capability_operation(self):
        args = subject.command_line(__file__, ".", "a" * 64)
        self.assertIn("--no-tools", args)
        self.assertEqual(args[args.index(
            "--capability-snapshot-operation-id") + 1], "a" * 64)
        self.assertIn("--ignore-user-config", args)
        self.assertIn("mcp_servers={}", args)
        self.assertEqual(args[-1], "-")

    def test_logical_identity_binds_every_dispatch_token_field(self):
        first, _ = subject.logical_operation_id(
            TOKEN, __file__, "a" * 64)
        for key in TOKEN:
            changed = dict(TOKEN)
            changed[key] = 2 if key == "attempt" else "changed"
            second, _ = subject.logical_operation_id(
                changed, __file__, "a" * 64)
            self.assertNotEqual(first, second, key)

    def test_result_parser_rejects_duplicate_stale_or_malformed_output(self):
        valid = {"type": "item.completed", "item": {
            "type": "agent_message",
            "text": json.dumps(subject.EXPECTED_RESULT)}}
        raw = (json.dumps(valid) + "\n").encode()
        self.assertEqual(json.loads(subject._assistant_result(raw)),
                         subject.EXPECTED_RESULT)
        with self.assertRaisesRegex(RuntimeError, "RESULT_SHAPE"):
            subject._assistant_result(raw + raw)
        stale = json.loads(json.dumps(valid))
        stale["item"]["text"] = json.dumps({**subject.EXPECTED_RESULT,
                                              "marker": "stale"})
        with self.assertRaisesRegex(RuntimeError, "RESULT_SHAPE"):
            subject._assistant_result((json.dumps(stale) + "\n").encode())

    def test_semantic_request_contains_no_genie_authority_or_paths(self):
        lowered = subject.SEMANTIC_REQUEST.lower()
        for forbidden in ("genie", "queue", "registry", "owned_root",
                          "token", "callback"):
            self.assertNotIn(forbidden, lowered)

    def test_unknown_live_cost_stops_before_process_entry_or_ledger_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(subject.subprocess, "Popen") as popen:
                result = subject.run_once(token=TOKEN, artifact_directory=root,
                    codex_home=root, working_directory=root,
                    ledger_path=root / "operation.sqlite", evidence_directory=root)
            popen.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(result["reason"], "LIVE_COST_BOUND_UNAVAILABLE")
        self.assertTrue(result["preserve"])
        self.assertFalse(result["allow_new_invocation"])

    def test_fresh_synthetic_plan_binds_exact_input(self):
        trial = Path(__file__).resolve().parent / "trial"
        plan = json.loads((trial / "PLAN.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["input_sha256"], hashlib.sha256(
            (trial / "INPUT.md").read_bytes()).hexdigest())
        self.assertEqual(plan["max_attempts"], 1)
        if (trial / "queue.sqlite").exists():
            stop = json.loads((trial / "STOP.json").read_text(encoding="utf-8"))
            self.assertEqual(stop["frontier"],
                             "PHASE_2B2_ATTESTED_LIVE_COMPLETE_NONCLAIM")
            self.assertTrue((trial / "operation.sqlite").exists())
        else:
            self.assertFalse((trial / "operation.sqlite").exists())

    def test_worker_module_imports_no_genie_authority_surface(self):
        tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for forbidden in ("shared_interfaces.run_control",
                          "shared_interfaces.run_events",
                          "shared_interfaces.status_tool",
                          "session_driver"):
            self.assertNotIn(forbidden, imported)


if __name__ == "__main__":
    unittest.main()

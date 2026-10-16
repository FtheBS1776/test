import json
import hashlib
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

    def test_post_entry_assignment_failure_is_unknown_without_retry(self):
        class BrokenJob:
            def __init__(self):
                self.terminated = 0
            def limit_flags(self):
                return subject.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            def assign_process(self, _process):
                raise OSError("assignment failed")
            def terminate(self, _code):
                self.terminated += 1
            def wait_for_active(self, _expected, _timeout):
                return True
            def accounting(self):
                return {"total_processes": 1, "active_processes": 0}
            def close(self):
                pass

        class Stream:
            def close(self):
                pass

        class Process:
            pid = 123
            _handle = 456
            stdin = stdout = stderr = Stream()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact, scratch, evidence = (root / "artifact",
                                            root / "scratch",
                                            root / "evidence")
            artifact.mkdir()
            scratch.mkdir()
            evidence.mkdir()
            raw = b"binary"
            (artifact / "codex.exe").write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            (artifact / "codex.exe.sha256").write_text(
                f"{digest}  codex.exe\n", encoding="ascii")
            with mock.patch.object(subject, "WindowsJob", BrokenJob), \
                    mock.patch.object(subject.subprocess, "Popen",
                                      return_value=Process()) as popen:
                result = subject.run_once(
                    token=TOKEN, artifact_directory=artifact,
                    codex_home=root, working_directory=scratch,
                    ledger_path=evidence / "operation.sqlite",
                    evidence_directory=evidence)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertTrue(result["preserve"])
        self.assertFalse(result["allow_new_invocation"])

    def test_fresh_synthetic_plan_binds_exact_input(self):
        trial = Path(__file__).resolve().parent / "trial"
        plan = json.loads((trial / "PLAN.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["input_sha256"], hashlib.sha256(
            (trial / "INPUT.md").read_bytes()).hexdigest())
        self.assertEqual(plan["max_attempts"], 1)
        self.assertFalse((trial / "queue.sqlite").exists())
        self.assertFalse((trial / "operation.sqlite").exists())


if __name__ == "__main__":
    unittest.main()

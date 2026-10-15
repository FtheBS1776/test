import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from phase2b2o_alpha_recovery_live import recovered_worker as subject


def jsonl(values):
    return b"".join((json.dumps(value) + "\n").encode() for value in values)


class RecoveredWorkerTests(unittest.TestCase):
    def test_command_is_exactly_isolated_and_stdin_gated(self):
        with tempfile.TemporaryDirectory() as root:
            args = subject.command_line("C:/alpha/codex.exe", root)
        self.assertEqual(args[1:3], ["exec", "--ignore-user-config"])
        self.assertEqual(args[-1], "-")
        pairs = list(zip(args, args[1:]))
        self.assertIn(("-c", "mcp_servers={}"), pairs)
        self.assertIn(("--sandbox", "read-only"), pairs)
        for name in ("apps", "plugins", "multi_agent", "shell_tool",
                     "unified_exec", "computer_use", "browser_use"):
            self.assertIn(("--disable", name), pairs)

    def test_plan_and_reasoning_are_data_not_tool_activity(self):
        raw = jsonl([
            {"type": "thread.started", "thread_id": "x"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "reasoning"}},
            {"type": "item.completed", "item": {"type": "plan"}},
            {"type": "item.completed", "item": {"type": "agent_message",
             "text": json.dumps(subject.EXPECTED_RESULT)}},
            {"type": "turn.completed"},
        ])
        summary, messages = subject.classify_events(raw)
        self.assertEqual(summary["classification"], "NO_TOOL_ACTIVITY_OBSERVED")
        self.assertEqual(summary["tool_item_types"], [])
        self.assertEqual(json.loads(messages[0]), subject.EXPECTED_RESULT)

    def test_tool_and_unknown_event_fail_closed(self):
        tool = jsonl([{"type": "item.completed",
                       "item": {"type": "mcp_tool_call"}}])
        self.assertEqual(subject.classify_events(tool)[0]["classification"],
                         "TOOL_ACTIVITY_OBSERVED")
        unknown = jsonl([{"type": "unexpected"}])
        self.assertEqual(subject.classify_events(unknown)[0]["classification"],
                         "UNKNOWN_EVENT_SHAPE")

    def test_evidence_write_is_create_once_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "raw"
            raw = b"evidence"
            self.assertEqual(subject._write_bytes_once(path, raw),
                             hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError, "ALREADY_EXISTS"):
                subject._write_bytes_once(path, raw)

    def test_new_logical_identity_binds_new_marker_and_token(self):
        one = subject.logical_operation_id("one", "C:/alpha/codex.exe", "v", "11")
        two = subject.logical_operation_id("two", "C:/alpha/codex.exe", "v", "11")
        self.assertNotEqual(one[0], two[0])
        self.assertIn(subject.MARKER, subject.SEMANTIC_REQUEST)


if __name__ == "__main__":
    unittest.main()

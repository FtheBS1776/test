import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from phase2b2n_event_evidence_recovery import recovery_preflight as subject


def jsonl(values):
    return b"".join((json.dumps(v) + "\n").encode() for v in values)


class RecoveryPreflightTests(unittest.TestCase):
    def test_unknown_item_is_diagnosed_without_becoming_tool_activity(self):
        raw = jsonl([
            {"type": "item.completed", "item": {"type": "plan"}},
            {"type": "item.completed", "item": {"type": "agent_message",
                                                    "text": "{}"}},
            {"type": "turn.completed"},
        ])
        result = subject.classify_events(raw)
        self.assertEqual(result["classification"], "UNKNOWN_EVENT_SHAPE")
        self.assertEqual(result["unknown_item_types"], ["plan"])
        self.assertEqual(result["tool_item_types"], [])

    def test_tool_item_is_explicitly_reported(self):
        raw = jsonl([{"type": "item.completed",
                      "item": {"type": "mcp_tool_call"}}])
        result = subject.classify_events(raw)
        self.assertEqual(result["classification"], "TOOL_ACTIVITY_OBSERVED")
        self.assertEqual(result["tool_item_types"], ["mcp_tool_call"])

    def test_durable_write_is_create_once_and_readback_bound(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "events.jsonl"
            raw = b'{"type":"turn.completed"}\n'
            observed = subject._write_durable_once(path, raw)
            self.assertEqual(observed, hashlib.sha256(raw).hexdigest())
            self.assertEqual(path.read_bytes(), raw)
            with self.assertRaisesRegex(ValueError, "ALREADY_EXISTS"):
                subject._write_durable_once(path, raw)

    def test_source_has_one_spawn_and_no_model_or_network_client(self):
        source = inspect.getsource(subject.run_once).lower()
        self.assertEqual(source.count("subprocess.popen("), 1)
        self.assertNotIn("for attempt", source)
        self.assertNotIn("while attempt", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)


if __name__ == "__main__":
    unittest.main()

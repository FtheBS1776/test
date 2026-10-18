"""R08 complementary input safeguards on the one maintained consumer."""
import json
import unittest
from unittest.mock import Mock

from shared_interfaces.mcp_consumer import GenieMcpReadonlyConsumer


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.consumer = GenieMcpReadonlyConsumer({})
        self.consumer._adapter.handle = Mock(side_effect=lambda call: {
            "type": "function_call_output", "call_id": call["call_id"],
            "output": '{"status":"REJECT","reason":"UNKNOWN_RUN"}'})

    def test_non_json_types_reject_before_adapter_entry(self):
        for args in ({1: "coerced-key"}, {"run_name": ("coerced-tuple",)}):
            self.assertEqual(self.consumer.call("get_run_status", args)["structuredContent"]["status"], "REJECT")
        self.consumer._adapter.handle.assert_not_called()

    def test_oversized_utf8_arguments_reject_before_adapter_entry(self):
        result = self.consumer.call("get_run_status", {"run_name": "é" * 8192})
        self.assertEqual(result["structuredContent"]["status"], "REJECT")
        self.consumer._adapter.handle.assert_not_called()

    def test_exact_argument_bound_delegates_once_without_semantic_rewrite(self):
        overhead = len(json.dumps({"run_name": ""}, separators=(",", ":")).encode())
        args = {"run_name": "x" * (self.consumer._argument_limit - overhead)}
        result = self.consumer.call("get_run_status", args)
        self.assertEqual(result, {"structuredContent": {"status": "REJECT", "reason": "UNKNOWN_RUN"}})
        self.consumer._adapter.handle.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

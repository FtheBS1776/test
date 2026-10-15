import inspect
from pathlib import Path
import sqlite3
import tempfile
import unittest

from phase2b2c_preflight import recovery_preflight as preflight
from shared_interfaces import live_codex_worker as live


class RecoveryPreflightTests(unittest.TestCase):
    def test_protocol_surface_is_readonly_inventory_only(self):
        self.assertEqual(preflight.PROTOCOL_REQUEST_METHODS, (
            "initialize", "config/read", "mcpServerStatus/list", "model/list"))
        source = inspect.getsource(preflight.run_once)
        self.assertNotIn('"thread/start"', source)
        self.assertNotIn('"turn/start"', source)
        self.assertNotIn("SEMANTIC_REQUEST", source)

    def test_binding_is_stable_and_explicitly_zero_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "codex.exe"
            executable.write_bytes(b"codex")
            first = preflight._binding(executable, "codex-cli test")
            second = preflight._binding(executable, "codex-cli test")
        self.assertEqual(first, second)
        self.assertEqual(first[1]["semantic_request_count"], 0)
        self.assertEqual(first[1]["thread_start_count"], 0)
        self.assertEqual(first[1]["turn_start_count"], 0)

    def test_command_orders_globals_before_app_server(self):
        args = preflight.preflight_command_line(__file__)
        self.assertLess(args.index("--strict-config"), args.index("app-server"))
        self.assertIn(("-c", "mcp_servers={}"), zip(args, args[1:]))
        self.assertNotIn("browser_use_mcp_client", args)
        self.assertIn("browser_use", args)

    def test_model_inventory_rejects_pagination_and_substitution(self):
        valid = {"data": [{"model": live.MODEL,
                            "supportedReasoningEfforts": [{
                                "reasoningEffort": live.REASONING_EFFORT}]}],
                 "nextCursor": None}
        self.assertEqual(preflight._model_inventory(valid)["model_match_count"], 1)
        invalid = dict(valid, nextCursor="more")
        with self.assertRaisesRegex(RuntimeError, "INCOMPLETE"):
            preflight._model_inventory(invalid)
        with self.assertRaisesRegex(RuntimeError, "NOT_ADVERTISED"):
            preflight._model_inventory({"data": [], "nextCursor": None})

    def test_ledger_duplicate_is_terminal_and_state_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preflight.db"
            ledger = preflight.PreflightLedger(path)
            self.assertTrue(ledger.claim("a" * 64, {"kind": "test"}))
            self.assertFalse(ledger.claim("a" * 64, {"kind": "test"}))
            ledger.finish("a" * 64, "UNKNOWN", {"reason": "test"})
            connection = sqlite3.connect(path)
            try:
                row = connection.execute(
                    "SELECT state,preserve,allow_new_invocation FROM operation"
                ).fetchone()
            finally:
                connection.close()
        self.assertEqual(row, ("UNKNOWN", 1, 0))


if __name__ == "__main__":
    unittest.main()

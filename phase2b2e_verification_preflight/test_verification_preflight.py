from pathlib import Path
import tempfile
import unittest

from phase2b2c_preflight import recovery_preflight as preflight
from phase2b2d_repaired_preflight import run_preflight_once as prior_runner
from phase2b2e_verification_preflight import run_preflight_once as runner
from shared_interfaces import live_codex_worker as live


class RecoveryVerificationPreflightTests(unittest.TestCase):
    def test_new_context_has_distinct_logical_operation_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "codex.exe"
            executable.write_bytes(b"codex")
            prior = preflight._binding(
                executable, runner.VERSION, prior_runner.OPERATION_CONTEXT)
            current = preflight._binding(
                executable, runner.VERSION, runner.OPERATION_CONTEXT)
        self.assertNotEqual(prior[0], current[0])
        self.assertEqual(current[1]["operation_context"],
                         runner.OPERATION_CONTEXT)

    def test_trial_and_ledger_are_isolated_from_prior_operations(self):
        prior_paths = {
            runner.ROOT / "phase2b2c_preflight" / "trial" /
            "preflight_operation.db",
            prior_runner.LEDGER,
        }
        self.assertNotIn(runner.LEDGER, prior_paths)

    def test_effective_inventory_requires_every_supported_disable(self):
        features = {name: False
                    for name in preflight.EFFECTIVE_DISABLED_FEATURES}
        config = {"config": {
            "mcp_servers": {}, "apps": {"_default": {"enabled": False}},
            "sandbox_mode": live.SANDBOX_MODE, "features": features}}
        mcp = {"data": [], "nextCursor": None}
        result = preflight._validate_preflight_inventory(config, mcp)
        self.assertEqual(result["mcp_tool_count"], 0)
        features[preflight.EFFECTIVE_DISABLED_FEATURES[0]] = True
        with self.assertRaisesRegex(RuntimeError, "DISABLE_NOT_OBSERVED"):
            preflight._validate_preflight_inventory(config, mcp)

    def test_bound_runtime_does_not_claim_documented_flag_support(self):
        args = preflight.preflight_command_line(__file__)
        self.assertFalse(preflight.BOUND_RUNTIME_SUPPORTS_IGNORE_USER_CONFIG)
        self.assertNotIn("--ignore-user-config", args)

    def test_inventory_observation_records_counts_not_names(self):
        config = {"config": {"mcp_servers": {"sensitive-name": {}},
                             "features": {}}}
        mcp = {"data": [{"name": "sensitive-name"}], "nextCursor": "more"}
        observation = preflight._inventory_observation(config, mcp)
        self.assertEqual(observation["configured_server_count"], 1)
        self.assertEqual(observation["status_item_count"], 1)
        self.assertTrue(observation["next_cursor_present"])
        self.assertNotIn("sensitive-name", repr(observation))

    def test_failure_member_evidence_preserves_partial_capture(self):
        class Unavailable:
            def image_path(self):
                raise OSError("gone")

        evidence = preflight._failure_member_evidence({123: Unavailable()})
        self.assertEqual(evidence, [{"pid": 123,
                                    "identity_observation_error": "OSError"}])


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import tempfile
import unittest

from phase2b2c_preflight import recovery_preflight as preflight
from phase2b2e_verification_preflight import run_preflight_once as prior_runner
from phase2b2f_isolation_preflight import run_preflight_once as runner


class IsolationVerificationPreflightTests(unittest.TestCase):
    def test_new_context_and_repaired_command_bind_distinct_operation(self):
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
        self.assertFalse(preflight.BOUND_RUNTIME_SUPPORTS_IGNORE_USER_CONFIG)
        self.assertNotIn("--ignore-user-config",
                         preflight.preflight_command_line(executable))

    def test_trial_and_ledger_are_isolated_from_prior_operations(self):
        prior_paths = {
            runner.ROOT / "phase2b2c_preflight" / "trial" /
            "preflight_operation.db",
            runner.ROOT / "phase2b2d_repaired_preflight" / "trial" /
            "preflight_operation.db",
            prior_runner.LEDGER,
        }
        self.assertNotIn(runner.LEDGER, prior_paths)


if __name__ == "__main__":
    unittest.main()

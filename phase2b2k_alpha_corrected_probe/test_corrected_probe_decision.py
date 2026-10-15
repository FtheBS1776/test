import inspect
import unittest

from phase2b2k_alpha_corrected_probe import corrected_probe_decision as subject


def observation(**changes):
    values = dict(
        launch_count=1,
        candidate_hash_matched=True,
        arguments=("exec", "--ignore-user-config", "--help"),
        exit_code=0,
        help_lists_required_flag=True,
        original_auth_unchanged=True,
        original_config_unchanged=True,
        alpha_processes_remaining=0,
        prompt_supplied=False,
        model_turn_attempted=False,
    )
    values.update(changes)
    return subject.Observation(**values)


class CorrectedProbeDecisionTests(unittest.TestCase):
    def test_observed_probe_proves_parser_support_only(self):
        decision = subject.decide(observation())
        self.assertEqual(decision.status, "EXEC_PARSER_ACCEPTED_NONCLAIM")
        self.assertTrue(decision.parser_support_proven)
        self.assertFalse(decision.runtime_isolation_proven)
        self.assertFalse(decision.worker_allowed)

    def test_identity_count_and_arguments_are_exact(self):
        self.assertEqual(subject.decide(observation(
            launch_count=2)).reason, "LAUNCH_COUNT_NOT_ONE")
        self.assertEqual(subject.decide(observation(
            candidate_hash_matched=False)).reason,
            "CANDIDATE_IDENTITY_MISMATCH")
        self.assertEqual(subject.decide(observation(
            arguments=("--help",))).reason, "UNEXPECTED_ARGUMENT_VECTOR")

    def test_model_auth_config_and_process_drift_invalidate(self):
        self.assertEqual(subject.decide(observation(
            prompt_supplied=True)).reason, "MODEL_PATH_OUT_OF_SCOPE")
        self.assertEqual(subject.decide(observation(
            original_auth_unchanged=False)).reason, "AUTHENTICATION_CHANGED")
        self.assertEqual(subject.decide(observation(
            original_config_unchanged=False)).reason,
            "CONFIGURATION_CHANGED")
        self.assertEqual(subject.decide(observation(
            alpha_processes_remaining=1)).reason, "ALPHA_PROCESS_REMAINS")

    def test_nonzero_or_missing_help_flag_rejects(self):
        self.assertEqual(subject.decide(observation(
            exit_code=2)).status, "PARSER_PROBE_REJECT_NONCLAIM")
        self.assertEqual(subject.decide(observation(
            help_lists_required_flag=False)).status,
            "PARSER_PROBE_REJECT_NONCLAIM")

    def test_module_has_no_launch_network_or_secret_capability(self):
        source = inspect.getsource(subject)
        for forbidden in (
                "subprocess", "Popen", "CreateProcess", "urllib", "requests",
                "socket", "auth.json", "config.toml"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

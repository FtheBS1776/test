import inspect
import unittest

from phase2b2j_alpha_parser_probe import parser_probe_decision as subject


def observation(**changes):
    values = dict(
        launch_count=1,
        candidate_hash_matched=True,
        arguments=("--ignore-user-config", "--version"),
        exit_code=2,
        unexpected_argument=True,
        original_auth_unchanged=True,
        original_config_unchanged=True,
        alpha_processes_remaining=0,
        model_turn_attempted=False,
    )
    values.update(changes)
    return subject.Observation(**values)


class ParserProbeDecisionTests(unittest.TestCase):
    def test_observed_root_rejection_is_inconclusive_and_not_retryable(self):
        decision = subject.decide(observation())
        self.assertEqual(decision.status,
                         "PARSER_PROBE_INCONCLUSIVE_NONCLAIM")
        self.assertEqual(decision.reason,
                         "ROOT_PARSER_REJECTED_EXEC_SCOPED_FLAG")
        self.assertFalse(decision.retry_allowed)
        self.assertFalse(decision.runtime_flag_support_proven)
        self.assertFalse(decision.live_worker_allowed)

    def test_wrong_launch_count_or_identity_invalidates_evidence(self):
        self.assertEqual(subject.decide(observation(
            launch_count=2)).reason, "LAUNCH_COUNT_NOT_ONE")
        self.assertEqual(subject.decide(observation(
            candidate_hash_matched=False)).reason,
            "CANDIDATE_IDENTITY_MISMATCH")

    def test_auth_config_or_process_residue_invalidates_evidence(self):
        self.assertEqual(subject.decide(observation(
            original_auth_unchanged=False)).reason,
            "AUTHENTICATION_CHANGED")
        self.assertEqual(subject.decide(observation(
            original_config_unchanged=False)).reason,
            "CONFIGURATION_CHANGED")
        self.assertEqual(subject.decide(observation(
            alpha_processes_remaining=1)).reason,
            "ALPHA_PROCESS_REMAINS")

    def test_model_turn_or_argument_drift_invalidates_evidence(self):
        self.assertEqual(subject.decide(observation(
            model_turn_attempted=True)).reason, "MODEL_TURN_OUT_OF_SCOPE")
        self.assertEqual(subject.decide(observation(
            arguments=("exec", "--help"))).reason,
            "UNEXPECTED_ARGUMENT_VECTOR")

    def test_module_has_no_launch_network_or_secret_capability(self):
        source = inspect.getsource(subject)
        for forbidden in (
                "subprocess", "Popen", "CreateProcess", "urllib", "requests",
                "socket", "auth.json", "config.toml"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

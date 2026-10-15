import inspect
import unittest

from phase2b2h_codex_rebind import rebind_decision as subject


INSTALLED = subject.Candidate(
    version="0.162.1",
    channel="stable",
    executable_sha256="installed-digest",
    supports_ignore_user_config=False,
)


class RebindDecisionTests(unittest.TestCase):
    def test_no_supported_stable_candidate_rejects_without_install(self):
        decision = subject.decide(INSTALLED, None)
        self.assertEqual(decision.reason, "NO_SUPPORTED_STABLE_REPLACEMENT")
        self.assertFalse(decision.install_allowed)
        self.assertFalse(decision.rebind_allowed)
        self.assertFalse(decision.process_launch_allowed)

    def test_prerelease_is_not_implicitly_authorized(self):
        candidate = subject.Candidate(
            "0.163.0-alpha.11", "alpha", "different-digest", True)
        decision = subject.decide(INSTALLED, candidate)
        self.assertEqual(decision.reason, "PRERELEASE_NOT_AUTHORIZED")
        self.assertFalse(decision.install_allowed)

    def test_identical_stable_candidate_is_not_a_rebind(self):
        candidate = subject.Candidate(
            "0.162.1", "stable", "installed-digest", False)
        self.assertEqual(
            subject.decide(INSTALLED, candidate).reason,
            "CANDIDATE_NOT_DISTINCT")

    def test_distinct_supported_stable_candidate_still_cannot_launch(self):
        candidate = subject.Candidate(
            "synthetic-next-stable", "stable", "different-digest", True)
        decision = subject.decide(INSTALLED, candidate)
        self.assertEqual(decision.status, "REBIND_READY_NONCLAIM")
        self.assertTrue(decision.install_allowed)
        self.assertTrue(decision.rebind_allowed)
        self.assertFalse(decision.process_launch_allowed)

    def test_module_has_no_install_launch_or_network_capability(self):
        source = inspect.getsource(subject)
        for forbidden in (
                "subprocess", "Popen", "CreateProcess", "npm", "urllib",
                "requests", "socket", "auth.json"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

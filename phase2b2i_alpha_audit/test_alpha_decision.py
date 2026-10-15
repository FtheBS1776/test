import inspect
import unittest

from phase2b2i_alpha_audit import alpha_decision as subject


def candidate(**changes):
    values = dict(
        prerelease_audit_authorized=True,
        registry_integrity_verified=True,
        os_name="win32",
        cpu_arch="x64",
        archive_paths_safe=True,
        lifecycle_scripts=(),
        authenticode_valid=True,
        signer_subject='CN="OpenAI OpCo, LLC", O="OpenAI OpCo, LLC"',
        executable_sha256="alpha-digest",
        installed_executable_sha256="stable-digest",
        required_flag_literal_present=True,
    )
    values.update(changes)
    return subject.StaticCandidate(**values)


class AlphaDecisionTests(unittest.TestCase):
    def test_complete_static_evidence_only_selects_parser_probe_candidate(self):
        decision = subject.decide(candidate())
        self.assertEqual(decision.status, "STATIC_CANDIDATE_NONCLAIM")
        self.assertEqual(decision.next_authorization,
                         "ONE_ALPHA_OFFLINE_PARSER_PROBE")
        self.assertFalse(decision.install_allowed)
        self.assertFalse(decision.execute_allowed)
        self.assertFalse(decision.process_launch_allowed)
        self.assertFalse(decision.runtime_support_proven)
        self.assertFalse(decision.effective_isolation_proven)

    def test_unverified_registry_integrity_rejects(self):
        self.assertEqual(subject.decide(candidate(
            registry_integrity_verified=False)).reason,
            "REGISTRY_INTEGRITY_NOT_VERIFIED")

    def test_unsafe_archive_path_rejects(self):
        self.assertEqual(subject.decide(candidate(
            archive_paths_safe=False)).reason, "UNSAFE_ARCHIVE_PATH")

    def test_lifecycle_scripts_reject(self):
        self.assertEqual(subject.decide(candidate(
            lifecycle_scripts=("postinstall",))).reason,
            "LIFECYCLE_SCRIPTS_PRESENT")

    def test_invalid_or_wrong_signer_rejects(self):
        self.assertEqual(subject.decide(candidate(
            authenticode_valid=False)).reason, "AUTHENTICODE_NOT_VALID")
        self.assertEqual(subject.decide(candidate(
            signer_subject="CN=Someone Else")).reason, "SIGNER_NOT_OPENAI")

    def test_missing_literal_rejects(self):
        self.assertEqual(subject.decide(candidate(
            required_flag_literal_present=False)).reason,
            "REQUIRED_FLAG_LITERAL_ABSENT")

    def test_same_executable_hash_rejects(self):
        self.assertEqual(subject.decide(candidate(
            installed_executable_sha256="alpha-digest")).reason,
            "CANDIDATE_NOT_DISTINCT")

    def test_module_has_no_install_launch_network_or_secret_capability(self):
        source = inspect.getsource(subject)
        for forbidden in (
                "subprocess", "Popen", "CreateProcess", "urllib",
                "requests", "socket", "auth.json", "config.toml"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

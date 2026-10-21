import unittest
from dataclasses import replace

from revocation_policy_transition import (
    SelectionReceipt,
    TransitionAuthorization,
    activate,
    authorization_digest,
    authorization_lineage,
    authorize_current_receipt,
    issue_reference_authorization,
    make_policy,
    policy_digest,
    policy_semantic_digest,
)
from revocation_source_selection import Evidence, Hold


class T(unittest.TestCase):
    def setUp(self):
        self.p0 = make_policy(4, {"ocsp", "crl"}, "ALL_REQUIRED_CONSENSUS")
        self.p1 = make_policy(5, {"ocsp"}, "SINGLE_REQUIRED")
        self.authorization_execution = "AUTHORIZE-179"
        self.execution = "ACTIVATE-179"
        self.a = TransitionAuthorization(
            self.p0.digest, self.p1.digest, 4, 5,
            policy_semantic_digest(self.p0), policy_semantic_digest(self.p1),
            self.authorization_execution, self.execution, "INCUMBENT-WARRANT"
        )
        self.a_digest = authorization_digest(self.a)
        from capability_authority import VerifierSession
        self.session = VerifierSession(authorization_lineage(self.p0))
        self.capability = issue_reference_authorization(self.session, self.p0, self.a)

    def E(self, source, status="good"):
        return Evidence(source, status, True, True, source + "-object", source + "-execution")

    _DEFAULT = object()

    def activate(self, authorization=None, incumbent=None, successor=None, digest=None, execution=None,
                 session=_DEFAULT, capability=_DEFAULT):
        return activate(
            incumbent or self.p0,
            successor or self.p1,
            authorization or self.a,
            self.a_digest if digest is None else digest,
            self.execution if execution is None else execution,
            self.session if session is self._DEFAULT else session,
            self.capability if capability is self._DEFAULT else capability,
        )

    def test_exact_authorized_successor_passes(self):
        self.assertEqual(self.activate(), self.p1)

    def test_authorization_and_activation_executions_are_separately_bound(self):
        self.assertNotEqual(self.a.authorization_execution_id, self.a.activation_execution_id)
        self.assertEqual(self.activate(), self.p1)

    def test_activation_execution_substitution_rejects(self):
        with self.assertRaises(Hold): self.activate(execution="OTHER-ACTIVATION")

    def test_wrong_parent_rejects(self):
        other = make_policy(4, {"crl"}, "SINGLE_REQUIRED")
        with self.assertRaises(Hold): self.activate(incumbent=other)

    def test_generation_skip_rejects(self):
        skipped = make_policy(6, {"ocsp"}, "SINGLE_REQUIRED")
        a = replace(self.a, successor_policy_digest=skipped.digest, successor_generation=6)
        with self.assertRaises(Hold): self.activate(authorization=a, successor=skipped, digest=authorization_digest(a))

    def test_unsupported_successor_mode_cannot_activate(self):
        unsupported = make_policy(5, {"ocsp", "crl"}, "NEWEST_WINS")
        a = replace(
            self.a,
            successor_policy_digest=unsupported.digest,
            successor_policy_semantic_digest=policy_digest(
                unsupported.generation, unsupported.authorized_sources,
                unsupported.mode, unsupported.primary,
            ),
        )
        cap = issue_reference_authorization(self.session, self.p0, a)
        with self.assertRaises(Hold):
            self.activate(authorization=a, successor=unsupported,
                          digest=authorization_digest(a), capability=cap)

    def test_successor_digest_substitution_rejects(self):
        a = replace(self.a, successor_policy_digest="other")
        with self.assertRaises(Hold): self.activate(authorization=a, digest=authorization_digest(a))

    def test_incumbent_digest_substitution_rejects(self):
        a = replace(self.a, incumbent_policy_digest="other")
        with self.assertRaises(Hold): self.activate(authorization=a, digest=authorization_digest(a))

    def test_missing_authorization_rejects(self):
        a = replace(self.a, incumbent_authorization_evidence_digest="")
        with self.assertRaises(Hold): self.activate(authorization=a, digest="anything")

    def test_wrong_authorization_rejects(self):
        with self.assertRaises(Hold): self.activate(digest="wrong")

    def test_missing_execution_identity_rejects(self):
        a = replace(self.a, activation_execution_id="")
        with self.assertRaises(Hold): self.activate(authorization=a, digest="anything", execution="")

    def test_missing_authorization_execution_identity_rejects(self):
        a = replace(self.a, authorization_execution_id="")
        with self.assertRaises(Hold): self.activate(authorization=a, digest="anything")

    def test_old_receipt_under_successor_rejects(self):
        old = SelectionReceipt(self.p0.digest, 4, (self.E("ocsp"), self.E("crl")), "good", "RECEIPT-0")
        self.assertEqual(authorize_current_receipt(self.p0, old), "good")
        with self.assertRaises(Hold): authorize_current_receipt(self.p1, old)

    def test_current_receipt_with_exact_policy_generation_passes(self):
        current = SelectionReceipt(self.p1.digest, 5, (self.E("ocsp"),), "good", "RECEIPT-1")
        self.assertEqual(authorize_current_receipt(self.p1, current), "good")

    def test_semantically_identical_successor_different_digest_requires_exact_authorization(self):
        alias = make_policy(5, {"ocsp"}, "SINGLE_REQUIRED", digest="P1-ALIAS")
        with self.assertRaises(Hold): self.activate(successor=alias)
        exact = replace(self.a, successor_policy_digest=alias.digest)
        cap = issue_reference_authorization(self.session, self.p0, exact)
        self.assertEqual(self.activate(authorization=exact, successor=alias, digest=authorization_digest(exact), capability=cap), alias)

    def test_rollback_from_successor_to_incumbent_is_not_current(self):
        self.activate()
        receipt = SelectionReceipt(self.p0.digest, 4, (self.E("ocsp"), self.E("crl")), "good", "RECEIPT-0")
        with self.assertRaises(Hold): authorize_current_receipt(self.p1, receipt)

    def test_consensus_receipt_does_not_become_single_required_receipt(self):
        old = SelectionReceipt(self.p0.digest, 4, (self.E("ocsp"), self.E("crl")), "good", "RECEIPT-0")
        with self.assertRaises(Hold): authorize_current_receipt(self.p1, old)

    def test_policy_generation_aliasing_rejects(self):
        alias = replace(self.p1, generation=4)
        with self.assertRaises(Hold): self.activate(successor=alias)

    def test_digest_alias_cannot_substitute_changed_semantics(self):
        changed = make_policy(5, {"ocsp", "crl"}, "ALL_REQUIRED_CONSENSUS", digest=self.p1.digest)
        with self.assertRaises(Hold): self.activate(successor=changed)

    def test_authorization_is_content_bound_not_boolean_or_identifier(self):
        # Replacing the proof with a truthy typed object or arbitrary identifier cannot pass.
        with self.assertRaises(Hold): self.activate(authorization=object())
        forged = replace(self.a, incumbent_authorization_evidence_digest="FORGED")
        with self.assertRaises(Hold): self.activate(authorization=forged, digest=self.a_digest)

    def test_missing_authorization_capability_rejects(self):
        with self.assertRaises(Hold): self.activate(capability=None)

    def test_direct_constructed_authorization_capability_rejects(self):
        from capability_authority import AuthorizedEvidence, Evidence as CapabilityEvidence
        fake = AuthorizedEvidence(
            CapabilityEvidence("BRAINS10-REVOCATION-POLICY-AUTHORIZATION-v1", self.a_digest, authorization_lineage(self.p0)),
            "forged",
        )
        with self.assertRaises(Hold): self.activate(capability=fake)

    def test_authorization_capability_wrong_digest_rejects(self):
        from capability_authority import Evidence as CapabilityEvidence
        bad = self.session.authorize(CapabilityEvidence(
            "BRAINS10-REVOCATION-POLICY-AUTHORIZATION-v1", "wrong", authorization_lineage(self.p0)
        ))
        with self.assertRaises(Hold): self.activate(capability=bad)

    def test_authorization_capability_wrong_lineage_rejects(self):
        from capability_authority import Evidence as CapabilityEvidence, VerifierSession
        foreign = VerifierSession("foreign")
        cap = foreign.authorize(CapabilityEvidence(
            "BRAINS10-REVOCATION-POLICY-AUTHORIZATION-v1", self.a_digest, "foreign"
        ))
        with self.assertRaises(Hold): self.activate(session=foreign, capability=cap)


if __name__ == "__main__":
    unittest.main()

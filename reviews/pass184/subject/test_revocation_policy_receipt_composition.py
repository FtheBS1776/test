import unittest
from dataclasses import replace

from revocation_policy_receipt_composition import (
    ComposedReceipt, authorize_composed, revocation_receipt_digest, selection_receipt_digest
)
from revocation_policy_transition import SelectionReceipt, make_policy
from revocation_receipt import Hold, RevocationPolicy, RevocationReceipt
from revocation_source_selection import Evidence


class T(unittest.TestCase):
    def setUp(self):
        self.p0 = make_policy(4, {"ocsp", "crl"}, "ALL_REQUIRED_CONSENSUS")
        self.p1 = make_policy(5, {"crl"}, "SINGLE_REQUIRED")
        self.rp0 = RevocationPolicy(self.p0.digest, 4, "DIRECT_COMPLETE_CRL_V1", "ISS", "crl")
        self.rp1 = RevocationPolicy(self.p1.digest, 5, "DIRECT_COMPLETE_CRL_V1", "ISS", "crl")

    def E(self, source, status="good"):
        return Evidence(source, status, True, True, source + "-object", source + "-execution")

    def C(self, policy, evidence, status="good", execute="COMPOSE-1"):
        selection = SelectionReceipt(policy.digest, policy.generation, tuple(evidence), status, "SELECT-1")
        crl_objects = [item.object_digest for item in evidence if item.source == "crl"]
        crl_object = crl_objects[0] if len(crl_objects) == 1 else "CRL"
        revocation = RevocationReceipt(
            policy.digest, policy.generation, "DIRECT_COMPLETE_CRL_V1", "CERT", "ISS", crl_object,
            status, 100, 200, "TIME", "REVOCATION-1"
        )
        return ComposedReceipt(
            selection, selection_receipt_digest(selection), revocation,
            revocation_receipt_digest(revocation), execute
        )

    def A(self, source, revocation, receipt):
        return authorize_composed(source, revocation, receipt, "CERT", "TIME", (120, 130))

    def test_current_receipt_passes(self):
        current = self.C(self.p1, [self.E("crl", status="good")])
        current = replace(
            current,
            revocation_receipt=replace(current.revocation_receipt, object_digest="crl-object"),
        )
        current = replace(
            current,
            revocation_digest=revocation_receipt_digest(current.revocation_receipt),
        )
        self.assertEqual(self.A(self.p1, self.rp1, current), "good")

    def test_exact_object_join_does_not_require_same_execution_id(self):
        current = self.C(self.p1, [self.E("crl")], execute="COMPOSE-3")
        current = replace(
            current,
            revocation_receipt=replace(current.revocation_receipt, object_digest="crl-object"),
        )
        current = replace(current, revocation_digest=revocation_receipt_digest(current.revocation_receipt))
        self.assertEqual(current.selection_receipt.execution_id, "SELECT-1")
        self.assertEqual(current.revocation_receipt.execution_id, "REVOCATION-1")
        self.assertEqual(self.A(self.p1, self.rp1, current), "good")

    def test_selected_crl_object_substitution_rejects(self):
        current = self.C(self.p1, [self.E("crl", status="good")])
        substituted = replace(
            current,
            revocation_receipt=replace(current.revocation_receipt, object_digest="other-crl"),
        )
        substituted = replace(
            substituted,
            revocation_digest=revocation_receipt_digest(substituted.revocation_receipt),
        )
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, substituted)

    def test_matching_object_from_other_source_cannot_bind_crl(self):
        receipt = self.C(
            self.p0,
            [self.E("ocsp", status="good"), self.E("crl", status="good")],
        )
        selection = replace(
            receipt.selection_receipt,
            evidence=(
                self.E("ocsp", status="good"),
                Evidence("crl", "good", True, True, "other-crl", "CRL-SELECT"),
            ),
        )
        receipt = replace(
            receipt,
            selection_receipt=selection,
            selection_digest=selection_receipt_digest(selection),
            revocation_receipt=replace(receipt.revocation_receipt, object_digest="ocsp-object"),
        )
        receipt = replace(receipt, revocation_digest=revocation_receipt_digest(receipt.revocation_receipt))
        with self.assertRaises(Hold): self.A(self.p0, self.rp0, receipt)

    def test_historical_consensus_receipt_rejects_under_successor(self):
        old = self.C(self.p0, [self.E("ocsp"), self.E("crl")])
        self.assertEqual(self.A(self.p0, self.rp0, old), "good")
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, old)

    def test_source_and_crl_policy_generation_mix_rejects(self):
        current = self.C(self.p1, [self.E("crl")])
        with self.assertRaises(Hold): self.A(self.p1, self.rp0, current)

    def test_old_crl_receipt_cannot_be_spliced_into_current_selection(self):
        current = self.C(self.p1, [self.E("crl")])
        old = self.C(self.p0, [self.E("ocsp"), self.E("crl")])
        splice = replace(current, revocation_receipt=old.revocation_receipt,
                         revocation_digest=revocation_receipt_digest(old.revocation_receipt))
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, splice)

    def test_selection_digest_substitution_rejects(self):
        current = self.C(self.p1, [self.E("crl")])
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, replace(current, selection_digest="other"))

    def test_revocation_digest_substitution_rejects(self):
        current = self.C(self.p1, [self.E("crl")])
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, replace(current, revocation_digest="other"))

    def test_status_conflict_rejects(self):
        current = self.C(self.p1, [self.E("crl")])
        bad_revocation = replace(current.revocation_receipt, status="revoked")
        bad = replace(current, revocation_receipt=bad_revocation,
                      revocation_digest=revocation_receipt_digest(bad_revocation))
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, bad)

    def test_missing_composition_execution_rejects(self):
        current = self.C(self.p1, [self.E("crl")])
        with self.assertRaises(Hold): self.A(self.p1, self.rp1, replace(current, composition_execution_id=""))


if __name__ == "__main__":
    unittest.main()

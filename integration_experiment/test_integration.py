import base64
import json
import os
import pathlib
import socket
import sys
import threading
import unittest
import ssl

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import stateful_subject as st
from atomic_join import BoundRegistryStore
from execution_identity_reference import ExecutionEnvelope, IssuerAuthorization, sign
from lifecycle_registry import RegistrySnapshot, digest_registry
from etcd_lifecycle_adapter import (EtcdLifecycleAdapter, Gateway, TestProviderBinding,
                                    EXCHANGE_LOG, fixture_authority_state)
from secure_fixture import tls_context


ENDPOINT = os.environ["BRAINS10_ETCD_ENDPOINT"]
CLUSTER_ID = os.environ["BRAINS10_ETCD_CLUSTER_ID"]
RUN_SCOPE = os.environ.get("BRAINS10_TEST_SCOPE", "local")
TLS_CONTEXT = tls_context(pathlib.Path(os.environ["BRAINS10_ETCD_CA_FILE"]))
AUTH_TOKEN = os.environ["BRAINS10_ETCD_AUTH_TOKEN"]
ROOT_TOKEN = os.environ["BRAINS10_ETCD_ROOT_TOKEN"]
WRONG_CA_FILE = pathlib.Path(os.environ["BRAINS10_ETCD_WRONG_CA_FILE"])


def b64(x): return base64.b64encode(x).decode("ascii")
def canon(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class Integration(unittest.TestCase):
    def setUp(self):
        self.name = self.id().rsplit(".", 1)[-1]
        self.ns = f"/brains10/pass219-etcd/{RUN_SCOPE}/{self.name}"
        self.key = Ed25519PrivateKey.generate()
        self.issuer = IssuerAuthorization("prod", "issuer-1", "key-1", "C1",
            self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
        self.snapshot = RegistrySnapshot("C1", (self.issuer,), digest_registry("C1", (self.issuer,)))
        self.store = BoundRegistryStore((self.snapshot,))
        self.binding = TestProviderBinding(ENDPOINT, "ephemeral-test-etcd", CLUSTER_ID,
                                           self.ns, "C1", True, "rbac-password")
        self.gateway = Gateway(ENDPOINT, ssl_context=TLS_CONTEXT, auth_token=AUTH_TOKEN)
        self.root_gateway = Gateway(ENDPOINT, ssl_context=TLS_CONTEXT, auth_token=ROOT_TOKEN)
        self.adapter = EtcdLifecycleAdapter(self.gateway, self.binding, self.store)
        state = fixture_authority_state(self.binding, generation=0, head_digest="HEAD-A",
            authority_config="C1", lifecycle_generation=7, registry_digest=self.snapshot.digest)
        init = self.gateway.txn([
            {"key": b64(self.adapter.current_key), "target": "VERSION", "result": "EQUAL", "version": "0"}
        ], [(self.adapter.current_key, state)])
        self.assertIs(init.get("succeeded"), True)

    def signed(self, eid, result_digest="result-1"):
        env = ExecutionEnvelope(eid, "prod", "issuer-1", "key-1", "C1",
            "subject-1", "config-1", "input-1", result_digest, "runtime-1")
        return sign(self.key, env)

    def activate(self, tid="tx-1", eid="exec-1", succ="HEAD-B", effects=(('publish','target-1','payload-1'),), challenge=b"read-challenge-1"):
        return self.adapter.activate(challenge=challenge, expected_generation=0,
            expected_head_digest="HEAD-A", successor_head_digest=succ,
            transition_id=tid, signed=self.signed(eid), effects=effects)

    def record(self, key):
        row, _ = self.adapter._read_raw(key)
        self.assertIsNotNone(row)
        return row[0], row[1]

    def test_linearizable_challenge_and_exact_authority_fields(self):
        status, obs = self.adapter.read_current(b"fresh-challenge", "C1")
        self.assertEqual(status, "CURRENT")
        self.assertEqual(obs.challenge, b"fresh-challenge")
        self.assertEqual(obs.authority_config, "C1")
        self.assertEqual(obs.state["lifecycle_generation"], 7)
        self.assertEqual(obs.state["registry_digest"], self.snapshot.digest)
        ranges = [json.loads(body) for path, body in self.gateway.requests if path == "/v3/kv/range"]
        self.assertTrue(ranges)
        self.assertTrue(all(r.get("serializable") is False for r in ranges))

    def test_empty_or_aliased_challenge_fails(self):
        self.assertEqual(self.adapter.read_current(b"", "C1")[0], "REJECT")
        self.assertEqual(self.activate(tid="read-challenge-1", challenge=b"read-challenge-1")[0], "REJECT")

    def test_atomic_successor_receipt_execution_and_outbox_same_revision(self):
        outcome, result = self.activate()
        self.assertEqual(outcome, "OK")
        self.assertEqual(result, {"generation": 1, "head_digest": "HEAD-B", "authority_config": "C1"})
        keys = [self.adapter.current_key, self.adapter.receipt_key("tx-1"),
                self.adapter.execution_key("exec-1"), self.adapter.effect_key(st.EID("tx-1", "publish", "target-1"))]
        rows = [self.record(k)[0] for k in keys]
        self.assertEqual({int(kv["mod_revision"]) for kv in rows}, {int(rows[0]["mod_revision"])})
        state = json.loads(self.record(self.adapter.current_key)[1])
        self.assertEqual((state["generation"], state["head_digest"], state["lifecycle_generation"]), (1, "HEAD-B", 7))

    def test_exact_retry_and_transition_id_mismatch(self):
        first = self.activate()
        self.assertEqual(first[0], "OK")
        self.assertEqual(self.activate(), first)
        self.assertEqual(self.activate(succ="HEAD-X")[0], "ID_REUSE_MISMATCH")

    def test_stale_parent_has_no_receipt_or_effect(self):
        self.assertEqual(self.activate()[0], "OK")
        out = self.adapter.activate(challenge=b"fresh-after", expected_generation=0,
            expected_head_digest="HEAD-A", successor_head_digest="HEAD-C",
            transition_id="tx-stale", signed=self.signed("exec-stale"), effects=())
        self.assertEqual(out[0], "STALE")
        self.assertIsNone(self.adapter._read_record(self.adapter.receipt_key("tx-stale")))

    def test_same_global_execution_id_with_different_envelope_rejects(self):
        self.assertEqual(self.activate()[0], "OK")
        conflict = self.adapter.activate(challenge=b"second-challenge", expected_generation=1,
            expected_head_digest="HEAD-B", successor_head_digest="HEAD-C",
            transition_id="tx-second", signed=self.signed("exec-1", "different-result"), effects=())
        self.assertEqual(conflict[0], "EXECUTION_OR_TRANSITION_REUSE_MISMATCH")

    def test_sibling_transactions_consume_one_parent(self):
        barrier = threading.Barrier(2)
        self.gateway.before_txn = lambda _: barrier.wait(timeout=5)
        result = []
        def run(tid, eid, successor, challenge):
            result.append(self.adapter.activate(challenge=challenge, expected_generation=0,
                expected_head_digest="HEAD-A", successor_head_digest=successor,
                transition_id=tid, signed=self.signed(eid), effects=())[0])
        a = threading.Thread(target=run, args=("tx-left", "exec-left", "HEAD-L", b"challenge-left"))
        b = threading.Thread(target=run, args=("tx-right", "exec-right", "HEAD-R", b"challenge-right"))
        a.start(); b.start(); a.join(10); b.join(10)
        self.gateway.before_txn = None
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(sorted(result), ["OK", "STALE"])
        state = json.loads(self.record(self.adapter.current_key)[1])
        self.assertEqual(state["generation"], 1)

    def test_lifecycle_change_between_read_and_txn_is_stale(self):
        mutate = Gateway(ENDPOINT)
        fired = {"once": False}
        def rotate_fixture(_):
            if fired["once"]: return
            fired["once"] = True
            row, _ = self.adapter._read_raw(self.adapter.current_key)
            kv, raw = row
            old = json.loads(raw); new = dict(old); new["lifecycle_generation"] += 1
            txn = mutate.txn([
                {"key": b64(self.adapter.current_key), "target": "MOD", "result": "EQUAL", "modRevision": kv["mod_revision"]},
                {"key": b64(self.adapter.current_key), "target": "VALUE", "result": "EQUAL", "value": b64(raw)}
            ], [(self.adapter.current_key, canon(new))])
            self.assertIs(txn.get("succeeded"), True)
        self.gateway.before_txn = rotate_fixture
        out = self.activate()
        self.gateway.before_txn = None
        self.assertTrue(fired["once"])
        self.assertEqual(out[0], "STALE")
        self.assertIsNone(self.adapter._read_record(self.adapter.receipt_key("tx-1")))

    def test_lost_txn_response_reconciles_same_receipt(self):
        self.gateway.after_txn = lambda _: (_ for _ in ()).throw(TimeoutError("drop response after server returned"))
        out = self.activate()
        self.assertEqual(out[0], "UNKNOWN_COMMIT")
        self.gateway.after_txn = None
        ident = out[1]
        self.assertEqual(self.adapter.reconcile(ident["transition_id"], ident["fingerprint"])[0], "OK")
        self.assertEqual(self.activate()[0], "OK")
        self.assertEqual(json.loads(self.record(self.adapter.current_key)[1])["generation"], 1)

    def test_pre_submit_loss_stays_unknown_until_exact_retry(self):
        self.gateway.before_txn = lambda _: (_ for _ in ()).throw(ConnectionError("not submitted"))
        out = self.activate(tid="tx-not-submitted", eid="exec-not-submitted")
        self.assertEqual(out[0], "UNKNOWN_COMMIT")
        self.gateway.before_txn = None
        ident = out[1]
        self.assertEqual(self.adapter.reconcile(ident["transition_id"], ident["fingerprint"])[0], "UNKNOWN_COMMIT")
        retry = self.activate(tid="tx-not-submitted", eid="exec-not-submitted")
        self.assertEqual(retry[0], "OK")

    def test_wrong_cluster_and_malformed_value_fail_closed(self):
        wrong = TestProviderBinding(ENDPOINT, "ephemeral-test-etcd", "1", self.ns, "C1")
        self.assertNotEqual(EtcdLifecycleAdapter(self.gateway, wrong, self.store).read_current(b"c", "C1")[0], "CURRENT")
        bad = Gateway(ENDPOINT)
        self.assertIs(bad.txn([
            {"key": b64(self.adapter.current_key), "target": "MOD", "result": "EQUAL",
             "modRevision": self.record(self.adapter.current_key)[0]["mod_revision"]}
        ], [(self.adapter.current_key, b"{")]).get("succeeded"), True)
        self.assertNotEqual(self.adapter.read_current(b"new-c", "C1")[0], "CURRENT")

    def test_unbounded_effect_list_is_outside_test_scope(self):
        out = self.adapter.activate(challenge=b"scope-challenge", expected_generation=0,
            expected_head_digest="HEAD-A", successor_head_digest="HEAD-B", transition_id="scope-tx",
            signed=self.signed("scope-exec"), effects=(('k','t','p'),('k2','t2','p2')))
        self.assertEqual(out[0], "OUTSIDE_TEST_SCOPE")
        self.assertEqual(json.loads(self.record(self.adapter.current_key)[1])["generation"], 0)

    def test_preexisting_outbox_key_is_never_overwritten(self):
        effect_id = st.EID("tx-1", "publish", "target-1")
        key = self.adapter.effect_key(effect_id)
        old_value = canon({"attacker": "preexisting"})
        inserted = self.gateway.txn([
            {"key": b64(key), "target": "VERSION", "result": "EQUAL", "version": "0"}
        ], [(key, old_value)])
        self.assertIs(inserted.get("succeeded"), True)
        out = self.activate()
        self.assertEqual(out[0], "EFFECT_ID_REUSE_MISMATCH")
        self.assertEqual(self.record(key)[1], old_value)
        self.assertEqual(json.loads(self.record(self.adapter.current_key)[1])["generation"], 0)

    def test_tls_wrong_ca_is_rejected_before_gateway_use(self):
        wrong = Gateway(ENDPOINT, ssl_context=tls_context(WRONG_CA_FILE), auth_token=AUTH_TOKEN)
        with self.assertRaises(ConnectionError):
            wrong.range(self.adapter.current_key)

    def test_tls_wrong_hostname_and_plaintext_downgrade_are_rejected(self):
        from urllib.parse import urlsplit
        parts = urlsplit(ENDPOINT)
        raw = socket.create_connection((parts.hostname, parts.port), timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):
                TLS_CONTEXT.wrap_socket(raw, server_hostname="wrong.invalid")
        finally:
            try: raw.close()
            except OSError: pass
        insecure_endpoint = ENDPOINT.replace("https://", "http://", 1)
        downgrade = Gateway(insecure_endpoint, ssl_context=TLS_CONTEXT, auth_token=AUTH_TOKEN)
        with self.assertRaises(ConnectionError):
            downgrade.range(self.adapter.current_key)

    def test_missing_and_invalid_bearer_tokens_fail_closed(self):
        for token in (None, "invalid-test-token"):
            gateway = Gateway(ENDPOINT, ssl_context=TLS_CONTEXT, auth_token=token)
            with self.assertRaises(ConnectionError):
                gateway.range(self.adapter.current_key)

    def test_password_authentication_is_required_for_gateway_user(self):
        import secure_fixture
        status, _ = secure_fixture._post(ENDPOINT, "/v3/auth/authenticate",
            {"name": os.environ["BRAINS10_ETCD_TEST_USER"], "password": "wrong-password"}, TLS_CONTEXT)
        self.assertNotEqual(status, 200)

    def test_rbac_allows_only_the_exact_namespace_prefix(self):
        outside = (f"/brains10/pass219-etcd/{RUN_SCOPE}0escaped").encode()
        with self.assertRaises(ConnectionError):
            self.gateway.range(outside)
        with self.assertRaises(ConnectionError):
            self.gateway.post("/v3/kv/put", {"key": b64(outside), "value": b64(b"must-not-write")})
        row, _ = self.adapter._read_raw(outside)
        self.assertIsNone(row)
        self.assertTrue(self.binding.tls)
        self.assertEqual(self.binding.auth_mode, "rbac-password")

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Integration)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    out = pathlib.Path(os.environ.get("BRAINS10_EVIDENCE_DIR", "."))
    out.mkdir(parents=True, exist_ok=True)
    (out / "HTTP_EXCHANGES.json").write_text(json.dumps(EXCHANGE_LOG, indent=2, sort_keys=True) + "\n")
    print(f"PASS219_ETCD_INTEGRATION_TESTS {'PASS' if result.wasSuccessful() else 'FAIL'} {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    sys.exit(0 if result.wasSuccessful() else 1)

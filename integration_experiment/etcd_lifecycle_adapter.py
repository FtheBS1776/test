"""Bounded NONCLAIM Pass-219-to-etcd composition experiment.

This is a test adapter for a provisioned fixture, not production authority code.
It intentionally accepts at most one small effect to stay within the tested scope.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

import stateful_subject as st
from execution_identity_reference import SignedEnvelope


MAX_TEST_EFFECTS = 1
MAX_TEST_REQUEST_BYTES = 64 * 1024
ADAPTER_VERSION = "pass219-etcd-nonclaim-v1"
EXCHANGE_LOG = []


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.b64decode(data, validate=True)


def _canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _text(x) -> bool:
    return type(x) is str and bool(x.strip())


@dataclass(frozen=True)
class TestProviderBinding:
    """Fixture binding only; the caller/test setup is not an authority source."""
    endpoint: str
    provider_id: str
    cluster_id: str
    namespace: str
    authority_config: str
    tls: bool = False
    auth_mode: str = "none"
    adapter_version: str = ADAPTER_VERSION

    def digest(self) -> str:
        if not all(_text(x) for x in (self.endpoint, self.provider_id, self.cluster_id,
                                      self.namespace, self.authority_config, self.auth_mode,
                                      self.adapter_version)):
            raise ValueError("BAD_PROVIDER_BINDING")
        return hashlib.sha256(_canonical({
            "endpoint": self.endpoint,
            "provider_id": self.provider_id,
            "cluster_id": self.cluster_id,
            "namespace": self.namespace,
            "authority_config": self.authority_config,
            "tls": self.tls,
            "auth_mode": self.auth_mode,
            "adapter_version": self.adapter_version,
        })).hexdigest()


@dataclass(frozen=True)
class CurrentObservation:
    challenge: bytes
    authority_config: str
    provider_id: str
    cluster_id: str
    raw_value: bytes
    mod_revision: int
    state: dict


class Gateway:
    """Small JSON HTTP-gateway client; every Range explicitly says serializable=false."""
    def __init__(self, endpoint: str, timeout: float = 3.0, after_txn=None):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.after_txn = after_txn
        self.before_txn = None
        self.requests = []

    def post(self, path: str, value: dict) -> dict:
        body = _canonical(value)
        self.requests.append((path, body))
        exchange = {"path": path, "request_b64": _b64(body), "response_b64": None,
                    "transport_error": None}
        EXCHANGE_LOG.append(exchange)
        req = urllib.request.Request(self.endpoint + path, data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            if path == "/v3/kv/txn" and self.before_txn:
                self.before_txn(body)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            exchange["transport_error"] = type(e).__name__ + ": " + str(e)
            raise ConnectionError(str(e)) from e
        result = json.loads(raw)
        if path == "/v3/kv/txn" and self.after_txn:
            try:
                self.after_txn(raw)
            except Exception as e:
                exchange["transport_error"] = "RESPONSE_LOST_AFTER_SERVER_REPLY: " + str(e)
                raise
        exchange["response_b64"] = _b64(raw)
        return result

    def range(self, key: bytes) -> dict:
        return self.post("/v3/kv/range", {"key": _b64(key), "serializable": False})

    def txn(self, compares: list[dict], puts: list[tuple[bytes, bytes]]) -> dict:
        if len({k for k, _ in puts}) != len(puts):
            raise ValueError("DUPLICATE_TXN_WRITE_KEY")
        request = {
            "compare": compares,
            "success": [{"requestPut": {"key": _b64(k), "value": _b64(v)}} for k, v in puts],
            "failure": [],
        }
        if len(_canonical(request)) > MAX_TEST_REQUEST_BYTES:
            raise ValueError("TEST_SCOPE_REQUEST_TOO_LARGE")
        return self.post("/v3/kv/txn", request)


class EtcdLifecycleAdapter:
    def __init__(self, gateway: Gateway, binding: TestProviderBinding, registry_store):
        if type(gateway) is not Gateway or type(binding) is not TestProviderBinding:
            raise ValueError("EXACT_TEST_TYPES_REQUIRED")
        if not _text(binding.cluster_id):
            raise ValueError("BAD_CLUSTER_ID")
        self.gateway = gateway
        self.binding = binding
        self.registry_store = registry_store
        prefix = binding.namespace.rstrip("/").encode("utf-8")
        if not prefix or not binding.namespace.startswith("/"):
            raise ValueError("BAD_NAMESPACE")
        self.prefix = prefix

    def _key(self, group: str, identity: str = "") -> bytes:
        if not _text(group) or (identity and not _text(identity)):
            raise ValueError("BAD_KEY_ID")
        # Type-specific prefixes make raw UTF-8 IDs injective within their key domain.
        return self.prefix + b"/" + group.encode("ascii") + (b"/" + identity.encode("utf-8") if identity else b"")

    @property
    def current_key(self): return self._key("authority-current")

    def receipt_key(self, tid): return self._key("transition", tid)
    def execution_key(self, eid): return self._key("execution", eid)
    def effect_key(self, effect_id): return self._key("outbox", effect_id)

    def _check_header(self, response):
        header = response.get("header")
        if type(header) is not dict or header.get("cluster_id") != self.binding.cluster_id:
            raise ValueError("PROVIDER_CLUSTER_MISMATCH")
        return header

    def _read_raw(self, key: bytes):
        response = self.gateway.range(key)
        header = self._check_header(response)
        try:
            count_raw = response.get("count")
            kvs = response.get("kvs")
            # The etcd JSON gateway omits protobuf default-valued response fields.
            if count_raw is None and kvs is None:
                count, kvs = 0, []
            elif count_raw is None or kvs is None:
                raise ValueError("INCOMPLETE_RANGE_DEFAULTS")
            else:
                count = int(count_raw)
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError("MALFORMED_RANGE") from e
        if count == 0:
            return None, header
        if count != 1 or type(kvs) is not list or len(kvs) != 1:
            raise ValueError("NONEXACT_RANGE")
        kv = kvs[0]
        if type(kv) is not dict or _unb64(kv.get("key", "")) != key:
            raise ValueError("MALFORMED_RANGE_KEY")
        return (kv, _unb64(kv["value"])), header

    def read_current(self, challenge: bytes, expected_authority_config: str):
        if type(challenge) is not bytes or not challenge:
            return "REJECT", None
        if not _text(expected_authority_config) or expected_authority_config != self.binding.authority_config:
            return "PROVIDER_CONFIG_MISMATCH", None
        try:
            row, header = self._read_raw(self.current_key)
            if row is None:
                return "AUTHORITY_UNAVAILABLE", None
            kv, raw = row
            state = json.loads(raw)
            required = {"generation", "head_digest", "authority_config", "lifecycle_generation",
                        "registry_digest", "provider_binding_digest"}
            if type(state) is not dict or set(state) != required:
                return "MALFORMED_AUTHORITY", None
            if type(state["generation"]) is not int or state["generation"] < 0:
                return "MALFORMED_AUTHORITY", None
            if type(state["lifecycle_generation"]) is not int or state["lifecycle_generation"] < 0:
                return "MALFORMED_AUTHORITY", None
            if not all(_text(state[x]) for x in ("head_digest", "authority_config", "registry_digest",
                                                 "provider_binding_digest")):
                return "MALFORMED_AUTHORITY", None
            if state["authority_config"] != expected_authority_config:
                return "PROVIDER_CONFIG_MISMATCH", None
            if state["provider_binding_digest"] != self.binding.digest():
                return "PROVIDER_CONFIG_MISMATCH", None
            rev = int(kv["mod_revision"])
            return "CURRENT", CurrentObservation(challenge, expected_authority_config,
                self.binding.provider_id, header["cluster_id"], raw, rev, state)
        except (ConnectionError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return "UNAVAILABLE", None

    def _read_record(self, key: bytes):
        row, _ = self._read_raw(key)
        if row is None:
            return None
        _, raw = row
        return json.loads(raw)

    def reconcile(self, tid: str, fingerprint: str, execution_id: str | None = None,
                  envelope_fingerprint: str | None = None):
        if not _text(tid) or not _text(fingerprint):
            return "REJECT", None
        try:
            record = self._read_record(self.receipt_key(tid))
        except (ConnectionError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return "UNKNOWN_COMMIT", None
        if record is None:
            return "UNKNOWN_COMMIT", None
        if type(record) is not dict:
            return "UNKNOWN_COMMIT", None
        if record.get("fingerprint") != fingerprint:
            return "ID_REUSE_MISMATCH", None
        if execution_id is not None and record.get("execution_id") != execution_id:
            return "EXECUTION_OR_TRANSITION_REUSE_MISMATCH", None
        if envelope_fingerprint is not None and record.get("envelope_fingerprint") != envelope_fingerprint:
            return "EXECUTION_OR_TRANSITION_REUSE_MISMATCH", None
        return "OK", record["result"]

    def activate(self, *, challenge: bytes, expected_generation: int, expected_head_digest: str,
                 successor_head_digest: str, transition_id: str, signed: SignedEnvelope, effects=()):
        if type(expected_generation) is not int or expected_generation < 0:
            return "REJECT", None
        if not all(_text(x) for x in (expected_head_digest, successor_head_digest, transition_id)):
            return "REJECT", None
        if type(challenge) is not bytes or not challenge or challenge == transition_id.encode("utf-8"):
            return "REJECT", None
        if type(signed) is not SignedEnvelope or type(effects) not in (tuple, list):
            return "REJECT", None
        if len(effects) > MAX_TEST_EFFECTS:
            return "OUTSIDE_TEST_SCOPE", None
        effect_ids = set()
        for effect in effects:
            if type(effect) is not tuple or len(effect) != 3 or not all(st.S(v) for v in effect):
                return "REJECT", None
            effect_id = st.EID(transition_id, effect[0], effect[1])
            if effect_id in effect_ids:
                return "REJECT", None
            effect_ids.add(effect_id)
        status, observation = self.read_current(challenge, self.binding.authority_config)
        if status != "CURRENT":
            return status, None
        state = observation.state
        snapshot = self.registry_store.exact(state["registry_digest"], state["authority_config"])
        if snapshot is None:
            return "REGISTRY_BINDING_UNAVAILABLE", None
        try:
            envelope = snapshot.verifier().verify(signed)
        except Exception:
            return "REJECT", None
        if envelope.authority_config != state["authority_config"]:
            return "AUTHORITY_CONFIG_MISMATCH", None

        envelope_fp = hashlib.sha256(envelope.canonical()).hexdigest()
        fingerprint = st.FP(expected_generation, expected_head_digest, successor_head_digest,
                            transition_id, state["authority_config"], effects)
        prior = self.reconcile(transition_id, fingerprint, envelope.execution_id, envelope_fp)
        if prior[0] == "OK":
            return prior
        if prior[0] == "ID_REUSE_MISMATCH":
            return prior
        if prior[0] == "EXECUTION_OR_TRANSITION_REUSE_MISMATCH":
            return prior
        # ABSENT is not asserted from a linearizable receipt read; it remains UNKNOWN until this
        # exact stable-ID conditional transaction resolves it.
        if (state["generation"], state["head_digest"]) != (expected_generation, expected_head_digest):
            return "STALE", None

        next_state = dict(state)
        next_state["generation"] = expected_generation + 1
        next_state["head_digest"] = successor_head_digest
        result = {"generation": next_state["generation"],
                  "head_digest": successor_head_digest,
                  "authority_config": state["authority_config"]}
        receipt = {"transition_id": transition_id, "fingerprint": fingerprint,
                   "execution_id": envelope.execution_id,
                   "envelope_fingerprint": envelope_fp, "result": result}
        outbox = []
        effect_compares = []
        for kind, target, payload in effects:
            effect_id = st.EID(transition_id, kind, target)
            effect_key = self.effect_key(effect_id)
            effect_compares.append({"key": _b64(effect_key), "target": "VERSION",
                                    "result": "EQUAL", "version": "0"})
            outbox.append((effect_key, _canonical({
                "effect_id": effect_id, "transition_id": transition_id,
                "kind": kind, "target": target, "payload": payload,
                "generation": result["generation"], "authority_config": state["authority_config"]})))
        receipt_key = self.receipt_key(transition_id)
        execution_key = self.execution_key(envelope.execution_id)
        puts = [(self.current_key, _canonical(next_state)),
                (receipt_key, _canonical(receipt)),
                (execution_key, _canonical({"execution_id": envelope.execution_id,
                                            "envelope_fingerprint": envelope_fp,
                                            "transition_id": transition_id}))] + outbox
        try:
            txn = self.gateway.txn([
                {"key": _b64(self.current_key), "target": "MOD", "result": "EQUAL",
                 "modRevision": str(observation.mod_revision)},
                {"key": _b64(self.current_key), "target": "VALUE", "result": "EQUAL",
                 "value": _b64(observation.raw_value)},
                {"key": _b64(receipt_key), "target": "VERSION", "result": "EQUAL", "version": "0"},
                {"key": _b64(execution_key), "target": "VERSION", "result": "EQUAL", "version": "0"},
            ] + effect_compares, puts)
        except (ConnectionError, TimeoutError, OSError, ValueError):
            return "UNKNOWN_COMMIT", {"transition_id": transition_id, "fingerprint": fingerprint}
        try:
            header = self._check_header(txn)
        except ValueError:
            return "UNKNOWN_COMMIT", {"transition_id": transition_id, "fingerprint": fingerprint}
        if type(txn.get("succeeded")) is not bool:
            return "UNKNOWN_COMMIT", {"transition_id": transition_id, "fingerprint": fingerprint}
        if txn.get("succeeded") is True:
            return "OK", result
        # Compare failed. A same-ID concurrent identical winner is resolved by its receipt;
        # otherwise the exact parent was consumed or an ID was already used.
        prior = self.reconcile(transition_id, fingerprint, envelope.execution_id, envelope_fp)
        if prior[0] in ("OK", "ID_REUSE_MISMATCH", "EXECUTION_OR_TRANSITION_REUSE_MISMATCH"):
            return prior
        try:
            used = self._read_record(execution_key)
        except (ConnectionError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return "UNKNOWN_COMMIT", None
        if used is not None:
            return "EXECUTION_OR_TRANSITION_REUSE_MISMATCH", None
        try:
            for kind, target, _payload in effects:
                effect_id = st.EID(transition_id, kind, target)
                if self._read_record(self.effect_key(effect_id)) is not None:
                    return "EFFECT_ID_REUSE_MISMATCH", None
        except (ConnectionError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return "UNKNOWN_COMMIT", None
        return "STALE", None


def fixture_authority_state(binding: TestProviderBinding, *, generation: int, head_digest: str,
                            authority_config: str, lifecycle_generation: int,
                            registry_digest: str) -> bytes:
    """Create fixture bytes only; this does not authorize/bootstrap production state."""
    if type(generation) is not int or generation < 0 or type(lifecycle_generation) is not int or lifecycle_generation < 0:
        raise ValueError("BAD_GENERATION")
    if authority_config != binding.authority_config or not all(_text(x) for x in
       (head_digest, authority_config, registry_digest)):
        raise ValueError("BAD_FIXTURE_STATE")
    return _canonical({"generation": generation, "head_digest": head_digest,
        "authority_config": authority_config, "lifecycle_generation": lifecycle_generation,
        "registry_digest": registry_digest, "provider_binding_digest": binding.digest()})

# Conformance scope — HTTPS/RBAC extension

This is a new subject, distinct from the earlier plaintext HTTP/no-auth capture. The test fixture uses one pinned etcd 3.6.5 member on loopback with a per-run generated CA/server certificate, strict client chain and hostname validation, password-authenticated V3 auth, and a least-privilege fixture role for a random run-scoped key prefix. No client certificate is used. Secrets and private keys are ephemeral and are not included in evidence.

## What the experiment can observe

- A real etcd v3.6.5 single-member process accepts a JSON-gateway Range explicitly marked non-serializable and a Compare/Txn request.
- The client validates the exact loopback server certificate against the generated CA; a different CA and plaintext mismatch are rejected.
- The etcd gateway accepts the test user only with the bearer token obtained through `/v3/auth/authenticate`; absent and invalid tokens fail closed.
- The V3 RBAC role permits reads/writes under its granted test prefix and denies a lexical-neighbor prefix; a root fixture read confirms the denied write did not land.
- Under the fixture, current authority fields are read through the exact configured namespace; the adapter observation carries the caller's nonempty challenge and checks the fixture provider-config binding. The challenge is not sent to etcd and is not provider-certified.
- A small test activation compares the exact current value and observed modification revision and compares the receipt, global execution, and outbox keys as absent, then atomically writes successor, stable receipt, global execution-ID consumption, and one outbox intent.
- Sibling races, lifecycle-data change between Range and Txn, same-ID replay/mismatch, missing/changed receipt resolution, and response-loss handling behave as tested.

## What the experiment cannot establish

- lifecycle authority for the test provider binding, trusted genesis, typed Pass 220–222 root-transition verifier integration, production endpoint/TLS/auth provisioning, or operator independence;
- production PKI or credential custody, mTLS/client-certificate identity, production token mode, or protection of `/health` and `/metrics` through V3 RBAC. The fixture uses etcd's development-only simple token mode and treats it only as an implementation test;
- general Pass 219 semantics for arbitrary numbers/sizes of effects, keys, IDs, or payloads;
- multi-node failover, stale follower behavior, distributed partitions, or production deployment semantics;
- sink delivery, cross-target projection coherence beyond the existing reference semantics, physical power-loss durability, rollback resistance, root compromise recovery, or whole-world rollback protection;
- proof that arbitrary user computation actually ran, a result-digest-to-successor warrant, generalized execution-ID allocation, or remote attestation.

Pass 186 remains controlling; this branch is NONCLAIM. A green workflow, local response revision, provider ID, artifact hash, or matching state digest cannot promote authority.

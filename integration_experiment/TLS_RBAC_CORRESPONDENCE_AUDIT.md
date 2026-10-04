# Pass 219 etcd HTTPS + RBAC pre-design audit — NONCLAIM

Date: 2026-10-04 UTC. Scope: an isolated one-member etcd 3.6.5 fixture using its HTTP gateway. This audit and attacks precede implementation. Pass 186 remains controlling; no promotion or freeze.

## Correspondence audit

| Lineage | Reuse / adapt | Exact consequence for this branch |
|---|---|---|
| L7 | Reuse the separation of integrity, identity, authorization, and currentness. Provider-returned cluster IDs, TLS success, auth tokens, endpoint text, revisions, and GitHub evidence are observations, not authority. | The per-run test CA and fixture credentials can demonstrate client/server protocol behavior only. They do not establish a production provider trust root, lifecycle-bound endpoint, or authorized genesis. |
| L2 | Reuse separate authority, execution, observation, and verification; fail closed on provider/config mismatch and unknown outcomes. | Do not make security failures fall back to plaintext, anonymous requests, local state, or cached authority. Do not let TLS or RBAC alter the atomic Range/Txn semantics. A transport/auth failure remains an unavailable/UNKNOWN observation. |
| Genie | Reuse strict scope: conformance is only to the exact observed subject, runtime, server version, and fixture configuration. | Claim only etcd 3.6.5 one-member gateway behavior with the recorded generated CA/server cert, fixture user, and namespace. No inference to production PKI, operations, cluster topology, or security posture. |
| EXP-010 | Adapt evidence binding: exact source commit, workflow, run/attempt, raw evidence, failure chronology, and independent adjudication. GitHub is executor/transport. | Preserve the distinct workflow subject and all failed/incomplete artifacts; avoid credential leakage. EXP-010 beacon, seed, freshness, and statistical criteria do not transfer. |
| Pass 191 / 225 | Reuse fresh linearizable Range, exact current-state compare, single atomic Txn, lifecycle-bound provider/config, fail-closed provider/auth mismatch. | TLS and successful bearer auth are prerequisites for the fixture request, not proof the endpoint/provider/config is lifecycle-authorized. |
| Pass 219 integration evidence | Reuse the exact already-tested transaction subject and use this as a separate transport/auth extension. | Do not rewrite/rename the previous cleartext run as TLS/RBAC evidence. Exact new source/workflow/run/attempt has a new identity. |

## Internal attack before research

1. Substitute an untrusted CA, wrong hostname, expired/not-yet-valid cert, or plaintext listener. Client must reject; no downgrade/fallback.
2. Serve a valid certificate for the wrong endpoint/identity. Hostname verification must reject; CA trust alone is insufficient.
3. Omit or corrupt auth token, use wrong password/token, or expire/revoke the user. Protected KV/gateway calls must reject, and adapter must not treat a gateway HTTP 200 as committed state.
4. Give fixture user only an exact namespace/prefix role, then read/write outside it. Out-of-prefix access must fail and a follow-up root fixture read must show denied writes made no change.
5. Confuse TLS client certificate Common Name with RBAC principal through the gateway. This is prohibited as an assumption; use username/password auth for API authorization.
6. Leak generated password, bearer token, private key, auth request body, or token response through command argv, environment dumps, workflow logs, crash text, test errors, exchange capture, or uploaded artifacts. Secrets must be ephemeral, not placed in argv, and redacted before durable capture. Record redaction metadata and integrity hashes without making the secret recoverable.
7. Use broad prefix encoding or malformed base64 to escape the test namespace. Test keys and role range must use exact byte prefixes; attempted sibling/out-of-prefix keys must be denied.
8. Treat `/health` or `/metrics` as RBAC-protected or as proof of KV identity. These endpoints have separate handling; do not use them as authority observations.
9. Turn auth/TLS failures or timeouts into ACCEPT, stale cached CURRENT, a second transition ID, or green test status. Keep fail-closed/UNKNOWN accounting and upload incomplete evidence.
10. Overclaim a single generated CA/one-member local fixture as independently administered PKI, provider identity, production least privilege, multi-node reliability, or rollback resistance. Explicitly exclude those conclusions.

## Pre-design disposition

The proposed adequate exact fixture is server-authenticated HTTPS (generated run-scoped CA; SAN-bound loopback hostname/IP) plus etcd V3 password authentication and a narrow test role. The gateway uses the returned bearer token. No TLS CN principal, production credential, client-side provider identity, or production trust claim is in scope. Keep secrets out of raw durable evidence and test both transport rejection and access-boundary denial. If the client implementation cannot safely redact auth exchanges while preserving sufficient evidence, stop before execution and revise the evidence plan. Required next gate: current official source verification and candidate cross-attack.

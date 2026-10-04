# L7 + L2 + Genie + EXP-010 correspondence audit — TLS/RBAC branch

Date: 2026-10-04 UTC. Pass 186 remains controlling. This is a separate NONCLAIM subject from the previous cleartext integration run.

| Prior experience | Correspondence / disposition |
|---|---|
| L7 | Reuse the rule that endpoint identity, etcd cluster IDs, revisions, artifact hashes, auth tokens, and TLS success are observations, not trust roots or authority. The generated CA and user are controlled by this fixture and cannot establish production provider trust, lifecycle authorization, or genesis. |
| L2 | Reuse separation of authority, execution, observation, and verification; fail closed on auth/TLS/configuration mismatch and retain UNKNOWN on uncertain Txn completion. TLS/RBAC failures do not permit cleartext, anonymous, stale-cache, SQLite, or new-ID fallback. |
| Genie | Claim only exact tested behavior for the pinned etcd 3.6.5 one-member process, loopback endpoint, generated server certificate, password-authenticated test user, and namespace. No generalization to production PKI, provider administration, cluster topology, or credential lifecycle. |
| EXP-010 | Bind source bytes/manifest, workflow, commit, run/attempt, logs, and artifact. GitHub is executor/transport. Preserve failures and incomplete artifacts, exclude credentials. EXP-010 seed/beacon/freshness/statistical requirements do not transfer to this deterministic conformance probe. |
| Pass 191/225 | Reuse linearizable Range, exact current-state compare, one atomic Txn, lifecycle-bound provider/config, fail-closed mismatch, and UNKNOWN handling. HTTPS and auth are transport gates and do not change currentness semantics. |
| Pass 219 | Reuse the bounded state/Txn adapter unchanged in semantics, but subject identity changes because transport/auth code and workflow change. Existing cleartext evidence does not cover this branch. |

The missing Pass 220–222 packages continue to hold lifecycle-root transition composition. This transport/auth probe neither needs nor discharges that branch.

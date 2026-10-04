# Cross-attack: proposed etcd HTTPS + RBAC fixture — NONCLAIM

Date: 2026-10-04 UTC. Performed after the correspondence audit, internal attack, and current official-source research, before code changes. No promotion or freeze.

## Exact candidate

Use the already bounded Pass 219 client/transaction subject against a new isolated etcd 3.6.5 one-member loopback fixture. Generate a per-run CA and server certificate with the exact loopback IP/DNS SAN used by the client. Configure server TLS with `--cert-file` and `--key-file`; deliberately do not set `--trusted-ca-file`/`--client-cert-auth`, because that would require client certificates and confuse the intended password-authenticated gateway principal. Configure etcd V3 RBAC with an ephemeral admin user only during fixture setup, then a separately generated least-privilege user whose role grants read/write only under one random test namespace. Enable auth; authenticate through `/v3/auth/authenticate`; send the returned token only in the `Authorization` header for KV gateway operations.

All passwords and tokens are run-scoped random values. Do not put them in process argv or workflow output. Authentication setup request/response bodies are omitted from durable evidence; only operation path and HTTP status are retained. Regular gateway exchanges never record auth headers, only whether authorization was present. Protect private keys as ephemeral files with restrictive permissions and delete the temporary tree after capture packaging. Scan the artifact for exact credential/token/private-key bytes before sealing; if any is found, redact the leaking file and mark the capture incomplete. The previous cleartext run remains a separate subject and is not rewritten.

## Cross-attack results

| Attack | Cross-check / result | Required assertion or limit |
|---|---|---|
| Wrong CA, wrong SAN/hostname, malformed cert, plaintext downgrade | Trust/hostname verification is implemented by the HTTPS client before any KV API call. No retry against `http://` or verification-disabled context. | Each bad server identity fails before an operation; record only sanitized exception class/message. |
| Valid CA but wrong host identity | Chain validity alone does not bind the requested endpoint name. | Hostname/IP SAN verification is enabled and wrong-name test rejects. |
| No token / invalid password / invalid token | TLS success is separate from RBAC identity. | KV Range/Txn calls fail; adapter returns no CURRENT/commit success and makes no fallback. Auth failure isn't an etcd transaction compare failure. |
| Allowed vs denied namespace | RBAC prefix range semantics can be incorrectly encoded or broadened. | Allowed scoped keys work; adjacent namespace and out-of-scope read/write reject; a root-only verifier confirms denied write left no value. |
| Auth setup captures secrets | Raw bodies and responses can expose ephemeral credentials in GitHub logs/artifacts. | No auth setup response/body is durably captured unredacted. Search the final evidence package and workflow log for fixture password/token literals before adjudication. Any leak blocks evidence acceptance and requires cleanup/repair. |
| TLS CN used as RBAC identity | Official gateway docs explicitly disallow that inference. | No client certificate is used; API identity comes only from password-authenticated token. This tests server-auth TLS, not mTLS. |
| `/health` or `/metrics` indicates protected identity | Both endpoints are outside V3 RBAC protection. | They are not used as trust, identity, or authority observations. Use KV operations only. |
| Simple-token stale-state race | Official docs characterize simple tokens as test-only and describe rare invalid-token race. | Pin/report test-only behavior. No production claim; an invalid-token response makes that case fail/INDETERMINATE rather than silently retrying into success. |
| Gateway HTTP 200 / misleading response | Gateway body/status can be malformed, partial, or semantically false. | Continue to parse the complete expected JSON response and verify Txn semantics; neither TLS nor HTTP status alone commits a transition. |
| Timeout/connection drop after Txn | Transport and auth errors can create UNKNOWN completion. | Existing stable transition ID and linearizable receipt resolution rules remain unchanged. No new ID, local fallback, or promotion. |
| Overclaiming fixture success | The same runner creates the CA, endpoint, server and users and observes the test. | Report implementation-level protocol/RBAC conformance in this generated one-member fixture only. No production provider, PKI, credential custody, operator independence, mTLS, multi-node, physical durability, or rollback claim. |

## Disposition

The GitHub-hosted ephemeral etcd environment is adequate for the exact tested scope if it has OpenSSL, the runner can bind loopback HTTPS, Python's TLS client verifies the generated CA and SAN, and the source capture redacts secrets before durable evidence. Current official docs support the selected protocol path. Proceed is justified for this independent NONCLAIM implementation probe only. Keep all production-provider identity, trust provisioning, lifecycle binding, independent administration, and Pass 220–222 root-transition work on HOLD. Do not promote or freeze.

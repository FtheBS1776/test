# Internal attack — TLS/RBAC fixture

Completed before implementation.

1. Wrong CA or hostname, expired/malformed certificate, and plaintext downgrade must fail before protected KV operations; no verification bypass or fallback.
2. Omitted/invalid bearer token and incorrect password must fail closed. TLS is not RBAC identity.
3. The least-privilege role must permit only the exact run-scoped namespace; read/write to its lexical neighbor must fail, and a privileged fixture verifier must confirm no denied write occurred.
4. Gateway TLS Common Name cannot be used as an RBAC principal; use password authentication and its bearer token only.
5. Generated passwords, tokens, and private keys must not enter command argv, workflow logs, exchange captures, crash messages, or uploaded artifacts. Capture only redacted setup status and no auth request/response body.
6. `/health` and `/metrics` are outside V3 RBAC. Never use them as identity, authority, or access-control evidence.
7. The etcd simple token is documented as test-only and has a known race. Do not claim production authentication; auth errors are failures/UNKNOWN, never retried into a passing claim.
8. Preserve adapter atomicity, stable transition identity, currentness, and fail-closed behavior. A transport/auth timeout cannot be treated as stale, successful, or permission to mint a new ID.

## First execution counterexample

Run 37203215898 returned HTTP 400 for `/v3/auth/role/grant`. Its etcd server log records the decoded request with only `name` and `auth: permission not given`. The initial fixture body placed `permType`, `key`, and `range_end` at the top level; protobuf ignored those unknown fields. Therefore an HTTP success from a future grant call is not enough. The repair candidate must use the pinned v3.6.5 nested `perm` object and then independently read the role back and prove it contains exactly one `READWRITE` interval `[prefix, prefix_end)`. Keep the first failure as counterevidence.

No production provider identity, independent PKI, mTLS identity, cluster-wide resilience, physical durability, or rollback conclusion is in scope.

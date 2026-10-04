# Pass 219 → Pass 225 bounded etcd integration experiment — NONCLAIM

## Read this first

This is a separately identified bounded implementation experiment. Pass 186 remains controlling. Passes 187–233 remain NONCLAIM. This package does not promote or freeze any pass.

### Bootstrap and verification order

1. Independently compute the outer ZIP SHA-256 and compare it with the value supplied with this package.
2. Extract into a clean directory; do not overlay it on previous files.
3. Run `python3 VERIFY_PACKAGE.py <package.zip>`.
4. Read, in order: `PRIOR_EXPERIENCE_AUDIT.md`, `INTERNAL_ATTACK.md`, `EXTERNAL_RESEARCH.md`, `CROSS_ATTACK.md`, `CONFORMANCE_SCOPE.md`, `SOURCE_LINEAGE.md`, and `WORKFLOW_NOTES.md`.
5. For a local real-etcd rehearsal, run `python3 run_integration_evidence.py --output <new-empty-output-directory> --expected-source-manifest "$(sha256sum SOURCE_MANIFEST.json | cut -d ' ' -f1)" --release-archive <verified-etcd-v3.6.5-linux-amd64.tar.gz>`.
6. For the GitHub evidence path, place `WORKFLOW_TEMPLATE.yml` byte-for-byte at `.github/workflows/pass219-etcd-integration.yml` on the isolated branch `nonclaim/pass219-etcd-integration-20261004`. A push to that branch runs the bounded harness; `workflow_dispatch` is included as an optional manual trigger after the workflow file exists on the default branch. Do not merge it to the default branch for this test. Retrieve and independently verify the artifact. A workflow run is evidence only after adjudication.

## Tested scope

- Real etcd v3.6.5 process, one local member, HTTP gateway, loopback, no TLS and no authentication.
- Fresh linearizable Range request (`serializable=false`) whose adapter observation carries the caller's challenge; etcd does not receive or certify the challenge. Exact authority-value compare; conditional transaction writes successor, stable receipt, global execution consumption, and one small outbox intent atomically.
- Sibling activation, stale parent, ID collision, exact replay, malformed state, provider-ID mismatch, read-challenge separation, and response-loss reconciliation.
- Maximum one effect in the fixture and a 64 KiB client request cap. This is not full Pass 219 behavior for arbitrary effect count/size.
- Genesis is test-fixture setup. Lifecycle change during activation is injected by a fixture transaction to test the Compare race; it is not root-authorized lifecycle rotation.
- This does not establish Pass 222 root authorization integration, production TLS/auth/provider administration, independent genesis, custody/recovery, multi-member etcd behavior, physical durability, or whole-world rollback resistance.

The one-element effect bound is a test-scope guard prompted by etcd transaction limits. The adapter does not split oversized effects across transactions. No generalized effect-size contract is claimed.

## Authority boundary

Provider identifiers and fixture lifecycle fields in this test are declared inputs, not trust anchors. HTTP response cluster IDs, revisions, run IDs, artifact hashes, and green status do not create authority. There is no local SQLite fallback. Errors or missing evidence do not become PASS. Disposition remains NONCLAIM pending independent adjudication.

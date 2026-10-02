# Correspondence and internal inspection before research or repair

2026-10-02; Pass 186 controls; all proposed work NONCLAIM.
Amendment SHA256 c89d73a8d07e0d52ff883ee47ea08595e53652a1d1fa80aa426d32a8e9c47c35.

L7 REUSE: exact bytes and run identity matter but do not confer authority; incomplete/failed runs cannot become PASS. A green job, artifact digest, or declared provider name is not independently administered production trust.
L2 REUSE: separate controller authority, execution, observations and later verification; exact-current compare and receipt commit remain one transaction; a retry is not a new logical transition. Shared runner/operator is one common-cause domain. Preserve all failed runs.
Genie REUSE: implementation conformance only to explicit tested contract, no generalization to untested environments.
EXP-010 ADAPT: repository commit + workflow + executable + run/attempt + raw evidence binding; preserve chronology and failures. Do not transfer beacon, seed, freshness or one-shot rules to this test.
Prior evidence: verified handoff correspondence and the independently inspected Pass230 original/R2 repair. No claim of freshly rereading all historical L7/L2/Genie sources.

Internal findings on exact supplied workflow:
1. Verify-required-files only checks existence. Neither embedded manifest nor amendment verifier is actually invoked, contrary to notes claiming package hash verification.
2. Original Pass230 txn stdin uses compare/success/failure words rather than blank-delimited grammar; previously independently confirmed against official client. It also overwrites initialization state, erases previous result directory, duplicates endpoint env/CLI, and lacks invocation timeouts. Preserve original identity; execute repaired subject under distinct identity if approved by audit.
3. Official container startup defaults and listen address are unspecified. An internal health check can pass while host-mapped port is unreachable. Verify actual image entrypoint/listen semantics before relying on it.
4. Image and action tags float. Client archive is neither checksum-verified nor retained with a measured identity. Use pinned versions/digests/commits and measure binaries; no new trust system required.
5. Service startup precedes all steps; startup failure can prevent in-job evidence capture. Prefer explicit startup after creating evidence so process logs and exit status can be retained.
6. Evidence omits some early failure details and successful preflight code. Copy of result directory may fail. Inspect failure propagation and artifact finalization. Missing output is incomplete, never success.
7. Sequential reads do not establish multi-node linearizability, failover, unknown-commit resolution, physical durability, or production identity. They can observe configured reads, conditional transaction, shared write revisions and stable replay in a single real member.
8. Namespace uses run+attempt, useful bounded isolation, not universal execution-ID authority.
9. Existing repository and workflow context must be inspected before changes; avoid repurposing EXP010 execution. No production secrets needed. Private-repo billing is unknown; no cost assumption.

Mandatory benign regression checks after research: manifest mismatch rejection; exact repaired client framing already measured; failure/timeout exit preserved; startup failure leaves logs; no reuse of evidence directory; workflow permissions/triggers/action pins; final artifact metadata and complete file hashes; incomplete evidence classified INDETERMINATE.

Genuinely new authority machinery: none. ADAPT existing gate and environment/evidence wrapper only. Mature domains: GitHub runner lifecycle, artifacts and etcd deployment. Current primary-source research and cross-check required next, before repair/execution.
Remaining stronger HOLDs even if test passes: independent provisioning/admin, production TLS/auth/custody, multi-node failures, rollback and physical durability.

# Delayed submission/retry correspondence, research and cross-check — NONCLAIM

2026-10-06 UTC. Pass 186 controls; no promotion/freeze. Existing GitHub and transport/quorum captures remain unchanged.

Read before this design: exact Pass225 contract and integration decision, Pass231/232 status, Pass233 protocol, successor frontier/stop rule, transport/quorum coverage/checkpoint and owned fixture sources. A concrete uncovered behavior exists in obligation 6: a request accepted by a transport intermediary may remain pending after client timeout and a linearizable receipt read showing absence. This branch uses ordinary transactions on exclusively owned loopback processes. It is not a production or security exploit test.

Prior correspondence and initial internal critique:
- L7 REUSE: missing observations are UNKNOWN; exact request/subject/attempt bindings matter. Shared controller/runner is a common-cause domain.
- L2 REUSE: a receipt read linearizes at its own point; absence then does not cancel an outstanding write. Keep the same logical request and receipt identity. Compare exact parent value/revision and receipt absence atomically; write successor+full receipt together. Separate authority permission, execution, observation and verification.
- Genie REUSE: accept only the exact tested schedules. EXP010 ADAPT: bind source/runtime/workflow/run/attempt, preserve errors; no beacon/seed/fresh executor rule.
- Defeated inference under review: timeout plus missing receipt means NOT_COMMITTED, allowing a fresh logical transition. The existing correct decision is UNKNOWN; no new ID is minted here.
- First critique: a proxy delaying before forwarding is not an etcd operation already in Raft, leader loss, a packet partition, or proof of every arbitrary in-flight outcome. It supplies a concrete transport-pending schedule only. Require actual accepted bytes, a real client TimeoutError before forward, a normal receipt read before release, and later upstream response as a witness excluded from reconciliation inputs.
- A positive control must traverse the same fixed single-request relay. The relay accepts only exact selected bytes, only /v3/kv/txn, only a fixed owned 127.0.0.1 upstream, bounded length and waits. No general proxy, host firewall changes, external target, credentials or public listener.
- Cleanup must release/join owned threads, stop owned processes before deleting data, and seal errors. Reusing output directories is forbidden. Local preparation is separate from remote execution.

Current primary-source research retrieved after initial review, before implementation:
1. https://etcd.io/docs/v3.6/learning/api_guarantees/ — atomic KV calls; one write revision per transaction; timeout/network disruption can leave the client's operation status uncertain. Default reads are linearizable; serializable is not authority-currentness.
2. https://etcd.io/docs/v3.6/dev-guide/api_grpc_gateway/ — /v3 JSON gateway; exact byte keys/values use base64. No production authentication claim from this plaintext fixture.
3. https://docs.github.com/en/actions/reference/security/secure-use — full commit action pins, minimal permissions and shared runner trust limits.
4. https://docs.github.com/en/billing/concepts/product-billing/github-actions — standard hosted runners on public repositories are free; artifact storage has separate quotas. Use the existing authorized public test repository, standard ubuntu-24.04, no cache, small evidence, one-day artifact retention. Account storage balance is not observed; no promise about actual account-wide charges.

Cross-check before implementation: REUSE the prior pinned etcd 3.6.5 binary identities and exclusive owned fixture helper. ADAPT only the narrow relay schedule: (a) ordinary positive response; (b) held request released after timeout+absent receipt, then committed; (c) exact same request retry commits while first request is held, and releasing the original fails its Compare. Require at most one state update and unchanged full key metadata on final retry. The source will record the exact timeline and both request bodies. The result will not be labeled a full Pass225 adapter proof, trusted production provider, independent administration, physical durability or arbitrary Raft cancellation behavior.

No new authority mechanism is introduced. Required review remains by the continuing controller; no fresh blind reviewer or delegated agent is claimed. Existing independent provisioning/custody/recovery/rollback/physical HOLDs remain separate. A failed engineering case is retained as INDETERMINATE, not automatically rerun or repaired into a passing history.

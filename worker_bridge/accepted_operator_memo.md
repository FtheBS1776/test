# Operator decision: persisted worker bridge, attempt 2

Task: `genie-worker-bridge-review-20261008`. Do not expand automated response routing until explicit task/input binding is checked. This feedback revision reviews the original sealed source; it neither reviews nor approves the controller's reported repair.

## Evidence and review scope

The original hashes match `source_v1/bridge.py`, `source_v1/test_bridge.py` and `CORRESPONDENCE_AND_PLAN.md`. Canonical manifest SHA-256 is `c6c9281c8c7a66a497f3106b2e174d5f4e8cb80325ec0228e28dc6df6d6f8ae2`, matching dispatch attempt 2. This digest uses sorted, compact UTF-8 JSON, not formatted file bytes. I read the original code and persisted feedback and performed local hashing. No tests or bridge code were executed. Candidate 1 omitted the routing defect below; this revision addresses that actual review feedback.

## Confirmed source-level routing defect

`submit(path,n,agent,text)` checks only the selected ledger's current attempt, bound agent and state. It receives neither the response's task ID nor input digest. Consider distinct task ledgers A and B, both WAITING_WORKER at attempt 1, both legitimately bound to reused agent X. Accidentally routing A's result to `submit(B,1,X,text_A)` passes these checks and installs A's text as B's candidate. No hostile database rewrite is required: the wrong ledger path suffices.

Likewise, `review(path,n,candidate_hash,decision,reason)` does not accept or compare task/input identity. If A and B have the same attempt number and identical candidate text, A's review routed to B can accept B. Hashing exact text distinguishes bytes, not their task context. `effect_db()` subsequently derives the effect from B's task and checks its internally consistent acceptance record, so it cannot recover the lost response context. These mechanisms follow from code inspection; they were not dynamically demonstrated by this worker.

Require explicit task ID and input digest on bind/submit/review envelopes, compare them to the persisted request before mutation, and retain them in acceptance validation. Add cross-ledger negatives using reused agents and identical text. The controller reports a repair, but revised top-level source and its tests remain unreviewed here; its success needs separately bound evidence.

## Dispatch, review and recovery

`request()` persists an attempt before returning DISPATCH_ONCE. Repeated requests while waiting return RECONCILE_WORKER rather than redispatch. An unbound attempt cannot distinguish “never invoked” from “invoked, acknowledgement lost.” Reconcile host evidence; null agent identity is not permission to invoke again. A running controller calls the model interface; Python supplies no model invocation or autonomous background service.

Within the selected ledger, changed duplicate candidates and stale attempts reject. Candidate/state and review/state updates are transactional; repair carries feedback into another bounded attempt, then HOLD at exhaustion. The reviewer label is a trusted-host assertion, not authenticated independent approval or semantic proof.

Delivery requires accepted bytes and uses a stable task-derived effect identity. After a sink commit with lost acknowledgement, replay can deduplicate the same effect and read the destination before recording DELIVERED. Fresh status readback prevents cached completion from proving a missing destination. Preserve UNKNOWN; do not silently replace the sink. The supplied tests describe these paths, but their presence is not an executed PASS.

## Remaining decisions and limits

Pin imported `report_sink` and `stateful_subject`: the three-file manifest does not cover their executable behavior. Persist host reconciliation evidence without mistaking it for invocation proof. Provide an inspection/recovery procedure for interruption after exclusive ledger-file creation but before schema completion; avoid automatic overwrite.

Prioritize verified routing repair, then dependency pinning and reconciliation before broader automation. Shared ancestry and role-scoped shared files provide neither independent evidence nor hostile-worker isolation. Whole-store rollback resistance, arbitrary infrastructure recovery, production trust and promotion remain outside this trial.

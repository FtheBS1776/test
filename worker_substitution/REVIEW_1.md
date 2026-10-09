# Exact candidate source/content review

Disposition: no blocking command-shape or fixture-logic defect found by source inspection; one diagnostic wording clarification is recommended below. Root execution and adjudication remain required. This is one bounded reviewer turn with the same shared model and ancestry, not independent proof or additional provider coverage. No candidate block, source program or tests were executed, and no candidate/source/ledger was modified.

## Computed subjects

| Subject | SHA-256 |
|---|---|
| model_output/QUICKSTART_1.md | a75b7f959dad7164497d4f50aee8752331e0617622b63cf287a437fad36f6403 |
| model_output/STATUS_1.json | f761779cbd4bd80a25c699cbabe4d4ab83ab52b7f1b13781f97d724a3a58d02c |
| active_runner/runner.py | d5450a38cf5aa4e9f6356b213fb15ddee2b751ba5101e6e17991ee6922363cd3 |
| active_runner/run_status.py | af0fdad950a7d1849ea04d5e3670acffde5d1bf4c4e9468017a29c70047327cf |
| run_queue/run_policy.py | ac708a3b3ad4927d58ead75a89825ffcbf43fa79a34f6a606567a38d282af543 |

Read README_FIRST.md before the candidate, metadata and actual source. The guide hash matches the assigned subject and worker metadata. The status CLI pins the inspected runner hash; that runner pins the inspected queue hash. This review did not independently rerun the prior dependency suites or establish authenticity of the repository.

## Inspection findings

**CLI shapes align.** Queue positional order is QUEUE OPERATION; `init` and `enqueue` consume direct policy/plan stdin. Runner positional order is QUEUE RUN_ID OWNED_ROOT OPERATION. Its main passes stdin fields as keyword arguments to `callback`, whose parameter is `supplied`. The guide correctly sends `supplied` plus exactly outcome/agent/evidence, agent/text, or candidate_hash/decision/reason. Status takes precisely QUEUE RUN_ID OWNED_ROOT. Queue stop accepts the documented reason object.

**The fixture is truthfully deterministic.** The guide explicitly labels the fake agent, deterministic candidate and observation evidence NO MODEL CALL. It distinguishes one charged reservation from an observed live model invocation, performs a separate exact-byte fixture review and does not credit the fixture as reasoning or worker substitution. Actual runner code emits actions and callbacks; none of the shown commands invokes an external model. Reported substitution acceptance must come from separate root evidence.

**Expected transitions are supported by source.** Fresh step requests, reserves and journals before returning INVOKE_WORKER; the next waiting step reconciles without new permission. Submission moves to review. Delivery requires accepted content and host observation, then queue completion performs destination readback. Status distinguishes historical queue state from fresh sink evidence. After queue COMPLETE, callback token validation rejects the terminal submission because entries must be ACTIVE/HOLD; the guide expects exit 2 and REJECT rather than treating an old callback as fresh permission.

**Preservation and stop boundaries are accurate.** `root.mkdir()` executes before any queue/task writes and has no exist_ok option. An existing directory fails; the block neither removes nor resets it. Bash errexit propagates that failure. Repairs and uncertain dispatch consume existing bounded reservations. Stopped accepted work does not call delivery, although existing sink evidence can still reconcile historical completion. No background/concurrent/rollback/authenticated-receipt claim is made.

**Minor wording ambiguity:** “Missing/partial state remains UNKNOWN” in the diagnostic paragraph is too broad if read as covering the queue itself. The inspected status CLI maps missing/partial per-task stores to nested UNKNOWN, but missing/partial queue or missing owned root can produce top-level REJECT/nonzero. Suggested clarification: “Missing/partial per-task stores appear as UNKNOWN; unreadable queue, invalid run context or missing owned root can reject the diagnostic.” This does not invalidate the shown fresh fixture path.

The action table omits the runner's RECONCILE_HOST fallback. An optional row should direct preservation and existing-call inspection, never new invocation. Its omission does not affect the block's serial normal path; do not infer that the table exhaustively lists every fallback.

## Root validation proposals, not results

Execute the exact unchanged block from the required repository root using a new owned directory; retain stdout/return codes and inspect actual sink application count. Repeat with the same directory and verify the exclusive guard fails before changing evidence. Check the final fresh status and terminal callback rejection. Treat stopped-before-delivery, exhausted-budget and missing-queue diagnostic cases as separate checks if needed to substantiate the surrounding prose; the happy-path block itself does not exercise those cases.

No promotion, publication, deployment, new spending or old provider experiment was performed or authorized by this review.

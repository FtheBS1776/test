# Before-design journal reuse audit

## Exact scope

Read worker_substitution_checkpoint/README_FIRST.md and the canonical roadmap's next authorized unit: remove duplicated journal validation through a read-only helper, preserving behavior and exact source bindings. Inspected current sources only:

| Subject | SHA-256 |
|---|---|
| host_adapter/journal.py | 8e5d5b2fc39dce31f2a1bce4617ec60e726dd84c5f60be914fb1eb0c1fc9e1d7 |
| active_runner/run_status.py | af0fdad950a7d1849ea04d5e3670acffde5d1bf4c4e9468017a29c70047327cf |

This is one bounded same-model/shared-ancestry source-review turn, not independent proof. No source was changed or executed, no tests/provider experiments were run, and no later revision is covered retrospectively. This plan does not authorize production, spending, deployment, promotion or resetting completed budgets.

## Extraction boundary

Extract the existing body under journal.status's connection wrapper into `status_db(db)` without changing its validation or returned fields. Keep `status(path)` responsible for its existing owned connection/transaction and delegate to that helper. The helper must neither open another connection nor commit/rollback/close the caller's transaction. Diagnostic callers retain their existing mode=ro/query_only transaction, schema checks, stricter checks and diagnostic projection. Avoid making read-only diagnostics depend on journal.status(path), which opens mode=rw.

## Behavior the diagnostic adapter must preserve

1. **Schema and absence:** diagnostic checks both host_calls and host_observations schema before any no-call return. Missing/misordered columns must remain nested UNKNOWN with HOST_RECORD_UNKNOWN_OR_INCONSISTENT and preserve=true. A valid schema with no current call returns UNKNOWN plus NO_RECORDED_HOST_CALL, without preserve=true. Journal's no-call output has no corresponding diagnostic reason and must be adapted deliberately.
2. **Exact types and goal:** diagnostic requires `type(req.attempt) is int`, `type(event.attempt) is int`, equality to the current attempt, and request goal equal to the plan goal. Journal uses equality alone and does not compare goal. Rehashed boolean `true` or floating `1.0` can equal integer 1; missing/altered goals can satisfy shared checks. Keep these stricter adapter checks for every event, including UNKNOWN events, within the same read transaction.
3. **Exception containment:** journal catches ValueError/TypeError/KeyError only, and initial task/call/attempt reads occur before that try. Diagnostic also catches AttributeError and sqlite3.Error around schema and journal reads. JSON arrays/null in a request/event can trigger `.get` AttributeError; missing tables or a failing cursor can escape the shared helper. Retain the adapter's wider catch. Otherwise a journal-local corruption can fall into task_report's outer catch and erase independently valid workflow/sink diagnostics.
4. **Projection, not passthrough:** existing diagnostic journal output contains status, host_outcome, agent, call_id, observation_count and independent_proof, with optional reason/preserve. It omits task_id, attempt, workflow_state and action returned by journal.status. On valid call with zero events, status is OBSERVED while host_outcome stays UNKNOWN. On inconsistency it resets agent and call_id to null and count to zero. Shared journal output retains the stored call_id even on inconsistency; do not leak that as validated diagnostic identity. Translate HOST_RECORD_INCONSISTENT to the existing diagnostic reason.
5. **Independent observations:** do not gate fresh sink observation on an accepted journal result. Existing task_report reports journal inconsistency separately while valid ACCEPTED/DELIVERED acceptance records can still support exact fresh sink readback. Conversely queue COMPLETE alone never confirms the sink. No candidate, payload or event evidence body should enter diagnostic JSON.
6. **Snapshot and currentness:** shared validation must use the same task transaction as workflow/plan/acceptance reads. Sink observer still opens a fresh read-only connection. Preserve the explicit separate-transactions/no-cross-store-atomicity scope. Wrong run must reject before task/sink inspection; missing task stores remain UNKNOWN without provisioning.
7. **Pins and history:** journal edits change queue's expected journal hash, then runner's queue hash, then diagnostic's runner hash. Update deliberately and retain old artifacts/review subjects. Source pin failures should still reject; do not bypass pins to simplify tests. Normal imports remain trusted-owned-source checks, not hostile-source isolation.

## Targeted attack matrix for root — proposals, not results

| Mutation or state | Expected diagnostic behavior |
|---|---|
| Valid schema, no call at attempt 0/current attempt | Exact prior NO_RECORDED_HOST_CALL shape |
| host_observations absent despite no call | Inconsistent UNKNOWN, not no-call success |
| Valid call with zero or only UNKNOWN events | OBSERVED plus UNKNOWN, accurate count/call identity |
| Consistent accepted events and bound agent | Same exact diagnostic fields before/after refactor |
| Rehash request with missing/changed goal; update saved request/call consistently | Diagnostic still UNKNOWN despite shared validator accepting the narrower contract |
| Rehash request/event attempt as true or 1.0 | Diagnostic exact-type rejection, including UNKNOWN events |
| JSON list/null request or event; corrupt event body/hash; mismatched agents | Journal-local UNKNOWN with null agent/call and zero count; no traceback or unrelated workflow loss |
| Missing current attempt row with a recorded call | Inconsistent UNKNOWN |
| Inconsistent journal alongside valid ACCEPTED/DELIVERED effect | Preserve workflow and independently computed fresh sink result |
| Remove or alter sink after queue COMPLETE | UNKNOWN/MISMATCH fresh sink, historical COMPLETE unchanged |
| Shared helper on an already-open ro transaction | No open/commit/rollback/close; transaction remains usable; no bytecode/DB changes |
| journal.status(path) versus status_db on equivalent valid/corrupt fixtures | Existing wrapper result/exception behavior preserved by verbatim extraction |
| Wrong run; partial per-task store; source pin mismatch | Same rejection/UNKNOWN boundaries and no writes |

Use small fresh local fixtures and before/after output comparisons. Assertions about read-only operation should cover connection mode and unchanged stores; do not rerun old provider experiments. Record any intentional behavior change separately instead of calling it equivalent extraction. A scoped HOLD on this maintenance unit need not block independent authorized useful work.

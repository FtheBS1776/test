# Prior experience correspondence and reuse

Actual trigger: saved-log unit controller submitted evidence as string; journal rejected EVIDENCE_BOUND before recording. Root corrected evidence dict on same call/reservation, no redispatch. Formatter makes that input mistake reject before constructing an observation callback. Reuse existing field names/limits, not an invented new event or scheduler.

L7 defeated caller-forgeable observation and same-ID aliasing designs: syntactically valid payload is not execution evidence or authentic provenance. Copy run/task/input/attempt/slot/call exactly, compare request projection, and leave actual persisted authorization/agent/current-state binding to unchanged runner. A stale saved dispatch may render, then callback must reject; formatter must not claim currentness or recreate IDs.

L2 authority/execution/observation/verification distinct; UNKNOWN is not accepted execution and cannot grant new invocation permission. Caller-supplied evidence remains trusted host assertion, no signed remote receipt. Shared-model roles not independent roots. JSON detached-copy protects representation correspondence within a rendered payload, not mutable store rollback or host authenticity.

Pass187 local hashes/counters cannot establish rollback resistance; Pass212 fresh destination readback covers exact accepted code effect only. Read-only regular-file snapshots/strict JSON reuse ordinary stdlib behavior without hostile filesystem confinement/atomic multi-file/currentness/power-loss claim. Existing production/root/custody/rollback/remote-authenticity/hostile-isolation HOLDs stay separate. No old provider/etcd/lost-ack/EXP010 fixture repeated.

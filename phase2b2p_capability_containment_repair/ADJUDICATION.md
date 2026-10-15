# Adjudication

Decision: **PHASE 2B2 CAPABILITY-CONTAINMENT REPAIR PREFLIGHT VERIFIED -
NONCLAIM**.

Exactly one fresh fixture-only Windows Job Object run occurred.  It invoked no
Codex executable and no model.  Assignment and kill-on-close policy were
verified before releasing the fixture gate.  The monitor captured each of the
three Job members while active, retained PID-reuse-safe handles, hashed their
executable images, reconciled them with total-process accounting, terminated
the Job once, and observed zero active members afterward.

The controller contract rejects missing, late, duplicate, stale, nonempty, or
mismatched capability snapshots and rejects any tool-like event.  A future
Codex executable must bind an empty startup `AllowedTools` policy and emit the
exact snapshot before a model request.  That executable does not yet exist in
this branch, so `allow_model_turn=false` and `allow_new_invocation=false`.

No prior run was retried or reclassified.  No reviewer, event application,
session-driver progression, Phase 2C autonomy, main merge, promotion/freeze,
spending, production claim, or EXP010 activity occurred.

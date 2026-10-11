# Root adjudication — Genie standalone provider-neutral autodrive

Disposition: **ACCEPT_NONCLAIM_STANDALONE_AUTODRIVE**

Accepted subject: provider-neutral finite automatic progression composed from the already accepted `session_driver.py`, at exact tested commit `b72a5df41a28a6b9faec65d115fdf83cc7c5c846`, workflow run `38174048555`, job `114572527718`.

## Accepted narrow conclusions

- The standalone execution bridge reuses the accepted finite session driver rather than creating a second orchestration loop.
- The driver is exact-byte pinned at SHA-256 `89b0fd1ef48d5460dada5cc59b25072a10ec9b5c7049af25eabbb2d4464bf9d9`.
- The bridge adds no provider/network/subprocess/background-service surface.
- A newly created canonical run can, with injected trusted-local worker/reviewer callables, automatically traverse existing Genie worker observation, candidate submission, review, bounded repair, delivery, and STOP semantics without manual `advance` calls between normal successful actions.
- In the one-attempt happy path, exactly one worker hook and one reviewer hook produced `STOP / ALL_TASKS_COMPLETE`, a CONFIRMED sink, and a CONFIRMED result that remained `UNTRUSTED_ACCEPTED_TASK_DATA`.
- In the existing two-attempt repair budget, exactly two worker and two reviewer hooks were used; the first review requested REPAIR, the second ACCEPT, exactly two model-call reservations were consumed, and the run stopped ALL_TASKS_COMPLETE.
- UNKNOWN observation, worker exception, and token mismatch each fail closed. A later independent drive invokes no worker and consumes no second reservation.
- If the driver's action bound ends after same-session submission but before review, a later drive does not reconstruct reviewer eligibility. It invokes neither worker nor reviewer and returns `RECONCILE_REVIEW / NO_SESSION_SUBMISSION`.
- Source drift of the accepted session driver fails before any worker invocation or canonical-state creation.
- Canonical provisioner (11/11) and standalone owner (5/5) regressions remain green.

## Test evidence

Final environment: Windows Server 2025 / `windows-2025-vs2026`, exact CPython `3.12.10`.

- `STANDALONE_AUTODRIVE_STATIC_BOUNDARY_PASS`
- canonical provisioner: 11/11 PASS
- standalone owner: 5/5 PASS
- provider-neutral autodrive: 7/7 PASS
- `STANDALONE_AUTODRIVE_IMPORT_CLOSURE_PASS`

No Genie runtime/test warnings were emitted. GitHub emitted only its own Node-20 action deprecation notice during runner cleanup.

## Authority / claim limits

This disposition does **not** establish or perform:

- a real model/provider/API invocation;
- provider request identity/idempotency or authenticated remote invocation proof;
- credentials, pricing, billing, quotas, or network timeout behavior;
- independence of worker/reviewer evidence when backed by common model/provider ancestry;
- persistent same-session reviewer eligibility across process restarts;
- always-on/background autonomy after the process exits;
- pause/resume;
- migration/import of historical state;
- execution on the user's physical machine;
- plugin installation/connection;
- final GUI/installer/production readiness;
- authority promotion, freeze, main merge, or EXP010 execution.

The autonomy claim is deliberately bounded: successful in-process injected worker/reviewer cycles no longer require repeated human continuation commands. It is not yet a usable real-model standalone product.

Pass 186 remains inherited controlling. This unit remains NONCLAIM.

## Next frontier

The next unavoidable external-integration choice is a concrete provider adapter. Before implementation, compare current provider/local options using the standing cost, maintenance, compatibility, and uncertainty rules. Prefer a design where providers are replaceable adapters and where an ambiguous provider/network outcome maps into the accepted UNKNOWN/no-retry semantics rather than automatic replay.

> Current isolated repair adoption: reused from fa4e291cfd1aa7147f39f359008f8d74a2f69798, adapted to the current candidate source pins, explicit queue cost policy and input materials. This is not a new accepted Windows build. Root README and exact source package identify supported evidence.

# Standalone provider-neutral execution bridge — NONCLAIM contract

## Purpose

Compose the already accepted finite `shared_interfaces/session_driver.py` into the minimal standalone owner so a local run can progress automatically through existing Genie worker/reviewer hooks without repeated manual `advance` calls.

This unit does **not** implement a model provider, network client, API key, billing path, daemon, background service, or new reasoning engine. It accepts injected trusted-local `worker` and `reviewer` callables only.

## Reuse decision

Decision: **REUSE** the accepted session driver; do not implement a second orchestration loop.

Prior host-return evidence established the key invariants to preserve:

- execution, observation, verification, and authority are distinct;
- a hook call or transport return is not itself authoritative observation;
- absence of an observation never implies permission to retry;
- original run/task/input/attempt/slot/call bindings must survive the worker return exactly;
- uncertain outcomes preserve the charged/original state and fail closed;
- reviewer decisions bind the exact candidate hash and token;
- same-model/shared-provider roles are not independent evidence roots.

The bridge exact-byte pins the already accepted `session_driver.py` raw SHA-256:

`872903f1eaec93fce406662382fcadc896d28e8ce894cf60ae083d3e02dc5ab8`

The driver itself retains its existing pinned `run_events.py` / controller / core chain. The bridge adds no callback semantics.

## API

`drive(run_name, worker, reviewer, max_actions=64, notify=None, costs=None, materials=None)`:

1. exact-load the accepted session driver;
2. load the fixed canonical live-state registry through the accepted Windows binder;
3. call `session_driver.drive_run(...)` exactly once;
4. return the driver's detached terminal dictionary unchanged.

Setup/source/live-state failures are sanitized as bridge-local setup errors. Once `drive_run` is entered, its existing terminal semantics remain controlling and are not reclassified.

## Worker boundary

The driver invokes the injected worker only after the existing controller emits a valid `INVOKE_WORKER` action. The worker receives the exact detached action including token/request.

A valid accepted worker reply remains exactly:

- original token;
- `outcome = OBSERVED_ACCEPTED`;
- bound agent identity;
- nonempty evidence object under existing journal constraints;
- bounded candidate text.

`UNKNOWN`, malformed reply, token mismatch, exception, failed observation, or failed submission returns/preserves the driver's existing UNKNOWN/reconcile semantics. The bridge never retries a worker because no result/observation was seen.

## Reviewer boundary

The injected reviewer is called only after the same driver session submitted a candidate and the existing controller emits `REVIEW_CANDIDATE` for the exact token/candidate hash. The existing driver records the review through the accepted event/callback surface.

The bridge never invents ACCEPT/REPAIR or substitutes a reviewer result.

## Bounded automatic progression

The existing driver may advance repeatedly within `max_actions` and may therefore perform bounded repair attempts already authorized by the existing queue policy/budgets.

This is finite in-process automatic progression, not an always-on daemon. Terminal STOP/HOLD/UNKNOWN/RECONCILE or the driver action bound ends the call.

If the driver loses its in-memory same-session submission eligibility (for example after an action-limit boundary before review), a later drive must preserve the existing conservative `RECONCILE_REVIEW` behavior rather than reconstructing or replaying review authority.

## Provider-specific future work

A later adapter may implement one concrete provider/worker callable. That adapter must separately address current provider API semantics, credentials, cost, request identity/idempotency if available, timeout/unknown invocation outcomes, and evidence capture.

Provider-specific uncertainty must map into this bridge's existing UNKNOWN/no-retry semantics. A network exception after a request may have been accepted by the provider; it is never automatic retry permission.

## Nonclaims

This unit does not establish:

- any real model/provider invocation;
- provider API idempotency or authenticated invocation proof;
- independent worker/reviewer evidence when both use shared ancestry;
- after-process/always-on autonomy;
- pause/resume;
- migration of historical state;
- execution on the user's physical machine;
- plugin installation/connection;
- production readiness, authority promotion, freeze, main merge, or EXP010 execution.


## Material, cost and operator-control repair

Before entering the driver, validate exact task coverage and UTF-8 material hashes against the existing queue plans. `materials` maps task IDs to text, bounded to 1 MiB each. Attach the original goal/request and detached UNTRUSTED_TASK_INPUT to both hooks; preserve the original token. Bad/missing material fails before a call reservation. `costs` passes through to the existing queue-owned admission; absence never implies free capacity. The owner reuses the queue's pure policy validation instead of mirroring it.

The owner/CLI `stop` operation uses the existing queue stop contract without a model/planner/plugin call. It prevents future dispatch through the selected run; it does not promise to cancel an in-flight external effect. Binder or required verification failure has no automatic alternate-state or model fallback. Test restoration inspects disposable copied stores through the same status owner only; historical readability is not authoritative currentness.

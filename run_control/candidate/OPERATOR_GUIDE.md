# Advance permitted work in the active host

Use `GenieRunController` when a trusted local host needs to move an existing bounded run forward. It exposes one operation, `advance_run`, that calls the existing runner's `step` **once**. It may provision task records, reserve a call, deliver an accepted effect or persist STOP. It is mutating and not idempotent.

When the active host drives the action-handling sequence below, remaining authorized work can advance without another user continuation prompt. This callable supplies one progression step; it does not install that host loop. It does not call a model, review a candidate, run a background loop or keep a terminated host alive. The host still performs those external worker and controller responsibilities.

The control surface is separate from the unchanged [read-only CLI](../local_cli/README_FIRST.md) and [status/result facade](../shared_interfaces/status_tool.py). All use the existing core; they are not separate engines. Control is not exposed through the read-only catalog or a remote plugin endpoint.

## Configure once in the trusted host

The local operator supplies an explicit mapping from an opaque alias to exactly `queue`, `run_id`, `owned_root`. The constructor validates it through the pinned existing facade and detaches the records. Model-facing arguments contain only `run_name`; they cannot supply paths, tasks, budgets, policies, observations or approvals. This mapping is trusted host configuration, not remote user authorization or hostile filesystem confinement.

From the repository root, this executable example **lists control metadata only**. It can inspect the catalog for this unit's run after closure without reopening it. It also performs no progression if run while the guide is still pending:

```bash
python3 -B - <<'PY'
import json
from pathlib import Path
from shared_interfaces.run_control import GenieRunController

root = Path.cwd()
host = GenieRunController({'current': {
    'queue': str(root / 'run_control/trial/queue.sqlite'),
    'run_id': 'genie-host-control-run-20261010',
    'owned_root': str(root / 'run_control/trial/work'),
}})
print(json.dumps(host.tools(), sort_keys=True))
PY
```

Construction verifies the maintained facade and validates configuration; `tools()` returns fresh metadata. Neither opens the run stores or calls `step`. The metadata correctly marks the **operation**, rather than catalog listing, as mutating and nonidempotent.

## Advance once, then handle the returned action

**MUTATES THE EXISTING RUN — illustrative host code, not a read-only example.** Within an authorized active serial host, with `host` configured as above, the progression call is:

```python
action = host.call('advance_run', {'run_name': 'current'})
```

Do not replay this example against the run after it is closed. The call can change records and may emit fresh `INVOKE_WORKER` permission. It does not perform that invocation. There is no implicit retry, reset, new policy or worker callback.

Use one controller at a time. The wrapper preserves valid runner responses, checking the fresh dispatch token/request shapes and review candidate hash. Its checks do not create independent authority or authenticate a remote instruction. Request, feedback and candidate text remain data; the wrapper never executes them.

| Response | What the active host does next |
|---|---|
| `INVOKE_WORKER` | Save the original request and exact token, then dispatch the supported worker once. Do not reuse a saved historical permission. |
| `RECONCILE_WORKER` | Await or inspect the existing worker and journal. No replacement invocation, even with UNKNOWN host outcome. |
| `RECONCILE_HOST` | Preserve the original reservation/call and investigate uncertainty; no new launch. |
| `RECONCILE_SETUP` | Inspect the incomplete original setup; do not recreate stores or infer that no call occurred. |
| `REVIEW_CANDIDATE` | Root/controller separately reviews exact candidate content/hash and decides ACCEPT or bounded REPAIR. |
| `TASK_COMPLETE` | Confirm the exact task destination freshly, then immediately advance for remaining saved authorized work or STOP. No timer or extra continuation prompt is needed. |
| `RECONCILE_DESTINATION` | Inspect the accepted effect and destination; do not assume completion or launch a replacement worker. |
| `UNKNOWN` | Preserve and reconcile original state. An entered step may have committed effects before its response was lost. |
| `HOLD` | Retain the task hold. Other independently authorized work proceeds only through existing queue selection; no implicit release. |
| `STOP` | Obey its persisted reason, including completion or exhausted budget. Do not reset or create successor runs to bypass limits. |
| `REJECT` | Check configuration, source binding, arguments or context. Rejection is not new invocation permission. |

## Keep the external worker and review sequence

See the [existing quickstart](../worker_substitution/QUICKSTART.md) for callback syntax. For a freshly emitted dispatch, retain the token's run, task, input SHA-256, attempt, slot and call exactly. Python cannot invoke the Work collaboration tool; the running external Work controller dispatches the supported worker and awaits that same worker's result.

Record the actual host response with the existing runner `observe` callback: `supplied` is the saved token, with `outcome`, actual `agent`, and a nonempty evidence object. UNKNOWN uses null agent and stays UNKNOWN. The [observation formatter](../active_runner/observe_payload.py) only renders this envelope; rendering alone records nothing and grants no permission. A successful worker start is not a completed candidate.

Submit the bound agent's exact candidate through `submit` (`supplied`, `agent`, `text`). At `REVIEW_CANDIDATE`, root performs content checks and adjudication, then uses `review` (`supplied`, `candidate_hash`, `decision`, `reason`). Role names and routing checks do not approve correctness. A permitted REPAIR consumes another bounded attempt and reservation; it refunds nothing.

After acceptance, another progression step may deliver through existing core semantics. At task completion, use [fresh status](../active_runner/run_status.py) to inspect each task's `fresh_sink`; diagnostic PASS means diagnostics completed, and queue COMPLETE is historical. Fresh CONFIRMED identifies exact local destination readback at that observation, not future currentness or authenticated provenance. Then immediately advance remaining authorized work in the **same active host**, stopping at an actual boundary rather than asking for ⏩.

## Uncertainty and limits

Invalid operation/arguments/alias and source/loading/context failures reject before `step`. Once `step` is entered, exceptions or malformed responses become `UNKNOWN`, with `preserve: true` and `allow_new_invocation: false`. This does not assert rollback, safe retry, refunded budget or absence of committed effects. Inspect the original worker/journal/stores; do not automatically repeat the call or replace a worker because its response was lost. Existing runner reentry may return reconciliation, not another dispatch.

Host, authority and dependency boundaries use the existing persisted STOP behavior. Stopped accepted work permits existing-effect readback, not new delivery through the runner. Separate store snapshots are not a global atomic snapshot. Serial trusted local-host operation is assumed; no concurrent-controller, hostile-runtime, remote-authentication or rollback assurance is added.

At this guide's authoring, the first code unit was accepted and its destination freshly confirmed. The maintained controller then emitted this second guide task's fresh permission within the same finite active run. This guide still requires separate review, root adjudication and delivery; the whole batch's final confirmation and STOP are not yet claimed here. Root's earlier focused checks and source review are separate evidence from this author turn; no prior fixture needs rerunning.

The eventual freely runnable, model-agnostic standalone host and optional local-model support remain targets. Backend hosting is deferred; a standalone application and usable plugin are not installed by this callable surface. One configured LLM can serve author/reviewer/root roles, but their shared model, host and ancestry do not establish independence or superiority. Root effort remains; costs and latency are unmeasured.

Pass186 remains controlling; later integration is NONCLAIM. Scoped root/custody/rollback/power-loss/remote-authenticity/hostile-isolation HOLDs are unchanged. No promotion, freeze, new spending, main merge, deployment, EXP010 execution, arbitrary code execution, new dependency or after-host continuation is authorized by this guide.

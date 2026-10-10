# Immediate host continuation — bounded NONCLAIM

The goal is immediate progress through remaining authorized work while the Work host stays active, without repeated ⏩ prompts. An hourly activation schedule does not supply that task-to-task loop. Reuse the existing host and runner now; establish any capability to continue after the host ends separately.

See the [operator quickstart](../worker_substitution/QUICKSTART.md), [runner scope](README_FIRST.md) and [repository map](../README.md). No new commands, installer, adapter or engine schema are introduced here.

## Three distinct capabilities

| Capability | Meaning and current scope |
|---|---|
| Activation | A user request or permitted schedule starts a host turn. This does not itself advance every task or preserve a local execution session. |
| Active progression | The running trusted Work controller immediately handles runner actions, observes worker results, reviews candidates and selects the next saved authorized task. Current collaboration tools support this finite serial work. |
| After-host execution | A separately supported execution host must remain available or resume under established access and authorization. Persistent task records alone do not execute a model or keep a host alive. This capability remains open here. |

At `TASK_COMPLETE`, obtain fresh per-task destination evidence and call `step` again within the same active host. Do not wait for a timer or ask the user merely to say continue. If authorized tasks are exhausted, persist `STOP`; a new plausible task is not automatically authorized. Genuine permission, budget, dependency or unresolved-state boundaries remain stopping points.

## Existing integration seam

[runner.py](runner.py) exposes `step(queue, run_id, root)` and `callback(queue, run_id, root, operation, supplied, **payload)`. Python emits actions; it cannot invoke the Work collaboration tool. The active external controller invokes the supported worker, awaits that existing worker, performs root content adjudication and advances the runner. Root/controller effort remains real work; removing continuation prompts does not remove that effort.

| Action or event | Required host response |
|---|---|
| Newly emitted `INVOKE_WORKER` | Save exact original request/token and dispatch the supported worker once. Bind run/task/input SHA-256/attempt/slot/call; a saved historical dispatch is not fresh permission. |
| Actual accepted host response | Apply `observe` with `supplied` equal to the saved token and fields `outcome`, `agent`, `evidence`. Accepted observation uses `OBSERVED_ACCEPTED`, the actual agent and a nonempty evidence object. Await the same worker; successful start is not a finished candidate. |
| Candidate returned | Apply `submit` with the exact token, bound `agent` and exact candidate `text`. Preserve content/hash correspondence. |
| `REVIEW_CANDIDATE` | Review exact content/hash separately from routing. Apply `review` with `candidate_hash`, `decision` (`ACCEPT` or `REPAIR`) and `reason`. A permitted repair is another bounded attempt, not a refunded call. |
| `TASK_COMPLETE` | Check fresh exact destination confirmation, then immediately call `step` for remaining authorized work or persisted STOP. Historical completion alone is insufficient. |
| `RECONCILE_WORKER` | Inspect/await the existing worker and journal. No new invocation permission, including when recorded host outcome is UNKNOWN. |
| `RECONCILE_HOST` | Preserve reservation/call uncertainty and reconcile the original invocation. No replacement launch. |
| `RECONCILE_SETUP` | Preserve the incomplete setup and inspect original records. Do not recreate missing stores or infer that no call happened. |
| `UNKNOWN` | Preserve partial/inconsistent state; investigate within scope. A lost response remains UNKNOWN, charged to its reservation, without retry launch. |
| `RECONCILE_DESTINATION` | Inspect the accepted effect and destination without assuming completion. Do not create a new model invocation. |
| `HOLD` | Retain the task hold; no implicit release. Independently authorized work may proceed only as permitted by existing queue selection and scoped boundaries. |
| `STOP` | Obey the persisted reason, including `ALL_TASKS_COMPLETE` and `CALL_BUDGET_EXHAUSTED`. No budget reset or successor-run bypass. |
| `REJECT` | Inspect exact callback/argument/state bindings. Rejection is not permission to resubmit under a fabricated identity or relaunch. |

[observe_payload.py](observe_payload.py) only renders the existing envelope; rendering neither records observation nor grants execution permission. The unchanged callback validates against actual current records. On host/authority/dependency boundaries, the existing queue stop reasons are `HOST_ENDED`, `AUTHORITY_BOUNDARY`, `DEPENDENCY_BOUNDARY`. A stopped accepted task permits existing-effect readback, not new delivery through the runner.

[run_status.py](run_status.py) separates historical queue state from fresh per-task `fresh_sink`. Diagnostic `PASS` means the diagnostic completed; queue `COMPLETE` is history. Fresh `CONFIRMED` binds the observed exact local effect, not future currentness, authenticity or rollback resistance. Separate store transactions are not an atomic cross-store snapshot.

## Supported-host reuse assessment

The supplied root preflight found `node`, `npm` and `git` on PATH, but no `codex` or `gh`; Python packages `openai`, `agents` and `pydantic_ai` were absent. These observations identify local availability only, not account access, model entitlement or successful execution. The active Work collaboration tools already supply the supported worker invocation seam for this finite host. No additional framework is needed to use it.

Official sources reviewed by root on **2026-10-10 UTC** describe a possible future host:

- [Codex App Server](https://learn.chatgpt.com/docs/app-server) provides a JSON-RPC protocol with `initialize`, `thread/start` and `turn/start`, thread/turn identities and `turn/completed` status. An integration must distinguish a successful start from completion, retain exact identities/results and still route candidate acceptance through existing root adjudication.
- [ChatGPT-plan App Server guidance](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) requires authorized plan-use credentials. `model/list` can reflect a bundled catalog rather than an entitlement check. Documentation and catalog discovery do not demonstrate usable access.
- [Automations guidance](https://learn.chatgpt.com/docs/automations) describes scheduled activation; web scheduled tasks do not retain the local folder between runs. Scheduling therefore does not establish this repository's continuing local host or replace immediate active progression.

App Server is a supported-protocol candidate, not installed, adopted or execution-verified here. Access and the exact supported protocol must be established before any new adapter is justified. This note makes no model-selection, entitlement, provider-diversity, installation, cost or live-access claim and requests no credential inspection, API call or spending.

## Retained limits

Completed narrow author/reviewer/root tasks demonstrate bounded work, not an unattended service or superiority over ordinary LLM work. Roles share model/host/ancestry and common causes; they are not independent evidence roots. The quickstart's preserved **NO MODEL CALL** fixture is separate from real host calls and need not be rerun for this clarification. Two preceding read-only audits are separate from this task's newly reserved author observation.

Pass186 remains controlling; later work is NONCLAIM. Root/bootstrap/custody, whole-store rollback, physical power-loss, remote authenticity and hostile-isolation HOLDs retain their scoped meanings. No production promotion, freeze, new spending, main merge, deployment, EXP010 execution, unlimited task discovery or background continuation after host death follows from this document. Its review, adjudication and exact fresh destination delivery are separate evidence steps.

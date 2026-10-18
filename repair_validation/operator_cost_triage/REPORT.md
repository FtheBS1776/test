# Active-host cost correspondence triage

Internal bounded read-only triage, 2026-10-18 UTC. Subject Git HEAD:
`938322b7c454521559cf6e4bd9ca79035dfe34b8`.
This is not strict-blind review or an independent evidential root.

## Finding: stale operational guidance omits current monetary prerequisite

The maintained code has an intentional distinction: low-level scheduling offers
and trusted external invocation admission. `active_runner/runner.py:99–111`
calls `bridge.request`, `queue.reserve` and `journal.begin`, then emits
`INVOKE_WORKER`. It never enters an external hook or invokes a model. This is
not by itself a monetary admission defect: the shared driver consumes that
offer and admits the exact action before entering a hook.

The direct operator guidance does not consistently preserve that distinction:

| Location | Current text/effect | Contradiction |
|---|---|---|
| `worker_substitution/QUICKSTART.md:7` | Real INVOKE_WORKER means active external Work host performs call once | Omits approved upper bound/admission; following this paragraph directly bypasses supported driver admission |
| `worker_substitution/QUICKSTART.md:99` | Active trusted Work host may dispatch newly reserved call once | Treats workflow reservation as sufficient permission |
| `worker_substitution/QUICKSTART.md:117` | At fresh action active Work controller performs real worker call once | No monetary prerequisite or current-driver route |
| `active_runner/README_FIRST.md:5` | Controller dispatches only fresh action | Correct necessary freshness condition, presented without equally necessary current monetary admission |
| `run_queue/README_FIRST.md:7` | Host order goes queue.reserve → journal.begin → controller tool | Describes old direct path without monetary admission, although the appended current recovery section at lines16–20 describes admission correctly |
| `session_driver/USAGE.md:27–28,39` | Callable/stream examples omit optional costs argument | Current defaults fail closed. Examples no longer explain how actual permitted invocation would be reached |

Root README line5 explicitly supersedes older next-action wording below. Its
current lines32–35 correctly require quote matching, and line73 parks the
model-task demonstration. Thus older root lines101–104 are stale guidance
risk, not evidence that the controlling current policy grants bypass. The
root still links the operator quickstart at line80 without an immediate
local warning in that quickstart. This makes the mismatch materially easy to
encounter through an otherwise supplied operator entry point.

`run_queue/OPERATOR_GUIDE.md` describes a specific historical trial and attributed
controller updates, not proof of a newly supported monetary path. Historical
workload contracts and fixture instructions should retain their original scope
and evidence rather than be retroactively represented as paid-model validation.

## Existing controls and bounded probe

The actual monetary owner is `run_queue/run_policy.py:186–223`, using the same
queue's `cost_actions`. `reserve` at lines78–102 only charges workflow slots.
`shared_interfaces/session_driver.py:98–103` uses author/repair role plus
operation `worker`; lines145–150 admit reviewer operation
`review:<candidate_sha256>` before hook entry. Unknown cost, unmatched quotes
and replay fail closed. Role/callable labels do not authenticate price bounds.

`probe.py` created two exclusive disposable stores beneath this report's
directory. It called source APIs only, never subject mains, external processes,
models, pilots or workflows. `RAW_OUTPUT.txt` preserves the complete successful
attempt (exit0). It established:

1. Fresh default policy, no `cost_policy`: `runner.step` emits a bound
   INVOKE_WORKER; workflow slots1, cost_actions0, default DISABLE_ALL, quotes{}.
2. Explicit attempt to admit asserted free author action is HOLD /
   COST_QUOTE_NOT_APPROVED. No external action was attempted.
3. Separate fresh default queue through `drive_run`: HOLD /
   COST_BOUND_UNKNOWN_OR_INVALID, zero worker/reviewer hook entries and zero
   actual model calls. The deliberately forbidden fake hooks were never entered.

This confirms a documentation seam rather than demonstrating model execution
or a shared-driver bypass. It does not establish an actually usable cost bound
for this Work host/account.

## Smallest reuse-based repair

Keep runner, queue, token and historical fixture semantics intact. Add a clear
current-operation notice to the existing quickstart and runner read-first;
revise present-tense direct-dispatch instructions/table entries to say a fresh
workflow action is necessary but does not grant monetary permission. Route
supported actual worker/reviewer invocation through the existing shared driver
with exact saved approved quotes and enforceable bounds. Clarify old direct
CLI recipe is no-model protocol exercise and not an alternative model launch
route. Add `costs` to driver documentation signatures/examples and explain
omission fails closed. Explicitly require progress callbacks to remain
observational: they run before admission and cannot dispatch on a reported
INVOKE_WORKER. No new budget service, quote registry, authority token, or runner
admission is necessary for this documented selected composition.

If a future operational manual-host adapter is supported, it must call this
same queue admission owner exactly once before external entry and preserve
uncertainty; that would require separately inspected source and integration
coverage, not this report's permission. No such adapter was added here.

## Limitations and preservation

No repository files were changed. No native host, SDK transport, subprocess,
network/provider, concurrency, whole-store rollback, power-loss, hostile host,
pricing provenance or invoice tests were attempted. Low-level primitives remain
callable by a trusted host; adversarial-host enforcement is outside their
contract. Explicit archives and unsupported launchers were not treated as
current dispatch permission. Existing completed evidence, scoped HOLDs,
mandatory deduplication rule, no spending, no live-pilot rerun, no merge,
deployment, scientific execution or master mutation exclusions remain intact.

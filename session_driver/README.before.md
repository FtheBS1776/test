# Genie: bounded reasoning and work orchestration

Genie is a model-agnostic prototype for governed planning, criticism, candidate production, repair and adjudication. It supports useful bounded work with one configured LLM and an active trusted ChatGPT Work controller. Author, reviewer and root/controller roles can share that model, host and ancestry; separate role names do not establish evidential independence or provider diversity.

Start with the [operator quickstart](worker_substitution/QUICKSTART.md) for exact CLI syntax and callback fields, then the [active-host scope](active_runner/README_FIRST.md). The quickstart's deterministic **NO MODEL CALL** fixture simulates callbacks; it is separate from actual host worker calls. Its historical recipe creates files and is not a prerequisite to repeat before using the tools.

The current priority is another concrete, independently authorized bounded task using existing components, with proportionate review and preserved evidence. Additional providers, an agent framework and new spending are not prerequisites. One-model usefulness beyond the narrow completed tasks is not proven; superiority, cost savings and latency improvements have not been measured.

## Component map

| Component | Existing entry point | Purpose |
|---|---|---|
| Queue | [run policy](run_queue/run_policy.py), [operator guide](run_queue/OPERATOR_GUIDE.md) | Saved plans, finite task/call reservations, selection and persisted STOP. |
| Active host composition | [runner](active_runner/runner.py) | Emits actions and validates callbacks against persisted bindings; does not invoke models. |
| Task ledger and journal | [bridge](worker_bridge/bridge.py), [journal](host_adapter/journal.py) | Candidate/review/effect records and trusted host observations. |
| Observation formatting | [observe payload](active_runner/observe_payload.py) | Read-only rendering of the existing callback envelope from original dispatch and evidence. |
| Current diagnostics | [run status](active_runner/run_status.py) | Separate queue history, task workflow, journal and fresh per-task sink readback. |
| Saved log reporting | [reporter](evidence_summary/report_logs.py), [strict parser](comparison_pilot/validation_summary.py) | Bounded captured-log summaries with explicit evidence scope. |
| Checkpoint integrity | [ZIP verifier](host_adapter/verify_checkpoint.py), [comparison](run_queue/compare_checkpoints.py) | Caller-anchored integrity checks and byte-bound checkpoint differences. |

Python emits workflow actions and cannot invoke the Work collaboration tool. Only the active external trusted host performs actual LLM calls. Work ends when that host ends; saved state supports later authorized inspection/resumption but provides no always-on or background execution service.

## Actual host sequence

1. Save the authorized bounded plan and original inputs. Use the existing queue policy and owned local stores; retain task, attempt and call limits. Reservations count uncertainty too, not just observed successful calls.
2. On a **newly emitted** `INVOKE_WORKER`, the active host dispatches once and saves the exact original request/token. The token binds run, task, input SHA-256, attempt, slot and call. `RECONCILE_WORKER`, `RECONCILE_HOST`, `RECONCILE_SETUP` and `UNKNOWN` grant no new invocation. Preserve gaps and investigate existing records.
3. Record the actual host response and nonempty evidence object. The formatter renders `supplied`, `outcome`, `agent`, `evidence`; compare them with the saved facts before the runner's `observe` callback. `UNKNOWN` stays UNKNOWN. Rendering does not record an observation, authenticate evidence or authorize relaunch; the callback remains the validator against current records.
4. Submit only the bound agent's exact candidate. Root/controller reviews content and hash separately from routing checks, choosing `ACCEPT` or a bounded `REPAIR`. A repair consumes another permitted attempt/reservation; it refunds nothing.
5. Accepted work may be delivered through the existing owned inbox while the run permits delivery. Confirm the exact per-task effect by fresh destination readback, including a separate fresh status process. An accepted candidate alone is not a confirmed destination.
6. Select the next authorized READY task or persist `STOP`. Respect `ALL_TASKS_COMPLETE`, budget exhaustion and host/authority/dependency boundaries. Do not reset a closed run, recreate missing stores or manufacture successor runs to bypass the budget. Stopped accepted work permits existing-effect readback, not new delivery through this runner.

## Read saved evidence without rerunning tests

From the repository root with Python 3.12, this read-only command summarizes a concrete saved unittest log:

```bash
python3.12 -B comparison_pilot/validation_summary.py report_format/FROZEN_RESULTS.txt --format unittest
```

It prints a `TEST_LOG_SUMMARY_ONLY` result. It does not execute the logged tests or establish authenticity, semantic correctness, coverage beyond that log, or current destination state. `NO_COVERAGE`/count0 remains explicit; malformed evidence is `REJECT`.

For original rich JSON check logs, the reporter offers explicit `checks` format alongside `unittest` and unchanged strict `json`. `checks` projects only status/count/check names/boolean flags through the unchanged pinned parser. It lists `projection.ignored_top_fields` and `projection.ignored_check_fields`; per-check status and metadata values supply no summary authority. Full JSON, including ignored metadata, is checked for decoding/duplicate/nonfinite errors. Entry hash/size bind the original captured raw bytes, not a projection file. Capture is bounded to 1 MiB per log and is not an atomic multi-file snapshot.

The reporter creates a new output exclusively and preserves existing outputs; use its documented syntax only with a separately selected new owned path. `REPORT_WRITTEN` means file creation, never aggregate PASS or test execution. Inspect individual PASS/FAIL/NO_COVERAGE/REJECT entries. Execution and fresh-sink claims remain `NONE`.

## Evidence and authority limits

Diagnostic top-level `PASS` means the diagnostic completed. Queue `COMPLETE` is historical; inspect every task's `fresh_sink`. `CONFIRMED` describes exact local destination readback at that observation, not future currentness or rollback resistance. Separate store transactions are not a global atomic snapshot.

ZIP verification requires the caller's expected outer SHA-256, checks the manifest and bounded archive contents, and never extracts or executes archive code. `INTEGRITY_ONLY` and byte differences do not establish authenticity or semantic acceptance. Do not substitute a package's self-declared hash for an external caller anchor.

Canonical approved roadmap and continuation documents travel in the delivered verifiable checkpoint. They are not canonical root Git files; repository evidence snapshots must not be assumed synchronized copies. Consult the delivered checkpoint with its saved caller anchor for the controlling priorities and retained history.

Root/bootstrap/custody, whole-store rollback, physical power-loss, remote authenticity and hostile-worker isolation HOLDs remain scoped. They do not globally block independently authorized bounded prototype work. Trusted serial local-host operation does not establish hostile-path confinement or signed remote execution evidence. No production readiness, authority promotion, freeze, new spending, main merge, deployment or EXP010 execution is authorized by this entry point.

## Immediate continuation

See the [host continuation note](active_runner/HOST_CONTINUATION.md) for immediate task-to-task progression, scheduled activation and execution-host lifetime. The current active host can advance permitted runner actions without an hourly wait or another continuation prompt.

## Shared core and interfaces

The approved [shared-core roadmap](shared_interfaces/ROADMAP.md) retains one Genie engine for eventual standalone and plugin interfaces, with hosting deferred. The first [read-only callable status component](shared_interfaces/USAGE.md) reuses existing diagnostics; it is not an installed plugin or deployed backend. Start with its [verification notes](shared_interfaces/README_FIRST.md).


Local operator commands are available without writing a Python snippet: [CLI read-first guide](local_cli/README_FIRST.md) and [current roadmap continuation](local_cli/ROADMAP.md). The CLI reads status or accepted results through the same reviewed core; no model dispatch, plugin/server installation or backend hosting is included.


Trusted active hosts can now advance existing bounded runs through a separate mutating [control interface and operator guide](run_control/OPERATOR_GUIDE.md). The [current roadmap](run_control/ROADMAP.md) records a finite two-task batch, fresh results and STOP. The external host still performs worker calls and review; this interface installs no background loop or backend.


The trusted host can also [record one worker observation, submission or root review](run_events/USAGE.md) through the unchanged callback core. [Event-interface roadmap notes](run_events/ROADMAP.md) preserve the current scope: callback acknowledgement is not model proof or automatic review, and no host loop or backend is installed.

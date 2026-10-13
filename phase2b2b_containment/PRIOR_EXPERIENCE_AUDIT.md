# Phase 2B2B prior-experience correspondence audit

This audit was completed on 2026-10-12 before the Phase 2B2A head was inspected and before Phase 2B2B branching or edits. It applies `brains10-pass230/PRE_RESEARCH_AUDIT.md`, `active_runner/REVIEW_PLAN.md`, `evidence_summary/CORRESPONDENCE.md`, `run_control/PRIOR_CORRESPONDENCE.md`, `run_events/PRIOR_CORRESPONDENCE.md`, `session_driver/PRIOR_CORRESPONDENCE.md`, `worker_bridge/CORRESPONDENCE_AND_PLAN.md`, `worker_substitution/PLAN_AND_CORRESPONDENCE.md`, `shared_interfaces/EXTERNAL_INTEGRATION_POLICY.md`, and the Phase 2A, 2B1, and 2B2A records.

1. Exact process identity and termination observation can support a bounded containment statement. They do not create controller authority, prove a worker ran correctly, authenticate content, establish reviewer independence, or authorize a callback.
2. Phase 2B2A explicitly left descendant process-tree control unresolved and explicitly excluded it from its accepted claim. A separate fixture-only preflight is therefore an `ADAPT`, while altering the accepted Phase 2B2A fixture would blur old and new evidence and is rejected.
3. The fixture must not be able to create its descendant until the parent has created the Job Object, set and queried the non-breakaway kill-on-close policy, assigned the process, verified membership, and sent an explicit gate. Ordinary `Popen` still permits trusted fixture startup before assignment, so this ordering does not prove hostile pre-assignment containment.
4. Windows Job Objects group processes as a unit, normally associate child processes with the parent's job, and can terminate associated processes when the last kill-on-close job handle closes. Nested-job support exists on Windows 8 and later. Those platform semantics are design inputs; local success remains limited to the exact tested host and process images.
5. Job assignment, active-count queries, retained process handles, image-path checks, termination, bounded waits, and active-zero readback are separate evidence steps. PID-only polling is insufficient because a PID can be reused.
6. Breakaway flags are not enabled. An assignment or nested-job incompatibility must fail closed. It may not silently degrade to direct-child-only cleanup while claiming tree control.
7. Deterministic failure before process entry may reject. Once process entry is attempted, assignment, release, report, query, termination, wait, or cleanup uncertainty remains `UNKNOWN`, preserves the one-shot state, and grants no new invocation permission. There is no retry, refund, reset, replacement, or alternate launcher path.
8. The selected host/child Python executables, Python DLLs, `_ctypes.pyd`, `kernel32.dll`, `conhost.exe`, fixture, argv, environment, and OS observation should be exact. This is deliberately a partial selected support set, not a complete CPython, standard-library, Windows, filesystem, or hardware closure.
9. A no-model fixture return is untrusted local test data. Local source hashes, tests, and same-host review remain common-cause evidence and do not establish rollback-resistant currentness or independent proof.
10. OpenAI's headless Codex guidance supports version-pinned, stdin-driven, structured-output CLI use, and its security guidance recommends isolated workloads and keeping credentials outside the child. Those remain future design inputs only. The Codex plan is not executed and its effective tools remain `NOT_PROBED`.

## Disposition

- Separate Windows-only Job Object helper, gated no-model process-tree fixture, partial runtime profile, and disposable adversarial tests: **ADAPT**.
- Preserve all Phase 2B2A files byte-for-byte: **REUSE**.
- Live Codex execution, auth/model/provider selection, effective tool inventory, request semantic redaction, MCP exposure, callbacks, `session_driver`, and persistent Genie runs: **DEFER**.
- Caller-selected executable/argv/env/cwd, breakaway permission, retry after `UNKNOWN`, direct-child-only tree claim, hostile-sandbox claim, main merge, promotion/freeze, spending, and EXP010: **REJECT**.

Official design references checked 2026-10-12:

- https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject
- https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs
- https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex
- https://developers.openai.com/api/docs/guides/agents-api/environments/security

## Exact head inspected after this audit

- Local branch: `nonclaim/genie-phase-2b2a-isolation-launcher-20261012`
- Local commit: `dc221b2df1316e819f1ea980df838f709f5fb1c1`
- Published equivalent commit: `d0ebe348188a99682966f774eea5cfcd1d9894c2`
- Tree: `b19388bd8393df9e0022a768fe22509c76552512`
- Parent: `eef5ac5e432a0d66ab5e41c808a26cbb6712ee40`
- Worktree: clean
- New branch: `nonclaim/genie-phase-2b2b-containment-preflight-20261012`

# Genie: bounded reasoning and work orchestration

## Current isolated recovery candidate — 2026-10-18 UTC

This section is the current **source-candidate** view under the one master roadmap. It supersedes older next-action wording below, not historical evidence. It does not mutate the canonical master roadmap, grant production authority, or claim that every archived script is supported by this candidate.

Base: `ad508c63024087d0d38f489f6b42ee7c5f9af662`, tree `2b1bad31e09f6c3bd98e1aa22e85640fec547b50`. The selected standalone owner/bridge, Windows binder and provisioner sources are reused from `fa4e291cfd1aa7147f39f359008f8d74a2f69798`; the divergent branch was not merged. Source imports, policy validation, material binding, stop behavior and transitive source pins are reconciled in this candidate. Its exact changed bytes and test logs travel with the recovery source package.

### Current capability and owner correspondence

| Scope | Maintained owner / supported evidence | Disposition and remaining gap |
|---|---|---|
| R01 status/frontiers | This current section, existing master process | Last accessible master snapshot is v11; intended Oct11 additions do not prove an uncertain save. No master write or save retry. Phase2C and separate standalone source history remain NONCLAIM. |
| R02 ownership/configuration | Existing queue, shared driver, shared MCP consumer, standalone owner | Current quote policy and source materials are explicit; candidate/archived code is historical evidence, not an alternate maintained route. Unknown outside consumers remain a coverage gap. |
| R03 review compatibility | PilotHooks + active events/driver/bridge | Local candidate tests exercise the actual producer. Bound invalid schema is REPAIR; token/hash/unknown-decision failures remain UNKNOWN. Valid ACCEPT and bounded REPAIR retained. Separate-context v4 review found a cost-entry defect outside the R03 path; its report is preserved. The repaired v5 source returned bounded NO_DEFECT_FOUND in a fresh context, with native/SDK coverage explicitly limited. |
| R04 containment claim | Phase2C CONTRACT / attested adapter | Corrected to CREATE_NO_WINDOW, then verified Job assignment before semantic input. No pre-assignment suspension or hostile-worker assurance claim. |
| R05 nonmutating inspection | Phase2C verify_sealed.py | Default inspection returns data without evidence writes. Explicit reports require a new external path; copied input manifests remain unchanged. Original verifier/result history preserved. |
| R06 resource lifetime | Existing driver tests | Two nonclosing SQLite sites repaired; duplicate imported test execution removed. Fresh affected-suite Windows validation now passes. Exact identities/traces of the six historical Windows errors remain unavailable; this does not reconstruct their causes or erase them. |
| R07 cost admission | run_queue.run_policy, one existing queue database | Default denies unknown/unapproved cost. Immutable provisioned role quotes, modes and limits govern same-queue durable action reservations. Author/repair/reviewer hooks admit before entry. Original, alpha, recovery and attested exported Codex adapters deny before ledger/process entry; v4 separate review exposed the missed alpha route and same-function inspection found its recovery sibling. Actual paid/provider-bounded operation remains unavailable. |
| R08 MCP overlap | shared_interfaces/mcp_consumer.py, existing server route | Combine strict input types and argument bound with retained correlation, source pins and untrusted labels. Preserve structured-only consumer semantics expected by the server; alternate source/history retained. No universal superiority claim. |
| R09 package identity | Exact source candidate / historical host report | Historical b3945f3b107d178ac99634b12666631191c80359f8456fde2f0a076c83251bbb package retains only its reported Windows Codex CLI 0.162.1 route evidence. Current SDK transport and a separately rebuilt candidate package are checked on hosted VMs; no installation, distribution or user-machine/CLI compatibility claim. Current source reuses the existing live-state entry from the standalone branch. It reads the owner-created fixed root without seed/cache fallback; the v3 fixture route and its checks are superseded and preserved in their checkpoint/history. |
| R10 supported composition | Reused standalone bridge -> same driver | Goal/material/identity/stop tests are joined by native Windows publication and full published-state -> binder -> bridge -> driver coverage. Stop blocks future dispatch, not an already entered hook. The operational plugin now binds the same canonical owner state. CLI post-entry failures preserve UNKNOWN rather than being labeled bad input. No crash-durability or hostile-filesystem claim. |
| R11 premise/revision meaning | Existing evidence/transition contracts; task contract below | Input/output text is data. Premise statuses, support and dependent revisions must be explicit in useful task review. General runtime premise tracking is not established by this repair. |
| R12 historical lessons | Actual checks named below | Typed identity, uncertainty, common cause, historical restoration limits and separation of observation from authority are applied to current decisions. No science HOLD is inferred away. |
| R13 useful whole-system task | Existing useful-task milestone | This recovery produces usable source/evidence analysis, but deterministic hook replay is not an autonomous LLM research demonstration. Park that demonstration until an actual permitted cost-bounded model/host path is available. |
| R14 actionable continuation | This section + exact diff/test record | Use current reasons and owners, then historical records as needed. No new dashboard, status authority or persistent enforcement service. |
| R15 leanness/performance | Existing tests and owners | One driver, one cost owner, one maintained consumer. Removed 20 duplicate test executions while retaining 23 distinct driver/protocol methods. No measured end-to-end speedup or invoice saving is claimed. |

### Selected composition and effective controls

- Checked environments: local Linux/Python 3.12.14 and standard hosted Windows 2025/Ubuntu 24.04 runners with Python 3.12.10, temporary owned SQLite stores and deterministic no-model hooks. Windows binder/provisioner tests use the native APIs, with their mutable state confined to disposable namespaces.
- `drive_run(..., costs=...)` and standalone `drive(..., costs=..., materials=...)` are trusted local host APIs. Unknown cost fails closed before a hook. Zero cost must match an explicitly provisioned quote; included capacity is not assumed free.
- Fresh queue policies may include `cost_policy={mode, limit_micro_usd, authorization_ref, quotes}`. Modes are `DISABLE_ALL` (default), `ENABLE_LIMITED`, `ENABLE_ALL`. Quotes map role to exact `{max_micro_usd, quote_ref}`. Monetary values are integer micro-USD. Limited/all configurations in tests are simulations, not spending authorization. No actual paid configuration is installed.
- Monetary records extend the existing queue transaction owner in `cost_actions`; they are not another service/database. Replay never grants a second entry; uncertainty remains reserved. There is no reset/refund/migration API. Old queues without this table are preserved and denied dispatch, while read-only inspection remains available.
- Quote provenance and bound correctness are trusted-host preconditions, not authenticated provider evidence. Arbitrary callables, malicious host bypass, external historical scripts, restored whole stores and provider invoices are not made safe by a string quote reference. New tool/service/runner integrations must use this same admission owner before being supported. No paid fallback is installed.
- The four exported model-turn adapters (original, alpha, recovery and attested) lack an enforceable total-exposure contract and return `LIVE_COST_BOUND_UNAVAILABLE` before process/ledger entry. Their former post-entry public-route test is replaced by a pre-entry-denial test; old code/test history and Windows evidence remain in Git.
- Standalone materials are a detached task-ID/text mapping covering the selected queue. UTF-8 bytes must match the original plan input hash (maximum 1 MiB per task); both worker and reviewer receive the same `UNTRUSTED_TASK_INPUT`. No model-supplied path selects a source file.
- Read-only plugin status/result projection retains two tools. The unchanged exact MCP 2.3.0 closure is installed in an isolated environment and transport-tested, including stdio and loopback HTTP. Local HTTP tests require removing ambient proxy settings for that test process; the initial proxy/dependency failure is preserved. No extra SOCKS dependency or version relaxation was introduced.
- One Windows build/check recipe is shared by both workflows through the existing composite action. The seed-generation stage is removed for the operational live-state package; the earlier eight-script reuse result remains historical. Recovery validation uses only standard runners on the verified public repository, with no cache/artifact uploads or model credentials. It builds and tests a disposable executable; it does not publish/install the package. The live plugin reads the same fixed canonical root created by the standalone owner. It neither provisions nor replicates that state in PLUGIN_DATA.
- The former fixture-seeding entry and its five bootstrap methods are preserved in commit `c1c0a396881c798cd7503135e8958128c93febca` and `GENIE_RECOVERY_REPAIR_CANDIDATE_v3_20261018.zip`; they are retired from the maintained route, not represented as current live-state coverage. Current entry checks exercise live-binder failure, refusal of a valid-looking old cache, transport binding and no retry. Historical output/manifests are untouched.
- Live entry and registry CLI reuse the existing MCP server's single stdio runner. Standalone stdin parsing reuses the existing strict registry decoder helpers. Unexpected owner/CLI failures after entry return UNKNOWN/preserve/no-new-invocation; deterministic input rejection remains REJECT.


Same-function selection for R09/R10:

| Existing alternative | Operational difference | Selection |
|---|---|---|
| Fixture-seeding entry through v3/c1c0a39 | Copies historical seed into PLUGIN_DATA; useful package-test harness, not the standalone owner's current state | Superseded for operation; exact source/tests and negative/positive receipts preserved |
| Live entry from fa4e291c | Reads fixed OS-selected canonical root, no cache copy or fallback | Reuse, with explicit package imports and shared stdio owner; current core/cost/identity semantics retained |

The alternatives share a read-only MCP purpose but have different state semantics. The live route closes an existing integration gap; it is not an extra plugin, state registry, authority mechanism or master-roadmap milestone. The compiled test uses a fresh owner-created no-model run, not restored historical state. That demonstration remains distinct from actual model reasoning and user-host compatibility.

### Decision-specific lessons and remaining holds

Exact typed identity and same-ID aliasing lessons are exercised by R03 token/hash checks and R07 quote/replay binding. UNKNOWN preserves original call/reservation identities; lost review acknowledgement does not roll back a committed REPAIR. Restored copies may be readable, but do not establish live currentness or rollback resistance. Same-thread author/reviewer/controller roles remain common-cause; changed model labels are not independence.

The direct L7 v5.64 frozen successor record and post-freeze audit support artifact-specific FROZEN status for candidate `ed7e5b610463b70fe9b3526d5bb065e4c65b7448b5dcec50e699d90b90473168`. The newer Brains14 summary says PREFREEZE; that contradiction remains visible, with the exact artifact record controlling that artifact. No new L7 or Genie freeze is made here.

Pass186 remains the inherited baseline; later integration stays NONCLAIM. Independent trust/currentness, whole-store rollback, physical power loss, hostile-worker isolation, provider identity/custody and EXP010/LMR science HOLDs remain scoped and unresolved.

### Useful reasoning obligations and next eligible work

A supplied-document deliverable must separate supported, proposed, rejected and unresolved premises; identify source/claim relations and common ancestry; consider a competing interpretation; and name which dependent conclusions a revision affects. These are review obligations, not a new ontology or an automatic claim-promotion mechanism. An accepted report remains `UNTRUSTED_ACCEPTED_TASK_DATA`.

Current decisive results are in `REPAIR_TEST_RESULTS.txt`. Older manifests/test logs remain historical, tied to their original bytes; they are not expected to match repaired source. The R03 v2 review record is retained as a predecessor record, not a second current status authority.

The separate-context v4 review returned `DEFECT_FOUND`: the alpha entry could claim an operation and reach fake Popen without cost admission. The adjacent recovery entry had the same missing guard. Both now reuse the existing queue admission owner and denial contract. This adds no cost service or invocation permission. A focused shared regression covers all four exported model-turn adapters, fresh stores and preservation of existing uncertainty. The review's 24 passing probe methods include a deliberate defect reproduction; they are not a clean acceptance result. Original review source/logs are preserved under `repair_validation/review_v4/`; its complete evidence archive also retains fresh reproduction stores.

Standing repair and delegation authorization applies to this continuation. It does not authorize paid external capacity or change the remaining exclusions. Same-host/model-family separate review narrows common-context influence but does not create independent evidence roots.

Fresh separate-context v5 review returned `NO_DEFECT_FOUND` within its eight fake-only test groups; native Windows/SDK coverage in that review remains INDETERMINATE. Separate author validation of the exact tree passed 120 Windows methods, 19 queue checks, 25 bridge checks, eight SDK checks and the compiled no-model composition. These sources of evidence retain their different coverage and shared ancestry. Reports, independent test sources and raw outputs are preserved under `repair_validation/review_v4/` and `repair_validation/review_v5/`.

Eligible follow-up within existing R09/R13: obtain actual user-host compatibility observations for the read-only Windows plugin; independently establish an enforceable permitted host/model cost contract for one useful supplied-document task through the existing engine. Plugin installation is not a prerequisite for the existing active-host model route, and a read-only plugin connection would not itself enable model dispatch. The documentation-only cost recheck did not establish this account's bound, so the model-task demonstration remains parked. Repair and delegation do not need renewed approval; missing capabilities or work outside the repair scope must be resolved without inventing free exposure. The Windows, SDK and disposable-package validation gaps have been narrowed by the exact runs recorded in `REPAIR_TEST_RESULTS.txt`; an actual user host connection remains untested. No live-pilot rerun, paid call, paid provider/runner capacity, main merge, deployment, production promotion, freeze, canonical master save or scientific execution is authorized by this source package. Missing external capabilities are parked; unrelated safe repair work need not wait.

---


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
2. A **newly emitted** `INVOKE_WORKER` is a workflow offer, not sufficient monetary permission. Use the existing shared driver with reviewed enforceable bounds and exact saved approved role quotes; only its admitted worker hook may enter external work once. Save the exact original request/token. Never dispatch from progress notifications, which precede admission. The token binds run, task, input SHA-256, attempt, slot and call. `RECONCILE_WORKER`, `RECONCILE_HOST`, `RECONCILE_SETUP` and `UNKNOWN` grant no new invocation. Preserve gaps and investigate existing records.
3. Record the actual host response and nonempty evidence object. The formatter renders `supplied`, `outcome`, `agent`, `evidence`; compare them with the saved facts before the runner's `observe` callback. `UNKNOWN` stays UNKNOWN. Rendering does not record an observation, authenticate evidence or authorize relaunch; the callback remains the validator against current records.
4. Submit only the bound agent's exact candidate. Any external reviewer invocation requires its own admission through the same queue owner. Root/controller reviews content and hash separately from routing checks, choosing `ACCEPT` or a bounded `REPAIR`. A repair consumes another permitted attempt/reservation; it refunds nothing.
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


### Finite active-host driver

[Driver checkpoint](session_driver/README_FIRST.md), [host API/protocol](session_driver/USAGE.md), and [roadmap continuation](session_driver/ROADMAP.md). Accepted driver sequences existing authorized work immediately with external host worker/reviewer hooks.23 focused checks passed. Actual code delivery is freshCONFIRMED; successor guide request encountered stdin EOF and remains UNKNOWN with its reservation preserved. Full two-task host demonstration is OPEN; do not replay the saved pending request. No model API, background host, backend or plugin installed; existing authority/HOLD boundaries remain unchanged.


### Current-host return path

[Host entry checkpoint](host_return/README_FIRST.md), [host usage](host_return/USAGE.md), [plugin surface inventory](host_return/PLUGIN_ROUTING.json), and [roadmap continuation](host_return/ROADMAP.md). A fresh two-task interactive run completed both exact resultsCONFIRMED and STOPALLTASKSCOMPLETE, with actual supported author returns and separate reviews/rootdecisions. The root still bridges model tools; short ASCII transport only, no always-on or installed plugin claim. Earlier pending guide remainsUNKNOWN and untouched. New entry has9focusedchecks and explicit UNKNOWN exit3; authority/HOLD boundaries unchanged.

Local read-only function adapter (NONCLAIM): [entry](plugin_local/README_FIRST.md), [usage](plugin_local/USAGE.md), [roadmap addendum](plugin_local/ROADMAP.md). No installed plugin or model API dispatch claim.


ChatGPT MCP consumer projection (NONCLAIM): [entry](plugin_mcp_consumer/README_FIRST.md), [contract](plugin_mcp_consumer/CONTRACT.md), [research](plugin_mcp_consumer/RESEARCH.md). Reuses the accepted read-only adapter; no MCP server, plugin connection, backend or model dispatch is installed.

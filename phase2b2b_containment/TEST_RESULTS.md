# Phase 2B2B verification results

Environment: exact Phase 2A host CPython 3.12.14; exact direct child runtime and selected Windows support set in `RUNTIME_PROFILE.md`; Windows Job Objects only; standard library only. Runtime mismatch is an assertion failure, never a skipped green test.

## Final clean suites

| Suite | Result |
| --- | --- |
| `phase2b2b_containment.test_process_containment` | 19/19 passed |
| `phase2b2a_launcher.test_isolated_worker` | 27/27 passed |
| `phase2b_events.test_events_mcp` | 22/22 passed |
| `run_events.test_events` | 15/15 passed |
| `run_control.test_control` | 13/13 passed |
| `phase2a_controller.test_controller_mcp` | 14/14 passed |
| `plugin_mcp_consumer.test_consumer` | 11/11 passed |
| `plugin_mcp_server.test_mcp_server` | 8/8 passed |

Total final targeted/regression result: **129/129 passed, zero skips**.

## Containment and adversarial coverage

The exact real probe verified: job policy set/readback; no breakaway flags; one pinned Python member before release; assignment before the gate; four stable post-release members; exact two-Python/two-console-host image multiset; retained process handles; one `TerminateJobObject`; zero active members; and every retained handle signaled/terminated. A separate real tree closes the last live kill-on-close job handle and observes all four handles terminate.

Adversarial tests cover invalid ID, bad root/path/digest, immutable source rebinding, exact runtime/OS support files, job-creation failure, `Popen` uncertainty, pre-commit and post-commit assignment uncertainty, pre-delivery and post-delivery gate uncertainty, post-report timeout, malformed child report, termination API failure with kill-on-close fallback, cleanup uncertainty with cwd preservation, concurrent calls, exact one-spawn behavior, post-entry canonical UNKNOWN, and no process/termination retry. Each focused run performs 20 malformed-report cleanup cycles and 10 injected termination failures, asserts no fixture cwd remains on verified cleanup, asserts preservation when cleanup is uncertain, verifies the direct child's Windows process handle is closed, and asserts exactly one `TerminateJobObject` call per termination-failure probe. Import/call checks exclude model/provider, network, MCP, Genie control/event, and session-driver surfaces. The complete Phase 2B2A manifest is rehashed byte-for-byte.

The final cleanup-accuracy-repair probe ID is `6dfd671fd8c3050494718375eb22dc80e5ba135852fcdaaa8a98ee1b64da0e00`. It returned `VERIFIED`, observed active counts `1 -> 4 -> 0`, and explicitly returned `model_invoked=false`, `allow_new_invocation=false`, `complete_runtime_closure=false`, and `hostile_preassignment_containment=false`. No raw child output or persistent probe store was retained.

## Integrity readback

The final integrity verifier remeasured the unchanged Phase 2A baselines:

- protected repository files: 54 files, 215,767 bytes, aggregate `ba2cd2b1fb6b1ed6c84d59b7255c1435d91a9afb68fa76c16fc8bc10bef18170`;
- historical SQLite: 27 files, 1,024,000 bytes, aggregate `56a1f0dcea069ba31a0a09f573fd927eaee4e25900bb6f1554564ffabbe33837`;
- installed `genie-readonly`: 5 files, 22,133,322 bytes, aggregate `00e1057d09ea950a121f17a752c1d3934b993e785a17abcfb8959ab37d80fbef`;
- installed read-only state: 34 files, 224,723 bytes, aggregate `2e9437c1cadda4b81ccdc48683fcccc4688de3a5cee650ca05f8329e177e87e9`.

The ignored Phase 2A raw queue/inbox/task and call/post artifacts retain exact SHA-256 values `bd2088ed...`, `72e695...`, `59c3b8...`, `a77847...`, and `ff9133...`.

## Preserved red-test history

The initial focused run was 9/10 because a test's substring heuristic rejected the documentation sentence “No Codex”; AST import/call allowlists already showed no executable path. The heuristic was narrowed without changing implementation. The expanded suite initially ran 14/15 because a harness expected UNKNOWN on a deterministic pre-entry source mismatch; the contract correctly returns REJECT before process entry. That expectation was corrected.

Final independent audit then found two real cleanup defects. A malformed-report stress run reproduced 1 failure in 10 because the temporary cwd cleanup could race the still-live console host; live-member and owned-resource cleanup was reordered ahead of bounded inert-directory deletion. A separate injected failure showed `TerminateJobObject` was called twice after the first call became uncertain; a termination-attempt latch now prevents replay and uses the verified kill-on-close policy as fallback. The expanded timeout test first ran 17/18 because it sampled a legitimate transient three-member startup state before the second console host joined; the harness now waits for the contract's stable four-member state before injecting uncertainty. After that first repair, 10 consecutive complete focused suites passed (180/180 test-method executions, exercising 200 malformed-report and 100 injected-termination probes), followed by a clean 128-test combined run and a real probe.

The independent first-repair audit (source hashes recorded in `VERIFICATION.json`) added 100 malformed-report and 50 injected-termination stress cycles with zero failures or residual roots; 105 sequential real probes with a stable host handle count of 156 across four 25-probe checkpoints; and 32-way same-instance contention yielding exactly one `VERIFIED`, 31 `UNKNOWN`, and one spawn. It also exercised 20 post-commit assignments, 10 post-delivery gate failures, 10 post-report timeouts, and five injected `TerminateJobObject` failures covering 20 retained member handles. Every uncertain case remained one-shot and UNKNOWN, every retained handle signaled, and no Python process or audit-root residue remained.

The final accuracy audit found two remaining claim/implementation mismatches: the direct child's Windows `Popen` handle was left for object destruction, and directory deletion was not gated off after another cleanup step became uncertain. The final repair explicitly closes that process handle, deletes the cwd only when preceding cleanup remains verified, and otherwise preserves it under canonical UNKNOWN. The runtime-profile wording was also narrowed: Windows version is observed and test-pinned, not enforced by the runtime checker. On the final source, 10 consecutive complete focused suites passed (190/190 test-method executions, exercising 200 malformed-report and 100 injected-termination probes), followed by the clean 129-test combined run above and the final real probe.

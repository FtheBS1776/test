# Phase 2B2A verification results

Environment: Windows local Codex; exact Phase 2A CPython 3.12.14 at `C:\Users\aaron\Documents\Codex\phase2a-venv\Scripts\python.exe`, executable SHA-256 `dcdc8a4ef3c108d7d11f7a8afea50502c8f41763d118f1a94dafc90c74f1614c`; standard library only. Runtime mismatch is an assertion failure, not a skipped green suite.

## Final clean suites

| Suite | Result |
| --- | --- |
| `phase2b2a_launcher.test_isolated_worker` | 27/27 passed |
| `phase2b_events.test_events_mcp` | 22/22 passed |
| `run_events.test_events` | 15/15 passed |
| `run_control.test_control` | 13/13 passed |
| `phase2a_controller.test_controller_mcp` | 14/14 passed |
| `plugin_mcp_consumer.test_consumer` | 11/11 passed |
| `plugin_mcp_server.test_mcp_server` | 8/8 passed |

Total final targeted/regression result: **110/110 passed**.

## Fixture-boundary coverage

The real Windows subprocess tests establish the exact seven-element fixture argv (`python.exe -I -S -B fixture --mode success`), no shell, three pipes, closed file descriptors, hidden-window creation flag, a minimal exact-key environment with the exact execution-class value, a fresh non-repository cwd, and a committed `CLAIMED` row visible at process entry. The launch ID is not added to argv or stdin. The final stdin envelope is independently capped at 65,536 bytes.

The success case returns one `UNTRUSTED_NO_MODEL_FIXTURE_OUTPUT / NO_MODEL_CALL`, records `RETURNED`, and exposes neither request text nor environment secrets in the parent result. The fixture contains no subprocess, network, OpenAI, Codex, MCP, or Genie mutation reference. That direct-source check is a bounded heuristic plus exact source hash, not proof about the full runtime/OS closure.

Adversarial cases cover bad shape/type/count/UTF-8 bounds; relative and repository paths; wrong mode, interpreter/fixture digest, aliases and hard links; non-SQLite/wrong/triggered claim schemas; a hard link injected after profile validation; claim-before-spawn ordering; same-ID crossed/concurrent calls; a distinct-ID limitation test; exception immediately after committed claim; source rehash failure after claim; lost return recording; `KeyboardInterrupt`; and exact pipe-limit/off-by-one behavior.

Every non-success fixture mode returns canonical UNKNOWN and never respawns the same launch ID: crash, nonzero, timeout, malformed JSON, oversize stdout/stderr, nonempty stderr with zero exit, invalid UTF-8, duplicate key, nonfinite value, extra/missing field, wrong request/stdin/argv hash, wrong protocol/classification/environment/cwd/model/proposal. The real timeout test confirms the direct child is no longer running after the bounded cleanup attempt.

The Codex-plan test independently pins the expected CLI version, path, executable hash, full base argv, exact disabled-feature tuple, stdin marker, absent model selection, absent auth, and `NOT_PROBED` tool inventory while asserting no process spawn.

## Integrity readback

The final read-only integrity verifier remeasured exactly the Phase 2A baselines:

- protected repository files: 54 files, 215,767 bytes, aggregate `ba2cd2b1fb6b1ed6c84d59b7255c1435d91a9afb68fa76c16fc8bc10bef18170`;
- historical SQLite: 27 files, 1,024,000 bytes, aggregate `56a1f0dcea069ba31a0a09f573fd927eaee4e25900bb6f1554564ffabbe33837`;
- installed `genie-readonly`: 5 files, 22,133,322 bytes, aggregate `00e1057d09ea950a121f17a752c1d3934b993e785a17abcfb8959ab37d80fbef`;
- installed read-only state: 34 files, 224,723 bytes, aggregate `2e9437c1cadda4b81ccdc48683fcccc4688de3a5cee650ca05f8329e177e87e9`.

The preserved ignored Phase 2A raw queue/inbox/task databases and raw call/post snapshots also retain SHA-256 values `bd2088ed...`, `72e695...`, `59c3b8...`, `a77847...`, and `ff9133...` respectively. No persistent Phase 2B2A store or raw child output was retained.

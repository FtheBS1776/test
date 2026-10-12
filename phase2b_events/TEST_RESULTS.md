# Phase 2B1 verification results

Environment: Windows local Codex, CPython 3.12.14 in the unchanged Phase 2A isolated environment, exact `plugin_mcp_server/requirements.lock.txt` closure plus `pywin32==312`.

## Final clean suites

| Suite | Result |
| --- | --- |
| `phase2b_events.test_events_mcp` | 22/22 passed |
| `run_events.test_events` | 15/15 passed |
| `run_control.test_control` | 13/13 passed |
| `phase2a_controller.test_controller_mcp` | 14/14 passed |
| `plugin_mcp_consumer.test_consumer` | 11/11 passed |
| `plugin_mcp_server.test_mcp_server` | 8/8 passed |

Total final targeted/regression result: **83/83 passed**.

The Phase 2B1 suite covers exact one-tool discovery/schema/annotations; source, schema, and SDK closure pins; bad tool/type/alias/token/payload/strict-JSON rejection; one detached delegation; consumer and server canonical UNKNOWN; commit-then-lost-response preservation; crossed-token no-effect behavior; operation and review-decision correspondence; delegate-mutation attacks; safe model-facing text; metadata mutants; real Windows stdio with spaces; all three operations on a disposable deterministic synthetic fixture; HTTP-option rejection; static absence of dispatch/progression/driver/network paths; Phase 2A manifest validation; and historical state hashes.

## Disposable stdio evidence

All event calls used temporary stores deleted after each test. The full deterministic sequence returned:

1. `observe -> RECORDED`
2. `submit -> SUBMITTED`
3. `review -> ACCEPT`

The harness supplied the observation, fixed candidate, and ACCEPT decision. No worker/reviewer model ran. Post-sequence task state was `ACCEPTED`, while the queue remained `ACTIVE`, one reservation remained charged, and reports/applications remained zero. No later `advance_run` call occurred, so there was no delivery, completion, or fresh destination confirmation.

The lost-response test performed one committed observation and then raised. The projection returned canonical UNKNOWN with preservation and no new invocation permission; it made no retry and retained the ACTIVE queue entry, charged reservation, WAITING_WORKER task, one host call, one observation, and zero sink effects.

## Supplemental accepted-driver harness limitation

A broad 104-test command included `session_driver.test_driver` and `session_driver.test_protocol`; the latter imports the former, so its class ran twice. Ninety-two test executions completed cleanly. Twelve errors were the same six pre-existing Windows temporary-directory cleanup failures repeated twice: those tests leave read-only SQLite inspection handles open when `TemporaryDirectory` tries to remove `task.sqlite`. The behavior assertions ran before cleanup. Phase 2B1 did not edit the accepted driver or its harness. The final 83-test in-scope/regression command excludes that unrelated cleanup-defective harness and passes cleanly.

## Integrity readback

The final read-only integrity verifier remeasured exactly the Phase 2A baselines:

- protected repository files: 54 files, 215,767 bytes, aggregate `ba2cd2b1fb6b1ed6c84d59b7255c1435d91a9afb68fa76c16fc8bc10bef18170`;
- historical SQLite: 27 files, 1,024,000 bytes, aggregate `56a1f0dcea069ba31a0a09f573fd927eaee4e25900bb6f1554564ffabbe33837`;
- installed `genie-readonly`: 5 files, 22,133,322 bytes, aggregate `00e1057d09ea950a121f17a752c1d3934b993e785a17abcfb8959ab37d80fbef`;
- installed read-only state: 34 files, 224,723 bytes, aggregate `2e9437c1cadda4b81ccdc48683fcccc4688de3a5cee650ca05f8329e177e87e9`.

The preserved ignored Phase 2A raw queue/inbox/task databases and raw call/post snapshots also match their recorded SHA-256 values. No persistent Phase 2B1 stores were created.

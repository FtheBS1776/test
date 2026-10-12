# Phase 2A verification results

Environment: Windows local Codex, CPython 3.12.14 in an isolated virtual environment, exact `plugin_mcp_server/requirements.lock.txt` closure plus `pywin32==312`.

## Final passing suites

| Suite | Result |
| --- | --- |
| `phase2a_controller.test_controller_mcp` | 14/14 passed |
| `run_control.test_control` | 13/13 passed |
| `plugin_mcp_consumer.test_consumer` | 11/11 passed |
| `plugin_mcp_server.test_mcp_server` | 8/8 passed |

Total final targeted/regression result: **46/46 passed**.

The Phase 2A suite covers exact single-tool discovery and annotations, source/SDK pins, bad tool/type/alias/input rejection, one delegation, canonical UNKNOWN/no retry, commit-then-exception preservation with no refund/reset, metadata mutations, malformed projections, Windows stdio operation with paths containing spaces, HTTP-option rejection, static Phase 2B/network exclusions, exact read-only/historical hashes, and the recorded pilot's bound token and persisted state.

## Repaired Phase 2A test-harness defect

The first Phase 2A suite run passed 11 tests and ended with two Windows temporary-directory cleanup errors because SQLite inspection connections were not explicitly closed. The implementation result assertions had passed. The harness was repaired with explicit connection closing; the final suite passes 14/14. This repair did not touch Genie core or the read-only package.

## Pre-existing legacy fixture limitation

`shared_interfaces.test_status_tool` passes 11/12 tests. `test_actual_existing_readback_and_sources` errors before exercising an interface because the selected base commit does not contain `active_runner/trial/queue.sqlite`. The missing historical fixture was not recreated because that would violate Phase 2A's prohibition on mutating or synthesizing historical run state. This is not a Phase 2A controller failure; all other tests in that legacy module pass.

## Live recorded pilot

Exactly one stdio MCP call was made against the tracked fresh synthetic alias, with zero retries. It returned `INVOKE_WORKER` as a bound action only. Read-only inspection afterward verified:

- queue entry `ACTIVE`; one reservation remains charged;
- task `WAITING_WORKER`; one host-call record;
- zero host observations;
- null agent, candidate, candidate hash, and review fields;
- zero reports and zero applications;
- no worker/reviewer model invocation and no event callback.

No second call was made against the recorded run.

The raw pilot SQLite stores, raw result, and raw post-call snapshot remain preserved and charged on the originating host. They are gitignored and not published; the branch records bounded state counts, exact raw-database hashes, and one-way token/request commitments instead. The recorded-state test validates those redacted snapshots on every checkout and additionally compares the live result and read-only stores when they are present locally.

# Genie Desktop host-compatibility package verification — 2026-10-11/12 UTC

Disposition: **ACCEPT_NONCLAIM_HOST_COMPAT_PACKAGE**

This record supersedes neither the earlier internal-package adjudication nor the first user-delivery record. It binds a newer package intended for a fresh **local ChatGPT Desktop Work/Codex** host-registration test after the prior cloud-host verification proved invalid for local stdio execution.

## Tested source

- Branch: `nonclaim/genie-desktop-plugin-package-20261011`
- Tested commit: `a98d11782443a1084518a910d1b4196c07974ea9`
- Workflow run: `38194737754`
- Job: `114634801711`
- Result: SUCCESS

## Host compatibility hardening

The package retains the portable Agent Plugins representation:

- root `plugin.json`
- root `mcp.json`

and additionally carries the currently supported OpenAI/Codex compatibility fallback:

- `.codex-plugin/plugin.json`
- root `.mcp.json`

Both representations name the same `genie-readonly` package and resolve to the same plugin-relative `./bin/genie-mcp.exe`. No extra tool, authority path, daemon, paid service, model provider, or network endpoint was added.

Package version is `0.1.1` so the host-compatibility build is distinguishable from the original `0.1.0` delivery.

## Identity-safe UNKNOWN fixture

The package build copies the historical `actual` seed without degrading its two confirmed tasks, then creates a separate synthetic read-only fixture through the existing pinned queue implementation:

- alias: `unknown-fixture`
- run ID: `genie-plugin-unknown-fixture-20261011`
- task ID: `genie-known-unavailable-fixture-20261011`

The synthetic queue contains a valid known task but deliberately has no task ledger/result destination. This produces epistemic unavailability only after run and task membership succeed.

The fixture does **not** reuse the historical run or task identities and therefore does not create same-ID aliasing with `actual`.

The build recorded:

- `SEED_MANIFEST_PASS desktop-plugin-seed-cd77d90644a34eafc2a8 33`
- `UNKNOWN_FIXTURE_PASS genie-plugin-unknown-fixture-20261011 genie-known-unavailable-fixture-20261011`

## Frozen lifecycle result

The actual self-contained Windows executable passed:

`DESKTOP_PLUGIN_FROZEN_PASS_WITH_UNKNOWN`

The frozen MCP test verified:

1. exactly `get_run_status` and `get_task_result` are advertised;
2. `get_run_status(actual)` returns `PASS`;
3. a historical confirmed task returns `CONFIRMED` and preserves `content_role = UNTRUSTED_ACCEPTED_TASK_DATA`;
4. accepted result text is not duplicated into the model-facing warning text;
5. `get_task_result(unknown-fixture, genie-known-unavailable-fixture-20261011)` returns exactly `UNKNOWN / TASK_RESULT_UNAVAILABLE` with no `result_text`;
6. a nonexistent run remains `REJECT / UNKNOWN_RUN`;
7. a nonexistent task remains `REJECT / UNKNOWN_TASK`;
8. state persists unchanged across a second launch;
9. partial and abandoned initialization states still fail closed and preserve bytes;
10. both portable and Codex compatibility manifest shapes are present and exact.

The exact 36-distribution Windows runtime/build acceptance closure passed and `pip check` found no broken requirements. The unchanged historical source-chain preflight also passed and left the five historical SQLite stores byte-identical.

## Delivery identities

- Executable SHA-256: `c45a34d56bb161e195b8b49fa11c5b0cac57e340974d8c7fe02133c20c2828f5`
- Executable bytes: `22132456`
- ZIP SHA-256: `b3945f3b107d178ac99634b12666631191c80359f8456fde2f0a076c83251bbb`
- ZIP bytes: `21836835`
- GitHub Actions artifact ID: `11722468151`

The downloaded artifact was independently SHA-256 checked after retrieval and matched the uploaded digest exactly. ZIP inspection confirmed five top-level package entries/files: portable `plugin.json`, portable `mcp.json`, compatibility `.codex-plugin/plugin.json`, compatibility `.mcp.json`, and `bin/genie-mcp.exe`.

## What remains unverified

This does **not** prove that ChatGPT Desktop will register the plugin on the user's physical machine. The next claim-bearing observation is a new local Desktop Work/Codex session after the source package is updated/refreshed and Desktop restarted.

A successful local test must observe the host launching the local executable and exposing exactly the two read-only tools, then perform PASS / CONFIRMED / UNKNOWN / REJECT checks. If a fresh local Desktop Work/Codex session still exposes zero tools, treat that as evidence of a genuine host-registration defect and collect the local client/process logs rather than modifying Genie authority semantics.

Pass186 remains inherited controlling; this package is NONCLAIM. No promotion, freeze, main merge, paid hosting, remote deployment, mutation tools, model dispatch, A2A, or EXP010 execution is authorized or implied.

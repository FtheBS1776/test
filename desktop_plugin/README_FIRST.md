# Genie local ChatGPT Desktop plugin package — NONCLAIM

Status: **INTERNAL PACKAGE VERIFIED / FIXTURE-BACKED / NOT INSTALLED / NOT CONNECTED**.

Purpose: package the already accepted two-tool read-only Genie MCP surface as a local Windows Desktop plugin with no paid hosting and no system-Python requirement.

Actual plugin installation/connection remains an external user/account action and requires explicit user action. This repository checkpoint does not install or connect anything.

## Design

- Portable Agent Plugins 1.0 `plugin.json` + `mcp.json`.
- One stdio MCP server: `./bin/genie-mcp.exe`.
- The compatible Desktop host owns process start/stop through stdio; the user does not keep a separate HTTP server running.
- The executable packages the existing pinned Genie read-only transport/core subset plus a bounded historical seed state for deterministic integration testing.
- On first fixture-backed launch only, the executable integrity-checks its bundled seed and provisions `${PLUGIN_DATA}/state` atomically.
- Existing `${PLUGIN_DATA}/state` is never replaced on plugin launch/update.
- Partial state or any abandoned `.state.init-*` first-run provisioning fails closed with `PLUGIN_STATE_PARTIAL_PRESERVE`; existing bytes are preserved rather than repaired/reseeded implicitly.
- Package code may be replaced by a future reviewed update; persistent state remains host-managed under `PLUGIN_DATA`.

## Current scope

The packaged MCP surface remains exactly:

- `get_run_status`
- `get_task_result`

The package does not add writes, model dispatch, autonomous continuation, public networking, OAuth, paid hosting, remote authority, production claims, promotion, freeze, main merge, or EXP010 execution.

The bundled historical seed is only a deterministic integration fixture. It is **not** the user's live Genie state, is not a currentness claim, and does not establish continuity with future live state. The fixture-backed package must not be installed or represented as though it were a live Genie integration.

## Internal verification

Accepted tested commit: `edf927d168713942b1ae41a66f7b0de7d691d5bc`
Workflow run/job: `38171548229` / `114565021679`
Environment: Windows Server 2025, exact CPython 3.12.10, isolated venv.

Verified:

- exact 36-distribution Windows runtime/build acceptance set;
- `pip check` clean;
- unfrozen real saved-state PASS/CONFIRMED calls with five SQLite files unchanged;
- deterministic 31-file seed `host-return-trial-b67b52024e8578e9999c`;
- self-contained Windows executable build;
- fixed-stage frozen core self-test;
- real frozen stdio MCP lifecycle (`DESKTOP_PLUGIN_FROZEN_PASS`);
- exact two-tool advertisement;
- PASS and CONFIRMED result behavior;
- `UNTRUSTED_ACCEPTED_TASK_DATA` boundary retained and accepted task text not duplicated into model-facing text;
- persistent state preserved over a second launch;
- partial state and abandoned initialization both reject/preserve.

Ephemeral successful CI executable:
`9a3bc47b2180ffc8ae977376994609d73b3968b4e2cc38bbed92e22b589269d8` / 22,130,908 bytes.

Ephemeral successful CI ZIP:
`833b34fe4a5eaec88b303cce542b08748e81e2852d4753b37e556fb45f659f7f` / 21,834,765 bytes.

The successful workflow intentionally did **not** upload the package. These are ephemeral build identities, not a user-delivery artifact anchor.

See `TEST_RESULTS.txt`, `VERIFICATION.json`, `BUILD_ADOPTION.md`, and `ROOT_ADJUDICATION.md` for evidence and preserved defect history.

## Build policy

PyInstaller is ADAPTed as a build-only dependency. The user does not install it. Build/runtime closure and Python version are pinned in CI; candidate upgrades must pass the same frozen lifecycle before adoption. The executable is unsigned during this NONCLAIM proof and must not be presented as production-trusted software.

Windows is the first packaging target. Cross-platform packaging remains a later portability task and must reuse the same Genie semantics rather than fork the core.

## Next boundary

The next product frontier is **controlled live-state binding/import**. A new NONCLAIM unit must replace fixture fallback as the operational setup path with an explicit, fail-closed binding to live Genie state while preserving exact registry/run/store identities and persistent `PLUGIN_DATA` semantics.

Only after that path is verified should the package be installed/connected in ChatGPT Desktop for a real host-driven read-only tool call. Installation/connection requires explicit user action. Remote/web/mobile access, tunnels, public HTTPS hosting, and public plugin publication remain optional later portability work.

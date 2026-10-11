# Genie local ChatGPT Desktop plugin package — NONCLAIM

Purpose: package the already accepted two-tool read-only Genie MCP surface as a local Windows Desktop plugin with no paid hosting and no system-Python requirement.

This package is **not installed or connected to ChatGPT yet**. Actual plugin installation/connection is an external user action and requires explicit user action after internal package verification.

## Design

- Portable Agent Plugins 1.0 `plugin.json` + `mcp.json`.
- One stdio MCP server: `./bin/genie-mcp.exe`.
- ChatGPT Desktop owns process start/stop through stdio; the user does not keep an HTTP server running.
- The executable packages the existing pinned Genie read-only transport/core subset plus a bounded historical seed state for integration testing.
- On first launch only, the executable integrity-checks its bundled seed and provisions `${PLUGIN_DATA}/state` atomically.
- Existing `${PLUGIN_DATA}/state` is never replaced on plugin launch/update. A partial state without the exact marker fails closed with `PLUGIN_STATE_PARTIAL_PRESERVE`.
- Package code may be replaced by an update; persistent state remains host-managed under `PLUGIN_DATA`.

## Current scope

The packaged MCP surface remains exactly:

- `get_run_status`
- `get_task_result`

The package does not add writes, model dispatch, autonomous continuation, public networking, OAuth, paid hosting, remote authority, production claims, promotion, freeze, main merge, or EXP010 execution.

The bundled historical seed is only a deterministic integration fixture. It is not a currentness claim and does not establish continuity with any future live Genie state.

## Build policy

PyInstaller is ADAPTed as a build-only dependency. The user does not install it. Build versions are pinned and CI must bind the full resolved build dependency closure before package acceptance. The produced executable is unsigned during this NONCLAIM proof; do not present it as production-trusted software.

Windows is the first packaging target because it matches the current user environment. Cross-platform packaging remains a later portability task and must reuse the same Genie semantics rather than fork the core.

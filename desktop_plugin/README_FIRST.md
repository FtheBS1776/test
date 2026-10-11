# Genie local ChatGPT Desktop plugin package — NONCLAIM

Status: **INTERNAL PACKAGE VERIFIED / NOT INSTALLED / NOT CONNECTED**.

Purpose: package the already accepted two-tool read-only Genie MCP surface as a local Windows Desktop plugin with no paid hosting and no system-Python requirement.

Actual plugin installation/connection remains an external user/account action and requires explicit user action. This repository checkpoint does not install or connect anything.

## Design

- Portable Agent Plugins 1.0 `plugin.json` + `mcp.json`.
- One stdio MCP server: `./bin/genie-mcp.exe`.
- The compatible Desktop host owns process start/stop through stdio; the user does not keep a separate HTTP server running.
- The executable packages the existing pinned Genie read-only transport/core subset plus a bounded historical seed state for integration testing.
- On first launch only, the executable integrity-checks its bundled seed and provisions `${PLUGIN_DATA}/state` atomically.
- Existing `${PLUGIN_DATA}/state` is never replaced on plugin launch/update.
- Partial state or any abandoned `.state.init-*` first-run provisioning fails closed with `PLUGIN_STATE_PARTIAL_PRESERVE`; the existing bytes are preserved rather than repaired/reseeded implicitly.
- Package code may be replaced by a future reviewed update; persistent state remains host-managed under `PLUGIN_DATA`.

## Current scope

The packaged MCP surface remains exactly:

- `get_run_status`
- `get_task_result`

The package does not add writes, model dispatch, autonomous continuation, public networking, OAuth, paid hosting, remote authority, production claims, promotion, freeze, main merge, or EXP010 execution.

The bundled historical seed is only a deterministic integration fixture. It is not a currentness claim and does not establish continuity with any future live Genie state.

## Internal verification

Accepted tested commit: `0578b62ea033c69601c0eaef6ab75658c0c8c8df`
Workflow run/job: `38171427730` / `114564670784`
Environment: Windows Server 2025, exact CPython 3.12.10, isolated venv.

Verified:

- exact 36-distribution Windows runtime/build acceptance set;
- `pip check` clean;
- unfrozen real saved-state PASS/CONFIRMED calls with five SQLite files unchanged;
- deterministic 31-file seed `host-return-trial-b67b52024e8578e9999c`;
- self-contained Windows executable build;
- real frozen stdio MCP lifecycle (`DESKTOP_PLUGIN_FROZEN_PASS`);
- exact two-tool advertisement;
- PASS and CONFIRMED result behavior;
- `UNTRUSTED_ACCEPTED_TASK_DATA` boundary retained and accepted task text not duplicated into model-facing text;
- persistent state preserved over a second launch;
- partial state and abandoned initialization both reject/preserve.

Ephemeral successful CI executable:
`1add37f928a70d02c275a133612fa353d17b5d4b338c7a4149c8e8f47e6e0b6b` / 22,122,614 bytes.

Ephemeral successful CI ZIP:
`71c92139425bb530d55132beaa791e6ebf81662f84b99ab225ab5855049c5ca0` / 21,826,678 bytes.

The successful workflow intentionally did **not** upload the package. These are ephemeral build identities, not a user-delivery artifact anchor.

See `TEST_RESULTS.txt`, `VERIFICATION.json`, and `ROOT_ADJUDICATION.md` for the full evidence and preserved defect history.

## Build policy

PyInstaller is ADAPTed as a build-only dependency. The user does not install it. Build/runtime closure and Python version are pinned in CI; candidate upgrades must pass the same frozen lifecycle before adoption. The executable is unsigned during this NONCLAIM proof and must not be presented as production-trusted software.

Windows is the first packaging target because it matches the current environment. Cross-platform packaging remains a later portability task and must reuse the same Genie semantics rather than fork the core.

## Next boundary

The next product frontier is **actual local ChatGPT Desktop installation/connection and a real host-driven read-only tool call**. No further repository engineering is required merely to prove that the package can build and run internally; that proof is complete.

Installation/connection must not be inferred from prior continuation authorization. It requires explicit user action/approval. Remote/web/mobile access, tunnels, public HTTPS hosting, and public plugin publication remain optional later portability work and are not prerequisites for this local package.

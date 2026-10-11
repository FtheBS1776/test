# Root adjudication — Genie local ChatGPT Desktop plugin package

Disposition: **ACCEPT_NONCLAIM_INTERNAL_PACKAGE**

Accepted subject: the internally verified Windows local plugin package built from tested commit `0578b62ea033c69601c0eaef6ab75658c0c8c8df` in workflow run `38171427730`, job `114564670784`.

## Accepted evidence

The evidence supports these narrow conclusions:

- The package was built on Windows Server 2025 with exact CPython 3.12.10 in an isolated venv.
- `pip check` passed and the exact expected Windows runtime/build closure count was 36.
- The unfrozen Windows source chain performed real `get_run_status` and `get_task_result` calls successfully before freezing and left the five saved SQLite stores byte-identical.
- The deterministic historical integration seed contained 31 bound files and verified as `host-return-trial-b67b52024e8578e9999c`.
- The frozen Windows executable was built with PyInstaller 6.22.3 / hooks 2026.8, with the approved dynamic Genie core carried as raw hash-pinned source data.
- The dynamically loaded core's standard-library `sqlite3` dependency was explicitly frozen; this repaired the earlier frozen-only `CORE_FAILURE` without changing Genie semantics or adding a third-party runtime dependency.
- The actual frozen executable passed the full stdio lifecycle test (`DESKTOP_PLUGIN_FROZEN_PASS`).
- The executable advertised exactly `get_run_status` and `get_task_result`.
- A saved run returned `PASS`; a confirmed task returned `CONFIRMED` and retained `UNTRUSTED_ACCEPTED_TASK_DATA`.
- Accepted task text was not duplicated into the model-facing text block; the text block explicitly retained the untrusted-data warning.
- A second launch against the same `PLUGIN_DATA` preserved existing state.
- Partial state and abandoned first-run `.state.init-*` state both failed closed and preserved existing bytes rather than reseeding or repairing them implicitly.
- Agent Plugins packaging is portable root `plugin.json` + `mcp.json`, with a plugin-relative `./bin/genie-mcp.exe` stdio command; no system Python, manually maintained HTTP server, paid hosting, or public ingress is required by this package design.

## Ephemeral build identities

- Executable SHA-256: `1add37f928a70d02c275a133612fa353d17b5d4b338c7a4149c8e8f47e6e0b6b`
- Executable size: `22122614` bytes
- CI ZIP SHA-256: `71c92139425bb530d55132beaa791e6ebf81662f84b99ab225ab5855049c5ca0`
- CI ZIP size: `21826678` bytes

These bind the successful ephemeral CI outputs only. The workflow intentionally printed `PACKAGE_NOT_UPLOADED_NONCLAIM`; no package was uploaded, distributed, installed, or connected. These are not yet user-delivery artifact anchors.

## Preserved defect history

The following failures remain evidence and are not rewritten as success:

1. Broad MCP submodule collection pulled unused optional `mcp.cli` and failed on CLI-only `typer`; the repair narrowed the frozen import surface rather than adding an unnecessary dependency.
2. Windows CRLF checkout changed raw source bytes and tripped `MCP_CONSUMER_SOURCE_BINDING`; the repair enforced LF checkout for Python source via `.gitattributes` without weakening hash verification.
3. Pre-repair frozen head `d2db494f527f1855f16d7e5be401f6545c888461` launched MCP but returned `REJECT / CORE_FAILURE` on the real status call. Its exact spec lacked `sqlite3`; the repaired tested head collected `sqlite3` and passed the frozen lifecycle.
4. Interrupted first-run provisioning replay was identified before package acceptance; abandoned `.state.init-*` now rejects/preserves rather than silently reseeding.

## Authority limits

This disposition does **not** establish:

- actual installation or connection in ChatGPT Desktop;
- behavior on the user's physical machine;
- remote/web/mobile access;
- public distribution or signing trust;
- currentness against whole-store rollback;
- root/bootstrap/custody continuity;
- remote authenticity or hostile-worker isolation;
- production readiness, authority promotion, freeze, main merge, or EXP010 execution.

Pass 186 remains inherited controlling and this package remains NONCLAIM.

## Next authority boundary

The next frontier is a real local ChatGPT Desktop installation/connection followed by representative read-only tool calls. Installing or connecting a plugin is an external user/account action and requires explicit user action/approval. Repository engineering authority does not imply permission to install it.

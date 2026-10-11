# Root adjudication — Genie local ChatGPT Desktop plugin package

Disposition: **ACCEPT_NONCLAIM_INTERNAL_PACKAGE**

Accepted subject: the internally verified Windows local plugin package built from tested commit `edf927d168713942b1ae41a66f7b0de7d691d5bc` in workflow run `38171548229`, job `114565021679`.

## Accepted evidence

The evidence supports these narrow conclusions:

- The package was built on Windows Server 2025 with exact CPython 3.12.10 in an isolated venv.
- `pip check` passed and the exact expected Windows runtime/build closure count was 36.
- The unfrozen Windows source chain performed real `get_run_status` and `get_task_result` calls successfully before freezing and left all five observed SQLite stores byte-identical.
- The deterministic historical integration seed contained 31 bound files and verified as `host-return-trial-b67b52024e8578e9999c`.
- The frozen executable retained the approved dynamic Genie core as raw hash-pinned source data and explicitly included dynamically required standard-library `sqlite3`.
- The fixed-stage frozen build self-test passed without exposing paths, exception text, or accepted result data.
- The actual frozen executable passed the full stdio lifecycle test (`DESKTOP_PLUGIN_FROZEN_PASS`).
- The executable advertised exactly `get_run_status` and `get_task_result`.
- A saved fixture run returned `PASS`; a confirmed task returned `CONFIRMED` and retained `UNTRUSTED_ACCEPTED_TASK_DATA`.
- Accepted task text was not duplicated into the model-facing text block; the text block explicitly retained the untrusted-data warning.
- A second launch against the same `PLUGIN_DATA` preserved existing state.
- Partial state and abandoned first-run `.state.init-*` state both failed closed and preserved existing bytes rather than reseeding or repairing them implicitly.
- The package uses portable Agent Plugins root `plugin.json` + `mcp.json`, with a plugin-relative `./bin/genie-mcp.exe` stdio command; the design requires no system Python, manually maintained HTTP server, paid hosting, or public ingress.

## Ephemeral build identities

- Executable SHA-256: `9a3bc47b2180ffc8ae977376994609d73b3968b4e2cc38bbed92e22b589269d8`
- Executable size: `22130908` bytes
- CI ZIP SHA-256: `833b34fe4a5eaec88b303cce542b08748e81e2852d4753b37e556fb45f659f7f`
- CI ZIP size: `21834765` bytes

These bind the successful ephemeral CI outputs only. The workflow explicitly printed `PACKAGE_NOT_UPLOADED_NONCLAIM`; no package was uploaded, distributed, installed, or connected. These are not user-delivery artifact anchors.

## Preserved defect history

The following failures remain evidence and are not rewritten as success:

1. Broad MCP submodule collection pulled unused optional `mcp.cli` and failed on CLI-only `typer`; the repair narrowed the frozen import surface rather than adding an unnecessary dependency.
2. Windows CRLF checkout changed raw source bytes and tripped `MCP_CONSUMER_SOURCE_BINDING`; the repair enforced LF checkout for Python source via `.gitattributes` without weakening hash verification.
3. A pre-repair frozen executable built and negotiated MCP but returned `REJECT / CORE_FAILURE` on the real status call. The same real calls passed unfrozen on Windows, isolating the fault to packaging. Explicitly collecting dynamically used stdlib `sqlite3` repaired the frozen lifecycle without changing Genie semantics or adding a third-party runtime dependency.
4. Interrupted first-run provisioning replay was identified before package acceptance; abandoned `.state.init-*` now rejects/preserves rather than silently reseeding.
5. The first `.gitattributes` repair did not itself trigger package CI because the workflow path filter omitted `.gitattributes`; source-representation policy is now a test-triggering input.

## Authority limits

This disposition does **not** establish:

- binding to the user's current/live Genie state;
- actual installation or connection in ChatGPT Desktop;
- behavior on the user's physical machine;
- remote/web/mobile access;
- public distribution or signing trust;
- currentness against whole-store rollback;
- root/bootstrap/custody continuity;
- remote authenticity or hostile-worker isolation;
- production readiness, authority promotion, freeze, main merge, or EXP010 execution.

The bundled seed is a historical deterministic integration fixture. A fixture-backed package must not be represented as a live Genie installation.

Pass 186 remains inherited controlling and this package remains NONCLAIM.

## Next authority boundary

The next frontier is **controlled live-state binding/import**, not installation. The package must gain a fail-closed path that binds persistent `PLUGIN_DATA` to explicitly selected live Genie state without silent overwrite, repair, fallback to the historical fixture, or ambiguity about run/store identity. That work may proceed as a separate NONCLAIM implementation branch.

Only after live-state binding is independently verified does a real local ChatGPT Desktop installation/connection followed by representative read-only tool calls become the next external user/account boundary. Installing or connecting the plugin requires explicit user action/approval and is not authorized merely by repository continuation.

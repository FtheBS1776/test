# Genie local ChatGPT Desktop plugin package — NONCLAIM

Status: **v0.1.1 REPLACEMENT CANDIDATE VERIFIED / PHYSICAL DESKTOP RETEST OPEN**.

Purpose: package the accepted two-tool read-only Genie MCP surface as a local Windows Desktop plugin with no paid hosting and no system-Python requirement.

The earlier v0.1.0 package was installed/enabled by the user, but the attempted verification environment exposed zero Genie tools. That observation did not establish a physical-Desktop launch defect because the verification handoff ran through a cloud Work execution surface. The replacement candidate below hardens Desktop/Codex compatibility and adds a truthful UNKNOWN fixture; it is not yet claimed to fix the host issue until a real local Desktop session proves it.

## Package design

The package carries both supported representations of the same plugin:

- portable Agent Plugins: root `plugin.json` + `mcp.json`;
- OpenAI/Codex compatibility fallback: `.codex-plugin/plugin.json` + `.mcp.json`.

Both point to one stdio MCP server: `./bin/genie-mcp.exe`.

The compatible local host owns process start/stop. The user does not maintain a separate HTTP server. The executable packages the existing pinned Genie read-only transport/core subset and deterministic test state. Persistent state remains under host-provided `PLUGIN_DATA`; updates must not silently replace existing state.

Partial state or abandoned `.state.init-*` provisioning fails closed with `PLUGIN_STATE_PARTIAL_PRESERVE`.

## MCP surface

Exactly:

- `get_run_status`
- `get_task_result`

No writes, model dispatch, autonomous continuation, public networking, OAuth, paid hosting, remote authority, production claim, promotion, freeze, main merge, or EXP010 execution is added.

## PASS / CONFIRMED / REJECT / UNKNOWN

The historical alias `actual` remains unchanged and supplies the PASS/CONFIRMED cases.

A separate synthetic test alias `synthetic-unknown` supplies a legitimate epistemic UNKNOWN case. Its copied queue policy is rebound to distinct run ID `genie-plugin-synthetic-unknown-20261011`; its owned result root is deliberately unavailable. This proves known membership with unavailable result evidence without corrupting or reinterpreting `actual` and without using a same-ID alias shortcut.

A nonexistent run remains deterministic `REJECT / UNKNOWN_RUN`; it is not mislabeled UNKNOWN.

See `UNKNOWN_FIXTURE.md`.

## Current internal verification

Accepted replacement-candidate tested commit: `61bf2da663ea260b0b09f544b7d167d31ec55af3`

Workflow run/job: `38194250230` / `114633333562`

Environment: Windows Server 2025, exact CPython 3.12.10, isolated venv.

Verified:

- exact 36-distribution Windows runtime/build set and clean `pip check`;
- unchanged original Windows read-only source chain;
- synthetic queue rebound to its own run ID with SQLite integrity PASS;
- seed `host-return-plus-unknown-b6bb873bf6c854f2dbaa`, 32 files;
- self-contained executable build;
- portable plus Codex-compatible manifest assembly;
- frozen stdio MCP lifecycle PASS;
- exact two-tool advertisement;
- PASS / CONFIRMED / REJECT / UNKNOWN classification boundary;
- `UNTRUSTED_ACCEPTED_TASK_DATA` retained and accepted text not duplicated into model-facing text;
- persistent state preserved across relaunch;
- partial and abandoned initialization fail closed;
- user-delivery artifact upload and independent post-download SHA verification.

Replacement executable:
`885ffc2b6edc6d884127b7aae6883bb524bdcbbdb6ba1f229da612ccd8526f2d` / 22,133,371 bytes.

Replacement ZIP:
`b94b023f618dc9bfc5952482b46d28e66eb38b778ee892b6d788b612536da706` / 21,838,028 bytes.

GitHub Actions artifact ID: `11722996512`.

See `HOST_COMPAT_VERIFICATION.md`, `UNKNOWN_FIXTURE.md`, `TEST_RESULTS.txt`, `VERIFICATION.json`, `BUILD_ADOPTION.md`, and the historical adjudication records.

## Next boundary

The next meaningful gate is a **physical ChatGPT Desktop replacement/update and a brand-new local Work/Codex session**.

The local host must then demonstrate:

1. exactly `get_run_status` and `get_task_result` are registered;
2. `get_run_status({"run_name":"actual"})` returns PASS;
3. `get_task_result` for `genie-work-host-entry-20261010` under `actual` returns CONFIRMED with the untrusted-data boundary intact;
4. a nonexistent run returns REJECT / UNKNOWN_RUN;
5. the known task under `synthetic-unknown` returns UNKNOWN / TASK_RESULT_UNAVAILABLE;
6. ChatGPT Desktop starts/stops the bundled stdio process without a manually maintained server.

Replacing/updating the user's installed local plugin is an external filesystem/application action. Do not claim the host issue is repaired until that real local test passes.

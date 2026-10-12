# Desktop host compatibility verification — NONCLAIM

Disposition: **ACCEPT_NONCLAIM_REPLACEMENT_CANDIDATE**

This record supersedes no historical evidence. It binds a new replacement candidate only.

## Tested subject

- Branch: `nonclaim/genie-desktop-host-compat-unknown-20261011`
- Tested commit: `61bf2da663ea260b0b09f544b7d167d31ec55af3`
- Workflow run: `38194250230`
- Job: `114633333562`
- Plugin version: `0.1.1`

## Compatibility hardening

The package retains the portable Agent Plugins root files:

- `plugin.json`
- `mcp.json`

and adds the currently supported OpenAI/Codex compatibility fallback:

- `.codex-plugin/plugin.json`
- `.mcp.json`

Both representations point to the same plugin-relative stdio executable `./bin/genie-mcp.exe` and expose no additional Genie tool or authority surface.

Current OpenAI documentation used for this boundary:

- `https://developers.openai.com/plugins/build/plugins`
- `https://developers.openai.com/api/docs/guides/agents-api/tools/plugins`

Those documents describe the portable root layout, the supported `.codex-plugin/plugin.json` compatibility fallback, bundled MCP configuration, local marketplaces in ChatGPT Desktop Work/Codex, and the need for a new session after plugin changes.

## Semantic conformance

The frozen package test requires exactly two tools:

- `get_run_status`
- `get_task_result`

It verifies four distinct classifications:

1. `actual` run status -> `PASS`.
2. Confirmed task result -> `CONFIRMED`, retaining `UNTRUSTED_ACCEPTED_TASK_DATA`; accepted result text is not copied into model-facing text.
3. Nonexistent run -> deterministic `REJECT / UNKNOWN_RUN`.
4. Known task in a separately bound synthetic run whose owned result evidence is unavailable -> epistemic `UNKNOWN / TASK_RESULT_UNAVAILABLE`.

The synthetic UNKNOWN case does not mutate or reinterpret `actual`. Its copied queue policy is rebound to the distinct run identity `genie-plugin-synthetic-unknown-20261011` before the registry alias `synthetic-unknown` is created. The synthetic alias deliberately points to an absent owned result root, so membership is known but result evidence cannot be established. See `UNKNOWN_FIXTURE.md`.

## Successful evidence

CI reported:

- `WINDOWS_PACKAGE_VERSION_CLOSURE_PASS 36`
- `WINDOWS_SOURCE_AND_READONLY_CALL_CHAIN_PASS 5 genie-work-host-entry-20261010`
- `SYNTHETIC_UNKNOWN_FIXTURE_PASS genie-plugin-synthetic-unknown-20261011 genie-work-host-entry-20261010`
- `SEED_MANIFEST_PASS host-return-plus-unknown-b6bb873bf6c854f2dbaa 32`
- frozen executable build PASS
- portable + compatibility package assembly PASS
- `DESKTOP_PLUGIN_FROZEN_PASS`
- artifact upload PASS

Package identities:

- EXE SHA-256: `885ffc2b6edc6d884127b7aae6883bb524bdcbbdb6ba1f229da612ccd8526f2d`
- EXE bytes: `22133371`
- ZIP SHA-256: `b94b023f618dc9bfc5952482b46d28e66eb38b778ee892b6d788b612536da706`
- ZIP bytes: `21838028`
- GitHub Actions artifact ID: `11722996512`

The downloaded user-delivery ZIP was independently re-hashed after retrieval and matched the same ZIP SHA-256 exactly.

## Preserved limits

This evidence does **not** prove that ChatGPT Desktop on the user's physical Windows machine registers or launches the replacement package. The prior installed `0.1.0` package was reported enabled but exposed zero Genie tools in the attempted verification environment. That earlier observation remains unresolved because the verification handoff ran through a cloud Work execution surface that cannot establish local-process behavior.

Therefore the next meaningful gate is an explicit replacement/update on the physical ChatGPT Desktop installation followed by a brand-new local Work/Codex session. Success requires real host observation of exactly the two tools and live PASS / CONFIRMED / REJECT / UNKNOWN calls.

No mutation, model dispatch, autonomous continuation, promotion, freeze, main merge, production claim, paid service, or EXP010 execution is authorized by this record.

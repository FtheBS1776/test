# Genie roadmap amendment — Desktop host compatibility — 2026-10-12 UTC

Status: **STANDING NONCLAIM ROADMAP AMENDMENT**

This amendment supplements `ROADMAP.md`. It does not promote, freeze, merge `main`, authorize spending, deploy production infrastructure, or authorize EXP010 execution.

## Why this amendment exists

The original local Windows plugin package v0.1.0 was installed and enabled, but the attempted verification environment exposed zero Genie tools and did not launch `genie-mcp.exe`. That observation is preserved, but it did not establish a physical ChatGPT Desktop host defect because the verification handoff ran through a cloud Work execution surface rather than a local Desktop session capable of spawning the Windows executable.

Current OpenAI plugin documentation distinguishes portable plugin packaging from the supported Codex compatibility overlay and states that local marketplace plugins are exercised in Work mode or Codex in the ChatGPT desktop app. Existing sessions do not reload changed plugin tools; use a new session after plugin changes.

## Replacement candidate v0.1.1

A new isolated NONCLAIM branch was created from the user-delivery v0.1.0 lineage:

`nonclaim/genie-desktop-host-compat-unknown-20261011`

The replacement candidate retains the portable Agent Plugins root layout:

- `plugin.json`
- `mcp.json`

and adds the supported OpenAI/Codex compatibility fallback:

- `.codex-plugin/plugin.json`
- `.mcp.json`

Both representations point to the same plugin-relative stdio executable and expose exactly the same two read-only Genie tools:

- `get_run_status`
- `get_task_result`

No second engine, paid hosting, manual daemon, write surface, model dispatch, autonomous continuation, A2A layer, public ingress, or new authority mechanism is introduced.

## Correct classification gate

The live-read verification contract is now explicitly four-way:

1. Valid saved run `actual` -> `PASS`.
2. Valid confirmed task result -> `CONFIRMED`, retaining `UNTRUSTED_ACCEPTED_TASK_DATA`.
3. Deterministically unrecognized run -> `REJECT / UNKNOWN_RUN`.
4. Known task whose result evidence cannot be established -> `UNKNOWN / TASK_RESULT_UNAVAILABLE`.

A nonexistent run must not be relabeled as epistemic UNKNOWN.

Because both historical tasks in `actual` are currently CONFIRMED, the package adds a separate **synthetic test-only UNKNOWN fixture**. It copies the historical queue, rebinds the copied queue policy to distinct run ID `genie-plugin-synthetic-unknown-20261011`, and points that synthetic alias at a deliberately unavailable owned-result root. It does not modify `actual`, reuse `actual`'s run identity, or establish operational authority.

## Internal verification evidence

Runtime-tested commit:
`61bf2da663ea260b0b09f544b7d167d31ec55af3`

Workflow run/job:
`38194250230` / `114633333562`

Successful gates include:

- exact 36-distribution Windows build/runtime set and clean `pip check`;
- unchanged original PASS/CONFIRMED read-only source chain;
- distinct synthetic run rebinding with SQLite integrity PASS;
- deterministic 32-file seed `host-return-plus-unknown-b6bb873bf6c854f2dbaa`;
- frozen Windows stdio executable build;
- portable + Codex compatibility package assembly;
- `DESKTOP_PLUGIN_FROZEN_PASS` covering PASS / CONFIRMED / REJECT / UNKNOWN;
- persistent-state preservation and fail-closed partial/interrupted provisioning;
- exact uploaded/downloaded package identity.

Replacement package identity:

- EXE SHA-256: `885ffc2b6edc6d884127b7aae6883bb524bdcbbdb6ba1f229da612ccd8526f2d`
- ZIP SHA-256: `b94b023f618dc9bfc5952482b46d28e66eb38b778ee892b6d788b612536da706`
- ZIP bytes: `21838028`
- GitHub Actions artifact ID: `11722996512`

The user-delivery ZIP was downloaded after CI upload and independently re-hashed to the same SHA-256.

## Immediate frontier

The next meaningful gate is **replacement/update on the user's physical ChatGPT Desktop installation**, followed by a **brand-new local Desktop Work/Codex session**.

That real host test must establish:

1. tool registry exposes exactly `get_run_status` and `get_task_result`;
2. `actual` returns PASS;
3. `actual` + `genie-work-host-entry-20261010` returns CONFIRMED and preserves the untrusted-data label;
4. a nonexistent run returns REJECT / UNKNOWN_RUN;
5. `synthetic-unknown` + the known task returns UNKNOWN / TASK_RESULT_UNAVAILABLE;
6. ChatGPT Desktop owns stdio process startup/shutdown without a manually maintained server.

Do not mark the plugin milestone connected or complete until those physical-host observations succeed.

## Preserved governance

- Pass 186 remains inherited controlling.
- This branch and all Desktop integration work remain NONCLAIM.
- `main` must remain untouched absent explicit authority.
- No recurring monetary cost by default.
- No routine user-maintained synchronization.
- No automatic dependency upgrade across semantic boundaries.
- External version changes remain adapter/conformance gated.
- Currentness/whole-store rollback, root/bootstrap/custody, power-loss, remote authenticity, and hostile-worker isolation HOLDs remain scoped.
- A successful read-only Desktop connection does not authorize mutation, model dispatch, autonomous continuation, remote hosting, public publication, promotion, freeze, or EXP010.

See `../desktop_plugin/HOST_COMPAT_VERIFICATION.md`, `../desktop_plugin/ROOT_ADJUDICATION_HOST_COMPAT.md`, and `../desktop_plugin/UNKNOWN_FIXTURE.md` for the bound evidence and exact limits.

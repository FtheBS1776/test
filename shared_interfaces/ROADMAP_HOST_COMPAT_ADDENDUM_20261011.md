# Genie roadmap host-compatibility addendum — 2026-10-11/12 UTC

This addendum is newer than the host-install wording in `ROADMAP.md` and governs the immediate plugin frontier. It does not replace the standing external-integration policy or any Pass186/scoped HOLD authority.

## State now reached

- Original Windows Desktop plugin v0.1.0: internally verified and delivered; installation/enabling was reported by the user.
- First attempted live verification: **invalid for local MCP**, because it ran in a cloud-hosted Work environment and observed no local tools/process. Do not use that attempt as evidence that the Windows package itself was defective.
- Host-compatibility package v0.1.1: **ACCEPT_NONCLAIM_HOST_COMPAT_PACKAGE** at tested commit `a98d11782443a1084518a910d1b4196c07974ea9`, workflow `38194737754`, job `114634801711`.
- v0.1.1 retains portable root `plugin.json` + `mcp.json` and adds the currently supported Codex compatibility fallback `.codex-plugin/plugin.json` + `.mcp.json` over the same executable.
- v0.1.1 adds a separate synthetic, identity-safe known-but-unavailable fixture so literal `UNKNOWN / TASK_RESULT_UNAVAILABLE` can be tested without degrading historical confirmed state.
- Frozen v0.1.1 lifecycle: `DESKTOP_PLUGIN_FROZEN_PASS_WITH_UNKNOWN`.
- Delivery ZIP SHA-256: `b3945f3b107d178ac99634b12666631191c80359f8456fde2f0a076c83251bbb`.

## Correct live verification matrix

A fresh **local ChatGPT Desktop Work/Codex** session must verify:

1. tool registry exposes exactly `get_run_status` and `get_task_result`;
2. `get_run_status` for alias `actual` -> `PASS`;
3. `get_task_result` for a confirmed `actual` task -> `CONFIRMED` with `UNTRUSTED_ACCEPTED_TASK_DATA` preserved;
4. `get_task_result` for alias `unknown-fixture`, task `genie-known-unavailable-fixture-20261011` -> `UNKNOWN / TASK_RESULT_UNAVAILABLE` with no result text;
5. nonexistent run -> `REJECT / UNKNOWN_RUN`;
6. nonexistent task -> `REJECT / UNKNOWN_TASK`;
7. Desktop owns stdio process start/stop; no separate manually maintained server is required.

The old proposed matrix that expected literal UNKNOWN from a nonexistent run was wrong and is superseded. Invalid identity is deterministic REJECT, not epistemic UNKNOWN.

## If local registration still fails

If a fresh local Desktop Work/Codex session using v0.1.1 still exposes zero Genie tools and never starts `genie-mcp.exe`, classify that as a genuine host-registration frontier. Collect local client/tool/process logs and inspect cache/marketplace loading before changing Genie core semantics.

Do not weaken source pins, UNKNOWN semantics, identity binding, or authority boundaries to accommodate a host loader failure.

## Still deferred / prohibited by this addendum

No mutation tools, model dispatch, autonomous continuation, A2A, remote hosting, tunnel/public HTTPS requirement, higher paid plan requirement, main merge, promotion, freeze, production claim, or EXP010 execution is authorized by this work.

Pass186 remains inherited controlling; all plugin integration remains NONCLAIM.

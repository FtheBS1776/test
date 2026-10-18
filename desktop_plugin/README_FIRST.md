# Genie local Windows live-state plugin candidate — NONCLAIM

The current operational entry reuses the live-state source from `fa4e291cfd1aa7147f39f359008f8d74a2f69798`, with package imports and the maintained shared MCP stdio runner. Read the root README for the one current source-candidate correspondence and `REPAIR_TEST_RESULTS.txt` for exact checks and limits.

The plugin reads the fixed OS-selected `FOLDERID_LocalAppData/GenieReasoningEngine/state-v1` root created by the existing standalone owner. It does not create/copy/migrate/repair state and cannot fall back to bundled seed or `PLUGIN_DATA`. Missing/invalid state rejects with a fixed code. The same two read-only tools expose diagnostics and accepted data; they do not authorize new work or model calls. Standalone creation remains `python -m standalone_app.cli create`, with its existing policy, cost and one-shot preservation rules.

The package retains portable and Codex-compatible manifest forms, source version 0.2.0. A no-model hosted build/test is not installation or compatibility on the user's machine. No model key, paid hosting, server deployment, promotion or governance freeze is introduced. Installation/connection still requires explicit user action; this candidate performs neither.

The former fixture-backed entry and its repaired bootstrap tests are preserved exactly in commit `c1c0a396881c798cd7503135e8958128c93febca` and the v3 source ZIP. They are superseded for operation, not silently relabeled as live-state evidence. Current tests reject a convincing old cache when live state is missing and check the whole fresh-owner/driver/compiled-plugin route on a disposable hosted Windows account. The plugin has no arbitrary root override; the compiled harness refuses a pre-existing app namespace and is CI-only.

## Actual host boundary — documentation checked 2026-10-18 UTC

This package is a local Windows stdio process, not a remotely hosted connector. [Official desktop-only plugin guidance](https://developers.openai.com/plugins/deploy/desktop-only) requires local execution and a locally running desktop thread. [Current plugin guidance](https://learn.chatgpt.com/docs/plugins) says desktop-only plugins are unavailable on mobile. [MCP guidance](https://learn.chatgpt.com/docs/extend/mcp) documents local desktop configuration and warns that local transports may be unavailable to a cloud coordinator. These are product prerequisites, not evidence of this package working on a particular account or machine.

The next compatibility observation must identify the actual Windows host/client version, exact reviewed package/config bytes, local execution/connection and the advertised two read-only tools. Preserve missing/invalid canonical-state rejection; do not seed a fixture, provision a replacement or use a root override to make a connection appear successful. This chat has no native user-computer access and exposes no Genie MCP tool. Hosted VM/SDK passes do not supply those missing observations. No installation, connection, binary publication, account change or remote hosting was performed here. This read-only plugin lane is separate from R13 model dispatch through the existing active host.

## Reported actual-host inventory — 2026-10-18

A user-pasted read-only inventory reports Windows 11 Home 23H2 (NT 10.0.22631.6199), ChatGPT Desktop 26.1013.40934/build20770, OpenAI.Codex package 26.1013.4894.0, enabled stdio registration and exactly the two Genie tool names visible. Its executable SHA256 `c45a34d56bb161e195b8b49fa11c5b0cac57e340974d8c7fe02133c20c2828f5` exactly matches the preserved v0.1.1 delivery in `HOST_COMPAT_VERIFICATION_20261011.md`. Case normalization changes digest notation only.

This narrows reported host identity/tool visibility for the historical fixture-backed package. It does not validate the repaired v0.2.0 live-state candidate on that machine. No Genie tool was invoked in the reported inventory; current data and effective runtime cwd remain unverified. A subsequent user-reported readiness inventory matches the four named manifest hashes in `BUILD_REPRODUCIBILITY_NOTE_20261011.md`, reports no explicit registration cwd, absent canonical `state-v1`/`.state-v1.init` and an existing legacy cache. It does not inventory extra package files or establish authoritative currentness. The normalized follow-up is `repair_validation/HOST_UPGRADE_READINESS_20261018.json`. Keep the installed binary/cache unchanged; do not relabel historical fixture results as live state. The normalized inventory and exact comparison are in `repair_validation/HOST_INVENTORY_COMPARISON_20261018.json`. User-specific profile paths are redacted in that record; the chat retains the original report. This is trusted-host/user-reported evidence, not signed or independent attestation.

The next isolated preparation is specified in [HOST_STAGE_PLAN_20261018.md](HOST_STAGE_PLAN_20261018.md): use an existing exact build runtime, preserve the old installation/cache, build into a new project stage, then make one gated missing-root rejection probe. Missing prerequisites stop without global installation. This is preparation only; no current laptop build/probe result, package activation or canonical-state creation is established. Static review records and the first review's corrected findings are retained under `repair_validation/host_stage_plan_review_v1` and `repair_validation/host_stage_plan_review_v2`.

The subsequent user-reported attempt created the exclusive stage, then stopped at `BLOCKED_TASK_LOCAL_ENVIRONMENT` because `PYTHONHOME` and `PYTHONPATH` remained visible after attempted removal. No clone, build or probe was reached. The original plan remains unchanged; do not resume or clean the occupied stage. The removal/check commands, shell version and process boundary are not supplied here, so the cause remains undetermined. The report also records one Firecrawl retrieval credit consumed; included allowance and monetary charge are UNKNOWN. See `repair_validation/HOST_TASK_ENVIRONMENT_BLOCKER_20261018.json` and [the read-only evidence request](HOST_ENVIRONMENT_EVIDENCE_REQUEST_20261018.md). No further credit-consuming retrieval is part of that request.

The subsequent four-file inspection reportedly records PowerShell `7.6.5` and the same PID for startup/checker, while exact internal cleanup/check expressions and empty versus nonempty entries remain UNKNOWN. The original blocker record is preserved; the narrower follow-up is `repair_validation/HOST_TASK_ENVIRONMENT_FOLLOWUP_20261018.json`. Next inspect the two named `ops` scripts as text only using the follow-up section of the existing evidence request. No cleanup retry or occupied-stage resume follows from a shared PID.

## Historical fixture-backed package record (superseded)

The following record describes its original source/binary, not the current live-state candidate.

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

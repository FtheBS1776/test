# Approved Genie shared-core roadmap — 2026-10-10 UTC

User-approved architecture: one model-agnostic Genie core, accessible through a standalone app and a usable plugin. Both interfaces reuse the same reasoning, saved state, worker/reviewer roles, adjudication and bounded execution contracts. Do not create two engines or let an interface grant authority the core does not have. One LLM remains useful; additional providers are optional; common-cause/shared-model ancestry remains explicit.

| Milestone | Current state | Exit criterion |
|---|---|---|
| Useful governed work in current Work environment | Existing bounded runner and useful tasks completed | Continue concrete eligible tasks with review, fresh delivery and original budget/STOP limits |
| Shared interface foundation | Read-only callable tools, MCP consumer projection, host-spawned stdio, loopback Streamable HTTP, and internally verified Windows Desktop package complete | Preserve one-core semantics while moving from internal package proof to an actual host connection; no added paid hosting or manual server prerequisite |
| Standalone application | Eventual target; not implemented | Run without this particular chat, with user start/pause/resume and suitable model integration; freely runnable host, paid services optional and never required by default |
| Usable plugin | Internal local Windows Desktop package VERIFIED; installation/connection OPEN | With explicit user action, install/connect the local package in ChatGPT Desktop and verify the exact two read-only tools plus representative PASS/CONFIRMED/UNKNOWN behavior |
| Backend hosting and public availability | DEFERRED by user | Select deployment/hosting only when needed and separately authorized; no funded free public compute guarantee |

Near-term interface work can reuse existing diagnostics without selecting a paid hosting platform, model backend, higher subscription tier, or second engine. A plugin request and a standalone request must retain the same meaning at the common core. Adding a plugin does not keep a terminated chat running or authorize unbounded successors.

## External integration and compatibility amendment — 2026-10-11

The standing policy is [EXTERNAL_INTEGRATION_POLICY.md](EXTERNAL_INTEGRATION_POLICY.md). It is a roadmap constraint, not a new authority dependency.

Hard requirements:

1. **No added recurring cost by default.** Prefer free/open/local/already-included capabilities. Paid APIs, subscriptions, hosted services, metered infrastructure, or additional paid model providers remain DEFERRED unless the user explicitly authorizes spending. External adoption should reduce total cost, burden, or risk rather than add them.
2. **No routine user-maintained synchronization.** Genie should own adapter compatibility, validation, migrations, capability checks, and state translation wherever practical. Do not design a system that requires the user to keep external dashboards, policies, versions, or state manually synchronized.
3. **No silent semantic drift from external upgrades.** External systems are isolated behind adapters. Pin or negotiate supported versions/capabilities where possible; test candidate upgrades against existing Genie contracts before adoption. Unsupported or incompatible versions fail closed or remain unavailable without corrupting authoritative state.
4. **Reference architectures are lessons first, dependencies only by exception.** For materially overlapping mature systems, record `REUSE`, `ADAPT`, `REJECT`, or `DEFER` before adding machinery. Studying Cedar/OPA, in-toto/SLSA, TUF, Tessera/Sigstore, Temporal/LangGraph, SPIFFE, OpenTelemetry, MCP, or A2A does not authorize installing them.
5. **Interoperability remains layered around one core.** MCP is the current tool/plugin boundary. A2A or a bounded agent adapter is a later agent-interoperability boundary. Neither transport may grant authority the Genie core does not already authorize.
6. **Observation is not authority.** Future metrics/traces may measure cost, latency, interventions, model calls, failures, and completion, but those records remain non-authoritative unless separately bound and verified by existing Genie authority rules.
7. **Currentness remains a scoped HOLD.** Local hashes, counters, signatures, append-only files, or historical receipts alone do not prove currentness against whole-store rollback. Any future stronger claim requires an anchor outside the rollback domain or an independently maintained witness/trust source.

## MCP local transports COMPLETE — 2026-10-11 UTC

The accepted read-only MCP consumer is composed into two tested local transports on the isolated NONCLAIM lineage:

- **host-spawned stdio**, intended for a local Desktop host that owns process startup/shutdown;
- **loopback Streamable HTTP** at `/mcp`, retained for conformance and future portability.

The official Python MCP SDK is ADAPTed only as a replaceable transport dependency. The original platform-neutral 28-distribution transport closure is pinned and runtime-checked; dependency-version mismatch or consumer-source mismatch fails closed before server construction.

The first real HTTP probe exposed an implementation defect: the low-level MCP `Server` does not accept the high-level `.run(transport=...)` interface. That failure was preserved. The server was repaired to use `streamable_http_app()` under the pinned ASGI runner. The same evidence pass also exposed that pinning only the top-level `mcp` package allowed transitive dependency drift, so the transport closure was locked rather than relying on the resolver. A later test-harness pipe warning was repaired. The host-spawned stdio path was then added over the same accepted handlers.

Final clean transport CI at tested commit `52b72cff246f9e1fe92eea694a9f9afce93ca109` reported `MCP_TRANSPORT_VERSION_CLOSURE_PASS 28`, `pip check` clean, and 8/8 tests PASS. The evidence includes a real stdio subprocess/client call and a separate real loopback Streamable HTTP call against the saved `actual` run; discovered SQLite files were byte-identical before/after both bounded probes. See `../plugin_mcp_server/README_FIRST.md`, `TEST_RESULTS.txt`, `VERIFICATION.json`, and `ROOT_ADJUDICATION.md`.

## Local Windows Desktop package INTERNALLY VERIFIED — 2026-10-11 UTC

The accepted stdio surface is now packaged as a self-contained local Windows Agent Plugins package with portable root `plugin.json` + `mcp.json` and a plugin-relative `./bin/genie-mcp.exe`. The design requires no system Python, paid hosting, public ingress, or manually maintained HTTP server. The host is intended to own process lifetime over stdio; persistent package state is isolated under client-managed `PLUGIN_DATA` so replaceable package code does not silently replace state.

Build-only PyInstaller was separately evaluated under the external-component adoption gate and accepted as `ADAPT (build-time only)`. The user does not install it. The accepted internal package build used exact CPython `3.12.10` on Windows Server 2025 in an isolated virtual environment. The reviewed combined Windows runtime/build acceptance set contained 36 distributions and passed `pip check`.

The packaging lane preserved and repaired several concrete defects rather than erasing them:

- broad MCP submodule collection pulled unused optional `mcp.cli`; the repair narrowed the frozen import surface instead of adding the CLI-only `typer` dependency;
- Windows CRLF checkout changed raw pinned source bytes; the repair preserves LF Python source bytes through `.gitattributes` rather than weakening SHA-256 verification;
- a pre-repair frozen executable launched MCP but returned `REJECT / CORE_FAILURE`; the exact failed freezer omitted standard-library `sqlite3`, which was used only by dynamically loaded hash-pinned core source. The repair explicitly freezes `sqlite3` without changing Genie semantics or adding a third-party runtime dependency;
- interrupted first-run provisioning was identified as a replay/continuity seam; abandoned `.state.init-*` now fails closed and preserves bytes instead of silently reseeding.

Final accepted internal package evidence is bound to tested commit `0578b62ea033c69601c0eaef6ab75658c0c8c8df`, workflow run `38171427730`, job `114564670784`. The run completed successfully and reported:

- `WINDOWS_PACKAGE_VERSION_CLOSURE_PASS 36`;
- `WINDOWS_SOURCE_AND_READONLY_CALL_CHAIN_PASS 5 genie-work-host-entry-20261010`;
- `SEED_MANIFEST_PASS host-return-trial-b67b52024e8578e9999c 31`;
- frozen build success with explicit `sqlite3` collection;
- `DESKTOP_PLUGIN_FROZEN_PASS`.

The frozen lifecycle verified exactly `get_run_status` and `get_task_result`, saved-run `PASS`, confirmed-result `CONFIRMED`, retained `UNTRUSTED_ACCEPTED_TASK_DATA`, no duplication of accepted result text into model-facing text, state preservation across a second launch, fail-closed partial-state preservation, and fail-closed abandoned-provisioning preservation.

Ephemeral successful CI executable identity: `1add37f928a70d02c275a133612fa353d17b5d4b338c7a4149c8e8f47e6e0b6b`, 22,122,614 bytes. Ephemeral CI ZIP identity: `71c92139425bb530d55132beaa791e6ebf81662f84b99ab225ab5855049c5ca0`, 21,826,678 bytes. The workflow explicitly recorded `PACKAGE_NOT_UPLOADED_NONCLAIM`; these identities bind ephemeral build outputs only and are not yet user-delivery anchors.

See `../desktop_plugin/README_FIRST.md`, `TEST_RESULTS.txt`, `VERIFICATION.json`, `ROOT_ADJUDICATION.md`, and `BUILD_ADOPTION.md`.

## Immediate frontier — actual local ChatGPT Desktop connection

Internal package engineering is complete for the current read-only proof. The next meaningful product step is no longer another simulated transport or freezer experiment. It is a **real local ChatGPT Desktop installation/connection**, followed by verification that the host can start/stop the packaged stdio process and call exactly the two accepted read-only tools.

This is an external user/account action. Prior `⏩` continuation authority does not itself authorize installing or connecting a plugin. Explicit user action/approval is required before crossing this boundary.

After installation, the first connected verification should remain narrow:

- enumerate exactly `get_run_status` and `get_task_result`;
- perform a representative `PASS` status read;
- perform a representative `CONFIRMED` task-result read while preserving the untrusted-data label;
- exercise an `UNKNOWN`/unavailable case without automatic replay or new authority;
- confirm the host manages plugin process lifetime without requiring the user to keep a separate server running;
- record any host/version/package facts needed for future compatibility checks.

Do **not** expand to mutation, model dispatch, autonomous continuation, A2A, remote hosting, tunnels, public HTTPS, or public plugin publication merely because the read-only package connects successfully. Each materially new semantic surface remains separately scoped and reviewed.

Remote/web/mobile connectivity is a later optional portability frontier. Secure MCP Tunnel, a public HTTPS endpoint, ChatGPT Sites, or another hosted path must not become a prerequisite for the local plugin and remain DEFERRED unless needed, compatible with existing access, and compliant with the cost/maintenance policy.

Prior progress preserved: operator README7c7625273156fd80b3eb1465137245f3ab2e4915; host clarification3d727e500c5c185c717e17c49e1bd8c3b8d9a91c; freely runnable standalone directiond534881c0ce1bdf3090374b8ddb0adb321adc31e. No completed experiments rerun. Pass186 remains inherited controlling; all later integration NONCLAIM. Root/custody/rollback/power-loss/remote-authenticity/hostile-isolation HOLDs remain scoped. No promotion, freeze, main merge, spending, production deployment or EXP010.

Persistence: both canonical Library files were freshly observed version11; original timeout remains uncertain, no retry/alternate Library write. Newer local canonical working text is retained. This Git roadmap addendum records newer engineering state; it is not a replacement receipt or claim that canonical Library versions advanced.

Current narrow implementation: status_tool.py delegates get_run_status to the unchanged pinned diagnostic. One author/one exact-source static reviewer,0 repairs;12 focused root checks, actual completed-run output correspondence and unchanged prior stores. One governed author reservation/call/observation/application, fresh subprocessCONFIRMED, STOP ALL_TASKS_COMPLETE. No UI, backend hosting, external authentication or after-host autonomy implemented. Original pre-dispatch roadmap bytes preserved as ROADMAP.input.md. Writes/dispatch through a plugin need their own scoped review, not an automatic extension of this read-only tool.

Accepted-result retrieval extension COMPLETE (2026-10-10 UTC): get_task_result now joins get_run_status in the same callable class. Only fresh exact owned-destination CONFIRMED releases accepted text, labelled UNTRUSTED_ACCEPTED_TASK_DATA; task/plan/attempt/request/reservation-slot bindings and existing acceptance validation are checked first. UNKNOWN/MISMATCH/unavailable outcomes withhold text. Candidate SHA37629d2ec2d8bdb88da66247c7093225e387b4d79220fb42b214cc01c8ef2619,11637bytes. One author, one exact-source reviewer and separate root adjudication;0 repairs;26 focused checks plus3 distinct supplementary checks passed. One author reservation/call/observation/application, fresh delivered resultCONFIRMED,STOP ALL_TASKS_COMPLETE.79 earlier stores and12 core source pins unchanged. Original constructor/loader/status descriptor and output preserved; earlier status source/docs saved in result_interface. Separate store snapshots remain non-atomic; valid whole-store copies do not establish custody/rollback continuity. This is a local callable component, not an installed plugin, remote server or always-on model dispatch. Backend remains DEFERRED; no deployment/spending/promotion/freeze/main merge/EXP010; Pass186 and scoped HOLDs unchanged. See ../result_interface/README_FIRST.md and SOURCE_MANIFEST.json for current extension, evidence and limits. Historical shared_interfaces/SOURCE_MANIFEST.json describes the parent status unit, not amended current files.

ChatGPT MCP consumer projection COMPLETE (2026-10-11 UTC): `mcp_consumer.py` pins and reuses the accepted local function adapter, projects exactly `get_run_status`/`get_task_result` into MCP-compatible read-only descriptors and returns complete adapter dictionaries as `structuredContent`. One first-pass semantic defect (invalid caller JSON reported UNKNOWN) was repaired so deterministic invalid input is REJECT while malformed/uncorrelated adapter outcomes remain UNKNOWN. Eleven focused checks and four saved read-only correspondence cases pass;27 SQLite files unchanged. No server/hosting/authentication/plugin connection or model call was added at that stage. See `../plugin_mcp_consumer/README_FIRST.md`.

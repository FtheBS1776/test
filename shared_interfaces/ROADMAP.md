# Approved Genie shared-core roadmap — 2026-10-10 UTC

User-approved architecture: one model-agnostic Genie core, accessible through a standalone app and a usable plugin. Both interfaces reuse the same reasoning, saved state, worker/reviewer roles, adjudication and bounded execution contracts. Do not create two engines or let an interface grant authority the core does not have. One LLM remains useful; additional providers are optional; common-cause/shared-model ancestry remains explicit.

| Milestone | Current state | Exit criterion |
|---|---|---|
| Useful governed work in current Work environment | Existing bounded runner and useful tasks completed | Continue concrete eligible tasks with review, fresh delivery and original budget/STOP limits |
| Shared interface foundation | Read-only callable tools, MCP consumer projection, host-spawned stdio, and loopback Streamable HTTP complete; local Desktop packaging OPEN | Package the accepted stdio surface as a local ChatGPT Desktop plugin and verify host-managed launch without changing Genie semantics |
| Standalone application | Eventual target; not implemented | Run without this particular chat, with user start/pause/resume and suitable model integration; freely runnable host, paid services optional and never required by default |
| Usable plugin | Local MCP transports complete; Desktop plugin package/installation not yet complete | Verify the two read-only tools through a local Desktop plugin, with the host starting/stopping Genie; preserve authority/untrusted-data boundaries and require no paid hosting |
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

The accepted read-only MCP consumer is now composed into two tested local transports on the isolated NONCLAIM branch:

- **host-spawned stdio**, intended for a local Desktop host that owns process startup/shutdown;
- **loopback Streamable HTTP** at `/mcp`, retained for conformance and future portability.

The official Python MCP SDK is ADAPTed only as a replaceable transport dependency. The complete observed 28-distribution transport closure is pinned and runtime-checked; dependency-version mismatch or consumer-source mismatch fails closed before server construction.

The first real HTTP probe exposed an implementation defect: the low-level MCP `Server` does not accept the high-level `.run(transport=...)` interface. That failure was preserved. The server was repaired to use `streamable_http_app()` under the pinned ASGI runner. The same evidence pass also exposed that pinning only the top-level `mcp` package allowed transitive dependency drift, so the transport closure was locked rather than relying on the resolver. A later test-harness pipe warning was repaired. The host-spawned stdio path was then added over the same accepted handlers.

Final clean CI at tested commit `52b72cff246f9e1fe92eea694a9f9afce93ca109` reports `MCP_TRANSPORT_VERSION_CLOSURE_PASS 28`, `pip check` clean, and 8/8 tests PASS. The evidence includes a real stdio subprocess/client call and a separate real loopback Streamable HTTP call against the saved `actual` run; discovered SQLite files were byte-identical before/after both bounded probes. See `../plugin_mcp_server/README_FIRST.md`, `TEST_RESULTS.txt`, `VERIFICATION.json`, and `ROOT_ADJUDICATION.md`.

This proves the bounded local transports, not an installed/connected ChatGPT plugin. No paid hosting, public ingress, model dispatch, authentication system, public submission, main merge, promotion, freeze, or EXP010 execution was added.

## Immediate frontier — zero-hosting local Desktop plugin

The preferred next product step is to package the accepted **stdio** transport as a local ChatGPT Desktop plugin so the host launches and stops Genie itself. This route is preferred because it avoids paid hosting, public ingress, a manually maintained server, and an architectural requirement to upgrade the user's ChatGPT plan.

Package/installation design must preserve the external-integration policy:

- no recurring monetary cost;
- no routine manual dependency/version synchronization;
- no automatic semantic upgrades;
- same exact two read-only tools and complete structured results;
- same explicit UNKNOWN and untrusted-result boundaries;
- no new authority granted by plugin manifests or host metadata.

Remote/web/mobile connectivity is a later optional portability frontier. Secure MCP Tunnel, a public HTTPS endpoint, ChatGPT Sites, or another hosted path must not become a prerequisite for the local plugin and remain DEFERRED unless they are needed, compatible with the user's existing access, and satisfy the cost/maintenance policy.

Preparing and testing the local plugin package is authorized NONCLAIM engineering work. Actual plugin installation/connection is an external user action and requires explicit user action; repository state alone does not authorize it. After installation, verify exactly the two read-only tools and representative PASS/CONFIRMED/UNKNOWN behavior before expanding the plugin surface.

Prior progress preserved: operator README7c7625273156fd80b3eb1465137245f3ab2e4915; host clarification3d727e500c5c185c717e17c49e1bd8c3b8d9a91c; freely runnable standalone directiond534881c0ce1bdf3090374b8ddb0adb321adc31e. No completed experiments rerun. Pass186 remains inherited controlling; all later integration NONCLAIM. Root/custody/rollback/power-loss/remote-authenticity/hostile-isolation HOLDs remain scoped. No promotion, freeze, main merge, spending, production deployment or EXP010.

Persistence: both canonical Library files were freshly observed version11; original timeout remains uncertain, no retry/alternate Library write. Newer local canonical working text is retained. This Git roadmap addendum records the newly approved architecture; it is not a replacement receipt or claim that canonical Library versions advanced.

Current narrow implementation: status_tool.py delegates get_run_status to the unchanged pinned diagnostic. One author/one exact-source static reviewer,0 repairs;12 focused root checks, actual completed-run output correspondence and unchanged prior stores. One governed author reservation/call/observation/application, fresh subprocessCONFIRMED, STOP ALL_TASKS_COMPLETE. No UI, backend hosting, external authentication or after-host autonomy implemented. Original pre-dispatch roadmap bytes preserved as ROADMAP.input.md. Next eligible interface work must serve a concrete approved operation; writes/dispatch through a plugin need their own scoped review, not an automatic extension of this read-only tool.

Accepted-result retrieval extension COMPLETE (2026-10-10 UTC): get_task_result now joins get_run_status in the same callable class. Only fresh exact owned-destination CONFIRMED releases accepted text, labelled UNTRUSTED_ACCEPTED_TASK_DATA; task/plan/attempt/request/reservation-slot bindings and existing acceptance validation are checked first. UNKNOWN/MISMATCH/unavailable outcomes withhold text. Candidate SHA37629d2ec2d8bdb88da66247c7093225e387b4d79220fb42b214cc01c8ef2619,11637bytes. One author, one exact-source reviewer and separate root adjudication;0 repairs;26 focused checks plus3 distinct supplementary checks passed. One author reservation/call/observation/application, fresh delivered resultCONFIRMED,STOP ALL_TASKS_COMPLETE.79 earlier stores and12 core source pins unchanged. Original constructor/loader/status descriptor and output preserved; earlier status source/docs saved in result_interface. Separate store snapshots remain non-atomic; valid whole-store copies do not establish custody/rollback continuity. This is a local callable component, not an installed plugin, remote server or always-on model dispatch. Backend remains DEFERRED; no deployment/spending/promotion/freeze/main merge/EXP010; Pass186 and scoped HOLDs unchanged. See ../result_interface/README_FIRST.md and SOURCE_MANIFEST.json for current extension, evidence and limits. Historical shared_interfaces/SOURCE_MANIFEST.json describes the parent status unit, not amended current files.

ChatGPT MCP consumer projection COMPLETE (2026-10-11 UTC): `mcp_consumer.py` pins and reuses the accepted local function adapter, projects exactly `get_run_status`/`get_task_result` into MCP-compatible read-only descriptors and returns complete adapter dictionaries as `structuredContent`. One first-pass semantic defect (invalid caller JSON reported UNKNOWN) was repaired so deterministic invalid input is REJECT while malformed/uncorrelated adapter outcomes remain UNKNOWN. Eleven focused checks and four saved read-only correspondence cases pass;27 SQLite files unchanged. No server/hosting/authentication/plugin connection or model call was added at that stage. See `../plugin_mcp_consumer/README_FIRST.md`.

# Root adjudication — Genie read-only MCP local transports

Disposition: **ACCEPT_NONCLAIM_TRANSPORT**

Accepted subject: the bounded local MCP transport unit at tested commit `52b72cff246f9e1fe92eea694a9f9afce93ca109`, covering both host-spawned stdio and loopback Streamable HTTP, together with the exact 28-distribution transport dependency closure and the already accepted MCP consumer projection.

Evidence supports the following narrow conclusions:

- The official MCP transport dependency closure installed consistently and passed `pip check`.
- The runtime rejects dependency-version drift and consumer-source mismatch before constructing the server.
- Exactly the accepted `get_run_status` and `get_task_result` tool surfaces are exposed.
- Tool schemas/annotations and complete structured results survive both tested MCP transports.
- `result_text` is not duplicated into model-facing text and remains explicitly untrusted data.
- Malformed transport-side projections fail to explicit UNKNOWN without automatic retry.
- A real host-spawned stdio MCP client/server probe against saved Genie state passed and left SQLite stores byte-identical.
- A separate real loopback Streamable HTTP client/server probe against the same saved state passed and left SQLite stores byte-identical.
- The initial HTTP-launch defect and later test-hygiene warning were preserved, repaired, and superseded by clean passing evidence rather than erased.

This adjudication does **not** establish an installed/connected ChatGPT plugin, public availability, authentication correctness, remote authenticity, currentness/rollback resistance, hostile isolation, production readiness, autonomy, promotion, freeze, main merge, or EXP010 execution.

The external-integration policy remains controlling: no paid hosting is selected; the MCP SDK is an ADAPTed replaceable transport dependency, not a Genie authority dependency; newer dependency versions require compatibility review before adoption.

Next frontier: package the accepted stdio transport as a local ChatGPT Desktop plugin so the host can start/stop Genie itself without requiring the user to keep a separate server running. This route is preferred over paid hosting, public ingress, or a higher-plan-only custom-MCP path. Remote/web/mobile connectivity remains an optional later portability frontier. Actual plugin installation/connection is an external user-account action and requires explicit user action; preparing and verifying the package does not.

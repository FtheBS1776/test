# Root adjudication — Genie read-only MCP server transport

Disposition: **ACCEPT_NONCLAIM_TRANSPORT**

Accepted subject: the bounded local Streamable HTTP MCP transport at tested commit `46fea87747e2a544e5888a37cfd0fbbae483d298`, together with the exact 28-distribution transport dependency closure and the already accepted MCP consumer projection.

Evidence supports the following narrow conclusions:

- The official MCP transport dependency closure installed consistently and passed `pip check`.
- The runtime rejects dependency-version drift and consumer-source mismatch before constructing the server.
- Exactly the accepted `get_run_status` and `get_task_result` tool surfaces are exposed.
- Tool schemas/annotations and complete structured results survive the MCP boundary.
- `result_text` is not duplicated into model-facing text and remains explicitly untrusted data.
- Malformed transport-side projections fail to explicit UNKNOWN without automatic retry.
- An actual Streamable HTTP client/server probe against saved Genie state passed and left SQLite stores byte-identical.
- The initial HTTP-launch defect and later test-hygiene warning were preserved, repaired, and superseded by a clean passing run rather than erased.

This adjudication does **not** establish a ChatGPT plugin connection, public availability, authentication correctness, remote authenticity, currentness/rollback resistance, hostile isolation, production readiness, autonomy, promotion, freeze, main merge, or EXP010 execution.

The external-integration policy remains controlling: no paid hosting is selected; the MCP SDK is an ADAPTed replaceable transport dependency, not a Genie authority dependency; newer dependency versions require compatibility review before adoption.

Next frontier: connect this private read-only server to ChatGPT through a supported no-public-ingress path, preferably Secure MCP Tunnel if available under the user's existing OpenAI access, then perform a real read-only plugin call. Creating/selecting the tunnel and installing the custom plugin are external account actions and require explicit user action/approval; they are not inferred from this adjudication.

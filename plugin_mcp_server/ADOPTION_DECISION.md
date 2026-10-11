# External-component adoption decision — official Python MCP SDK

Decision: **ADAPT**

This record applies the standing `shared_interfaces/EXTERNAL_INTEGRATION_POLICY.md` gate.

1. **Need** — Genie needs a standards-compatible Streamable HTTP MCP transport so ChatGPT can eventually connect to the already accepted read-only tool surface.
2. **Replacement** — Using the official SDK avoids hand-maintaining a moving wire protocol, version negotiation, Streamable HTTP details, and multi-version compatibility logic.
3. **Cost** — The SDK is MIT-licensed and free. This unit selects no paid API, hosted service, larger GitHub runner, or paid model. Standard GitHub-hosted runners for this public repository are currently free under GitHub's published billing rules.
4. **User burden** — The dependency is pinned exactly in-repository and runtime-checked. CI installs and tests it automatically. The user is not expected to track or manually synchronize MCP versions.
5. **Semantic boundary** — MCP transports the existing Genie descriptors and result dictionaries. It may not reinterpret authority, UNKNOWN, provenance, receipts, currentness, execution identity, STOP/budget, acceptance, or untrusted result data.
6. **Version strategy** — Exact runtime pin `mcp==2.3.0`; any different installed version fails closed. Future versions require a new compatibility review and regression/conformance pass before the pin changes.
7. **Failure mode** — Missing/wrong SDK version prevents server construction. Malformed consumer output becomes explicit `UNKNOWN`; it is not retried automatically and does not modify Genie state.
8. **Authority** — All authority remains in the existing Genie core. MCP annotations and SDK behavior are non-authoritative transport metadata.
9. **Decision** — `ADAPT`: use the official SDK only behind the transport adapter; do not make its orchestration, policy, persistence, or lifecycle semantics part of the Genie core.

The choice can be revisited if a later SDK adds cost, recurring manual maintenance, or semantic coupling that outweighs the protocol-maintenance burden it removes.

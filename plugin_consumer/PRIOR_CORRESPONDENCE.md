# Prior-experience correspondence — ChatGPT/MCP consumer contract

Scope: a pure consumer-side mapping over the already accepted read-only `GenieFunctionAdapter`. No MCP server, network transport, authentication, provider call, dispatch, deployment or state mutation is introduced.

## Reuse / adaptation / new semantics

- **Reuse unchanged:** `shared_interfaces/function_adapter.py` SHA-256 `9627bc0967e4b6115f405671be8a2c60498101e276d96062d55572537f2769d2`; its exact two read-only tools, schemas, strict argument parsing, one-delegation behavior, preserved result dictionaries and sanitized UNKNOWN behavior.
- **Adaptation:** convert accepted function metadata to MCP-compatible `name`, `title`, `description`, `inputSchema` and explicit safety annotations; convert structured tool arguments to the adapter's JSON-string boundary; convert the adapter's validated JSON output into MCP-style `structuredContent` plus text content.
- **New semantics:** only the wrapper-integrity boundary. A locally generated correlation token checks that the adapter returns the reply for the call just issued. It is never a Genie task, execution, ledger, authorization or provenance identity.

## L7 mapping

Applicable invariants: integrity/identity are not authorization; caller-supplied IDs cannot create authority; exact IDs do not remove same-ID aliasing; direct construction cannot bypass adjudication; incomplete/blocked outcomes cannot become PASS; semantic completeness matters beyond structural validity.

Defeated shortcuts not repeated:
- do not treat MCP request IDs, plugin call IDs or local correlation IDs as Genie authority;
- do not treat a valid plugin/MCP envelope as proof the underlying Genie result is true/current;
- do not equate an installed-looking format with an installed plugin, live server or autonomous dispatcher.

Mandatory attacks: forged/extra tool names, malformed JSON trees, correlation mismatch, malformed adapter output, exceptions, and semantic states containing UNKNOWN despite top-level diagnostics.

## L2 mapping

Applicable invariants: keep authority/execution/observation/verification separate; preserve UNKNOWN and coverage; representation must preserve decisions; discovery != belief; downstream formatting must not reinterpret historical policy meaning.

Defeated shortcut not repeated: mapping a Genie `UNKNOWN` or `REJECT` dictionary to protocol success/failure semantics that invite a new logical action. Core semantic dictionaries remain ordinary structured data. Only wrapper-integrity failure becomes `isError: true`.

No retry occurs inside this consumer.

## Genie / EXP-010 mapping

One shared core is retained. The wrapper adds no second controller and no worker/provider requirement. EXP-010 scientific execution/non-exposure rules do not apply to this ordinary engineering interface unit. No scientific action is performed.

## External-domain gate

This seam enters the current ChatGPT plugin/MCP ecosystem, so current primary documentation was checked after the internal attack. The relevant official sources establish that current ChatGPT plugins can expose MCP tools; tool annotations must accurately describe behavior; structured results can carry `structuredContent` and `content`; authorization remains server-side; and the current Python MCP SDK exposes request context separately from model arguments. No SDK is required for this unit.

## Remaining HOLDs

Even if this unit passes: no MCP server/streamable-HTTP endpoint, Secure MCP Tunnel, authentication, remote hostile-client confinement, plugin installation, publication, backend, concurrent-controller assurance, after-host execution, autonomous model dispatch, promotion or production acceptance is established. Pass186 remains inherited controlling; this unit is NONCLAIM.

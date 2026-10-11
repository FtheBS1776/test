# MCP server transport contract

## Inputs

The transport accepts one trusted operator registry path at startup. The registry is parsed by the existing strict read-only CLI registry parser. Tool calls are limited to the two descriptors emitted by the accepted MCP consumer projection.

## Source and version bindings

- `shared_interfaces/mcp_consumer.py` SHA-256 must equal `21f3fc657abb16c9ba7c9189f266cbdfeaec1dbf0ae2ca6d051caee1565ddd5d`.
- Installed Python package `mcp` must report version exactly `2.3.0`.
- A source or SDK mismatch fails closed before the server is constructed.

## MCP surface

Exactly two tools are advertised, in deterministic order:

1. `get_run_status`
2. `get_task_result`

Names, titles, descriptions, JSON input schemas, and read-only annotations are copied from the accepted consumer projection. The low-level SDK server is used so the schemas are not regenerated from Python signatures.

No resources, prompts, mutation tools, sampling, elicitation, background jobs, model dispatch, filesystem write tools, shell tools, or generic method dispatch are added.

## Tool-call behavior

Each MCP `tools/call` is delegated exactly once to the accepted consumer's `call(name, arguments)` surface. The server does not retry a call because it returns `UNKNOWN`.

A valid consumer result is returned intact in MCP `structuredContent`. The accompanying model-facing text block contains only a fixed status summary and never duplicates `result_text`. If `result_text` exists, the text block explicitly says it is untrusted data, not instructions.

If the consumer projection is malformed or the transport cannot safely preserve the returned structure, the MCP result is:

`{"status":"UNKNOWN","reason":"MCP_SERVER_OUTCOME_UNKNOWN"}`

This fallback grants no authority or retry permission.

## Transport

The executable entry point serves MCP Streamable HTTP at `/mcp`, defaulting to loopback `127.0.0.1:8787`. It uses stateless HTTP with JSON responses because these two read-only tools require no server-to-client callback channel.

A public deployment, Secure MCP Tunnel connection, OAuth configuration, plugin installation, or directory publication is outside this unit.

## Authority and compatibility

MCP is transport only. Tool annotations are hints and are not authorization. The Genie core remains authoritative for provenance, acceptance, UNKNOWN, currentness, STOP/budget, and all other governed state.

No SDK upgrade is automatic. A candidate SDK or protocol revision must pass the external-integration policy and this unit's regression/conformance tests before the version pin changes.

# Genie read-only MCP server transport — NONCLAIM

This unit composes the already accepted read-only `GenieMcpReadonlyConsumer` into an actual MCP server using the official Python MCP SDK pinned to `mcp==2.3.0`.

Scope is transport only. It does **not** add model dispatch, mutation, authentication, paid hosting, public deployment, background execution, authority promotion, freeze, main merge, or EXP010 execution.

Read `CONTRACT.md` and `ADOPTION_DECISION.md` before changing this unit.

Current source: `../shared_interfaces/mcp_server.py`.

The runtime refuses to start if the installed MCP SDK version is not exactly the reviewed version. External upgrades therefore cannot silently change Genie-visible semantics.

The server exposes exactly two read-only tools through the accepted consumer:

- `get_run_status`
- `get_task_result`

`result_text`, when present, remains `UNTRUSTED_ACCEPTED_TASK_DATA`; the MCP text block does not duplicate that content and explicitly labels it untrusted. `UNKNOWN` remains non-authorizing and is not retry permission.

The local server defaults to `127.0.0.1:8787/mcp` and uses Streamable HTTP. A real ChatGPT connection still requires a supported private tunnel or reachable HTTPS endpoint; that connection is a separate external step and is not claimed by this checkpoint.

Automated tests run on the isolated NONCLAIM branch with standard GitHub-hosted Linux runners. The repository is public, so that standard runner usage is currently free under GitHub's published billing rules. No larger runner, paid service, or artifact storage requirement is introduced here.

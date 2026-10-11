# Genie read-only MCP local transports — NONCLAIM

This unit composes the already accepted read-only `GenieMcpReadonlyConsumer` into actual MCP transports using the official Python MCP SDK pinned behind an exact 28-distribution compatibility closure.

Scope is transport only. It does **not** add model dispatch, mutation, authentication, paid hosting, public deployment, background execution, authority promotion, freeze, main merge, or EXP010 execution.

Read `CONTRACT.md` and `ADOPTION_DECISION.md` before changing this unit.

Current source: `../shared_interfaces/mcp_server.py`.

The runtime refuses to start if the reviewed transport dependency closure or pinned consumer source does not match. External upgrades therefore cannot silently change Genie-visible transport semantics.

The server exposes exactly two read-only tools through the accepted consumer:

- `get_run_status`
- `get_task_result`

`result_text`, when present, remains `UNTRUSTED_ACCEPTED_TASK_DATA`; the MCP text block does not duplicate that content and explicitly labels it untrusted. `UNKNOWN` remains non-authorizing and is not retry permission.

## Tested transports

### Host-spawned stdio — preferred local Desktop path

`--transport stdio` runs the same accepted handlers over stdin/stdout. A compatible desktop host can start and stop this process itself, so the user does not need to keep a separate HTTP server running. This is the preferred current packaging target for a local ChatGPT Desktop plugin because it requires no paid hosting or public ingress.

### Streamable HTTP — retained portability path

The default transport serves loopback Streamable HTTP at `127.0.0.1:8787/mcp`. This remains useful for conformance and possible future remote/tunnel portability, but it is not a routine manual prerequisite for the preferred local plugin path.

Final bounded CI evidence at tested commit `52b72cff246f9e1fe92eea694a9f9afce93ca109` passed the exact 28-distribution closure, `pip check`, and 8/8 tests including real stdio and real Streamable HTTP calls against saved Genie state with SQLite stores byte-identical before/after.

A real ChatGPT plugin installation/connection is still a separate external user action and is not claimed by this checkpoint.

Automated tests run on the isolated NONCLAIM branch with standard GitHub-hosted Linux runners. The repository is public, so that standard runner usage is currently free under GitHub's published billing rules. No larger runner, paid service, or artifact storage requirement is introduced here.

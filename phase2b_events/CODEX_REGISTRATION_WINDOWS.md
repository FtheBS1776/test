# Separate local Codex registration — reference only

Phase 2B1 is tested directly over stdio without changing global Codex configuration. Any later authorized registration must use a distinct identity such as `genie-events-phase2b1`, an absolute reviewed Python/executable path, this exact branch checkout, and a separately approved controller-owned registry:

```toml
[mcp_servers.genie-events-phase2b1]
command = '<absolute-path-to-reviewed-python-or-events-exe>'
args = ['-B', '-m', 'shared_interfaces.mcp_events_server', '--registry', '<absolute-path-to-controller-owned-registry.json>']
cwd = '<absolute-path-to-this-exact-branch-checkout>'
```

Do not add this tool to `genie-readonly` or the Phase 2A controller, point it at an existing historical run, expose it over HTTP, or enable it in a worker/reviewer context. MCP approval UX is not Genie authorization. UNKNOWN preserves the original state and grants no replay.

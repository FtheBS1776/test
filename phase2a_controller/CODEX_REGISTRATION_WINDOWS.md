# Separate local Codex registration — reference only

Phase 2A was exercised directly over stdio without changing the user's global Codex configuration. If a later explicitly authorized local registration is needed, it must use a separate identity such as `genie-controller-phase2a`, an absolute Python/executable path, this branch's working directory, and the Phase 2A-only registry:

```toml
[mcp_servers.genie-controller-phase2a]
command = '<absolute-path-to-the-reviewed-python-or-controller-exe>'
args = ['-B', '-m', 'shared_interfaces.mcp_controller_server', '--registry', '<absolute-path-to-phase2a_controller/trial/REGISTRY.json>']
cwd = '<absolute-path-to-this-exact-branch-checkout>'
```

Do not add this tool to `genie-readonly`, point it at the installed read-only state, expose it over HTTP, or enable it in worker/reviewer contexts. MCP approval UX is not Genie authorization. A new process after an uncertain call may only reconcile the preserved original state; it is not retry permission.

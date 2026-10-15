# Alpha isolation preflight contract

Classification: **NONCLAIM**.  One fresh no-auth app-server process entry, no
semantic request, no thread, no turn, no model invocation, and no retry.

The exact alpha executable runs under the accepted kill-on-close Windows Job
path.  Its `CODEX_HOME` starts empty, no API or access-token variable is passed,
and network proxy variables point to a closed local endpoint.  Configuration
explicitly empties MCP servers, disables apps/plugins/agent/tool features, and
selects read-only/never policy.  Effective config and MCP status must be read
back before acceptance.

Assignment and Job policy verification precede protocol traffic.  Any
uncertainty after process entry is terminal `UNKNOWN`, with preservation,
`allow_new_invocation=false`, and no retry or alternate launcher.

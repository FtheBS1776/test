# Repaired recovery-preflight contract

Classification: **NONCLAIM**.  This authorization covered one fresh logical
operation and one Codex app-server process entry.  The protocol surface allowed
only `initialize`, `config/read`, `mcpServerStatus/list`, and `model/list`, plus
the `initialized` notification.  It prohibited semantic requests,
`thread/start`, `turn/start`, model execution, tools, callbacks, delivery,
reviewer progression, retries, replacement launchers, and Phase 2C.

The child used the existing ChatGPT login, a separate empty scratch directory,
read-only sandbox configuration, approval `never`, explicit empty MCP config,
and disabled app/plugin/multi-agent/tool capabilities.  Effective inventory had
to be observed, not inferred.  Assignment to the kill-on-close Windows Job had
to precede protocol traffic.  Any uncertainty after process entry was terminal
UNKNOWN with preservation and no new invocation.

The configuration corresponds to the official Codex configuration reference:
<https://learn.chatgpt.com/docs/config-file/config-reference>.

# Isolation-verification preflight contract

Classification: **NONCLAIM**.  This authorization covered one fresh logical
operation and one Codex app-server process entry.  The protocol surface allowed
only `initialize`, `config/read`, `mcpServerStatus/list`, and `model/list`, plus
the `initialized` notification.  It prohibited semantic requests,
`thread/start`, `turn/start`, model execution, tools, callbacks, delivery,
reviewer progression, retries, replacement launchers, and Phase 2C.

The planned child used the existing ChatGPT login, a separate empty scratch
directory, read-only sandbox configuration, approval `never`, explicit empty
MCP config, disabled capabilities, and the documented `--ignore-user-config`
flag.  Effective inventory had to be observed rather than inferred.  Assignment
to the kill-on-close Windows Job had to precede protocol traffic.  Any
uncertainty after process entry was terminal UNKNOWN with preservation and no
new invocation.

The flag is documented in the official Codex CLI reference:
<https://learn.chatgpt.com/docs/cli/reference>.

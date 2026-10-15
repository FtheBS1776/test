# Phase 2B2 recovery preflight contract

Classification: **NONCLAIM**.  One fresh logical operation and one actual Codex
app-server process entry, with zero semantic requests and zero model turns.

Allowed protocol requests were exactly `initialize`, `config/read`,
`mcpServerStatus/list`, and `model/list`.  `initialized` was the only notification.
No `thread/start`, `turn/start`, tool call, callback, reviewer, delivery, or
session-driver progression was permitted.  The child used the existing ChatGPT
login, read-only sandbox, approval `never`, explicit empty MCP configuration,
disabled apps/plugins/multi-agent and related capabilities, and a fresh empty
scratch directory outside the Genie trial.

The process had to be assigned to the kill-on-close Windows Job before protocol
traffic.  Once process entry was attempted, uncertainty was terminal UNKNOWN
with preservation, no retry, and no replacement launcher or identity.

The configuration corresponds to the official Codex configuration reference:
<https://learn.chatgpt.com/docs/config-file/config-reference>.

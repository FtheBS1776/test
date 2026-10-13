# Phase 2B2 live pilot contract

Classification: **NONCLAIM**.  One fresh synthetic run, one logical operation,
at most one Codex app-server process entry, at most one model turn, no retries.

The exact child binding is Codex CLI `0.162.1`, executable SHA-256
`dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`,
model `gpt-5.6-sol`, reasoning `low`, service tier `default`, read-only sandbox,
approval `never`, empty dynamic tools/environments/capability roots, explicit
empty MCP configuration, disabled apps/plugins/multi-agent and related tool
features, and existing ChatGPT authentication through `CODEX_HOME`.  No API key
or paid external service is introduced.  The isolation choices correspond to
the official Codex configuration reference at
<https://learn.chatgpt.com/docs/config-file/config-reference>.

Before semantic release, the parent must assign the child to a non-breakaway
kill-on-close Windows Job, verify membership/policy, read effective config,
obtain an empty paginated MCP status result, and verify the bound model/effort.
The semantic prompt is a fixed data-only request containing no Genie identity or
path.  Output is accepted only as untrusted worker data and only after fresh
destination readback.

Any uncertainty from the `Popen` attempt onward is terminal `UNKNOWN` with
`preserve=true`, `allow_new_invocation=false`, and no retry/refund/reset,
replacement identity, or alternate launcher.  This pilot stops before Phase 2C,
broader mutations, main merge, promotion/freeze, spending, production claims,
or EXP010.

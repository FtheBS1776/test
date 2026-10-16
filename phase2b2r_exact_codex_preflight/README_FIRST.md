# Phase 2B2R exact Codex no-model preflight

Classification: **NONCLAIM**. This stage verifies the freshly built, exact
patched `codex.exe` before any model turn is authorized.

The workflow checksum is independently recomputed. One Codex process is then
started with `--no-tools`, the exact logical-operation identity, ignored user
configuration, empty MCP configuration, disabled apps/plugins/multi-agent,
read-only sandbox, and stdin deliberately withheld. The process is assigned to
the accepted non-breakaway kill-on-close Windows Job before any semantic bytes
are released. Live member identities are captured with retained handles; the
Job is terminated once; every member must signal; fresh accounting must report
zero active members.

This stage performs zero model turns, makes no claim of general sandboxing or
independent provenance, and grants no retry after process entry. A deterministic
artifact/checksum failure before process entry may `REJECT`; all uncertainty
from `Popen` onward is terminal `UNKNOWN` with `preserve=true` and
`allow_new_invocation=false`.

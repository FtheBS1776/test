# Phase 2B2Q: exact Codex capability build

This NONCLAIM stage carries a source-only patch against the exact upstream
`rust-v0.163.0-alpha.11` release commit
`5425d3e625daa58eea3ad1de27c087eb3b2ffbd3`.

The patch reuses that release's startup-captured `ToolPolicy` with an empty
allowlist, rejects any nonempty finalized router before sampling, and emits one
hash- and logical-operation-bound `capability.snapshot` record before the JSONL
`turn.started` record.  It does not add a model provider, API key, paid service,
public deployment, tunnel, or recurring task.

The workflow is deliberately branch-scoped and one-shot.  It checks the exact
upstream commit, applies the patch, formats and tests the changed execution
path, builds `codex.exe` on a clean Windows runner, records its SHA-256 digest,
and retains the artifact for seven days.  Building the binary is not authorization
to run a model turn.

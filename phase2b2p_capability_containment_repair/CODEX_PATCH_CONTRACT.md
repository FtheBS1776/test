# Codex patch contract — NONCLAIM

The live worker remains prohibited until an exact, hash-bound Codex executable
implements both requirements below.

1. `--no-tools` must bind the existing startup `AllowedTools([])` policy before
   tool planning.  Empty means no advertised or routable built-in, hosted,
   dynamic, extension, plugin, MCP, app, collaboration, deferred, Code Mode,
   `exec`, or `wait` tool.  Later config, resume state, or turn state may not
   widen the captured policy.
2. Immediately after the final tool router is constructed and before the first
   model request, `exec --json` must emit exactly one `capability.snapshot`
   record matching `repair_contract.validate_capability_snapshot`.  It contains
   identities and digests only, never credentials or authority-bearing paths.

The controller must validate the snapshot before writing the semantic request
to stdin.  Missing, late, duplicate, stale, nonempty, or mismatched snapshots
fail before semantic release.  Any uncertainty after process entry remains
UNKNOWN with preserve=true and allow_new_invocation=false.

The Windows monitor must capture every member's image and hash at first live
observation, retain its process handle, reconcile captured identities with Job
total-process accounting, and require zero active processes at termination.

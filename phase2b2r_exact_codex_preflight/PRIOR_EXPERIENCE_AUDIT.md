# L7/L2/Genie/EXP010 correspondence audit

This standing correspondence audit was applied before the Phase 2B2R design or
execution and before the exact build artifact is admitted.

- **L7 — preserve raw evidence before interpretation.** The workflow checksum
  is not trusted by itself: the downloaded executable is hashed again locally.
  The executable, source commit, empty-tool policy, model, sandbox, and logical
  operation are bound by exact values and digests. Runtime stdout/stderr are
  bounded and hashed, while process identity is captured live through retained
  handles rather than reconstructed from PIDs after exit.
- **L2 — keep evidence layers separate.** Artifact provenance, CLI binding,
  Job containment, capability attestation, event classification, worker output,
  and destination readback are separate checks. Neither a GitHub workflow nor
  Codex JSONL is treated as sole authoritative observation. This preflight does
  not produce or accept worker output.
- **Genie — child has no authority.** The child receives no Genie token, queue
  path, owned-root path, registry path, mutation tool, callback, historical run
  state, or authority-bearing secret. Its environment identifies the existing
  Codex home for authentication reuse but passes no credential value. Stdin is
  withheld for the entire no-model preflight.
- **EXP010 — evidence discipline only.** EXP010 is not read, mutated, launched,
  promoted, frozen, or otherwise exercised. No claim transfers from it.

The earlier live `UNKNOWN` operations remain terminal and unchanged. A checksum
or other deterministic failure before `Popen` may `REJECT`. From the process
entry attempt onward, every uncertainty is `UNKNOWN`, preserves the operation,
allows no replacement invocation, and is never retried.

## Disposition

- Exact artifact hash readback, withheld-stdin process entry, verified Job
  assignment, eager member identity capture, one termination, and fresh
  zero-active readback: **ADAPT**.
- Accepted Phase 2A/2B1/2B2A/2B2B artifacts and read-only Genie integrity:
  **PRESERVE**.
- One later attested worker turn, untrusted result handling, and fresh
  destination readback: **DEFER until this preflight accepts**.
- Retry after entry, replacement identity, alternate launcher, reviewer/model
  dispatch, Phase 2C autonomy, main merge, promotion/freeze, spending, broad
  mutation, production claims, or EXP010 execution: **REJECT**.

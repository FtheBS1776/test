# Phase 2B2S single attested live pilot

Classification: **NONCLAIM**. This stage may run only after Phase 2B2R accepts
the exact downloaded executable. It admits one durably claimed logical
operation, one Codex process entry, and at most one model turn. There is no
retry, refund, reset, replacement identity, or alternate launcher after entry.

The exact executable/source/hash, model, effort, service tier, read-only
sandbox, output schema, semantic request, dispatch token, and canonical empty
tool policy are bound into the logical-operation digest. User configuration is
ignored; MCP is empty; apps/plugins/multi-agent and related tool surfaces are
disabled; `--no-tools` installs the empty startup policy. The exact finalized
router must emit one matching `capability.snapshot` before `turn.started` and
must expose zero tools. Any mismatch or tool-shaped event is terminal UNKNOWN.

Raw stdout/stderr are durably stored and read back before classification, but
JSONL is not sole authority: the workflow checksum is independently rehashed,
the Job process tree is captured through retained live handles, output is
cross-checked against a separately read destination file, and task acceptance
requires a later fresh Genie destination readback. All worker output remains
untrusted data. Same-host/same-provider evidence remains common-cause and
non-independent.

## Sealed outcome

The one authorized execution completed on 2026-10-16. The final capability
snapshot reported zero tools and matched the bound executable, logical
operation, model, sandbox, and policy digests. The result was accepted only
after fresh destination readback. This outcome does not widen the contract or
authorize Phase 2C.

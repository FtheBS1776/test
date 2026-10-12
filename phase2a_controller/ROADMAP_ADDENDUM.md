# Genie roadmap addendum — Phase 2A controller boundary

Phase 2A implements a separate, local, stdio-only MCP projection over the accepted one-step `advance_run` primitive. It does not change the read-only integration or Genie core semantics.

Exit criteria are: exact one-tool discovery; explicit write/destructive/non-idempotent metadata; trusted one-alias synthetic registry; one live MCP call returning a bound action/token; no model dispatch, callback, review, report, or application; UNKNOWN/no-retry preservation; adversarial/mutation checks; and byte-identical read-only package plus historical state.

**Mandatory stop:** do not expose worker/reviewer dispatch, `apply_run_event`, or `session_driver` from this branch. Those are Phase 2B or later and require a new correspondence audit and explicit authorization. No main merge, promotion, freeze, spending, or EXP010 activity follows from Phase 2A.

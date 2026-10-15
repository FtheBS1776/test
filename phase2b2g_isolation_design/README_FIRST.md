# Phase 2B2 isolation recovery design - read first

Classification: **OFFLINE DESIGN ONLY - NONCLAIM**.

This directory records the recovery design after the terminal isolation-
verification preflight `UNKNOWN`.  It contains no launcher and performed no
Codex process entry, model turn, credential copy, authentication change,
software upgrade, or Genie mutation.

The decision is to reject credential-cache duplication and require a separate,
explicitly authorized Codex upgrade or rebind before any new preflight.  The
replacement binary must first prove offline that it accepts the documented
`--ignore-user-config` flag.  A later, separately authorized no-model preflight
would still have to observe the actual empty MCP/tool inventory; the flag alone
is never acceptance evidence.

All earlier `UNKNOWN` operations remain preserved and non-retryable.

# Genie Phase 2B2A fixture-only process-boundary candidate — NONCLAIM

This checkpoint adds a host-internal launcher for exactly one deterministic `NO_MODEL_CALL` Python fixture. It tests a narrow parent/child process boundary: a bounded parent request travels over stdin to a fresh non-repository working directory, the child receives a minimal environment, and its strictly validated response remains untrusted fixture data.

The launcher is not an MCP server and is not registered with Codex. It cannot call `advance_run`, `apply_run_event`, `session_driver`, a worker model, or a reviewer model. Its only executable child is the exact local CPython path and byte hash plus the exact repository fixture path and byte hash. The separate Codex CLI function returns a deferred, non-executable argv sketch only.

A launcher-local SQLite claim is committed before the fixture process starts. Reuse of that exact launch ID after a persisted claim in the same fresh, untampered disposable store never spawns again. This is not global exactly-once, rollback resistance, hostile-tamper resistance, or suppression for a fresh launch ID/store. Handled uncertainty after claim commit returns canonical `UNKNOWN`, preserves the claim, and grants no new invocation permission; the launcher itself never retries. Forced process termination can prevent any return value.

Read [the contract](CONTRACT.md), [the correspondence audit](PRIOR_EXPERIENCE_AUDIT.md), [the isolation profile](ISOLATION_PROFILE.md), [test results](TEST_RESULTS.md), [adjudication](ADJUDICATION.md), [roadmap stop](ROADMAP_ADDENDUM.md), and machine-readable [verification](VERIFICATION.json) and [source manifest](SOURCE_MANIFEST.json).

Phase 2B2A is not Phase 2B2 completion. No model, provider, authentication, effective Codex tool-inventory probe, persistent Genie run/store, callback, MCP exposure, global registration, spending, main merge, promotion/freeze, or EXP010 activity occurred.

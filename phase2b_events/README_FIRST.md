# Genie Phase 2B1 event MCP candidate — NONCLAIM

This checkpoint adds a separate local stdio MCP projection of the already accepted `GenieRunEvents.apply_run_event` primitive. Discovery contains exactly one write/destructive/non-idempotent tool. Its three operation values remain `observe`, `submit`, and `review`; no new mutation semantics were introduced.

The Windows stdio tests use fresh temporary stores. One deterministic sequence records a synthetic no-model observation, submits fixed fixture text, and applies a synthetic caller-supplied ACCEPT. It reaches task `ACCEPTED` but stops before progression: the queue is still ACTIVE, one reservation remains charged, and reports/applications are zero. The fixture data is not worker output or reviewer judgment and proves no model execution, provenance, truth, independence, completion, or delivery.

Read [the contract](CONTRACT.md), [the correspondence audit](PRIOR_EXPERIENCE_AUDIT.md), [the isolation gate](ISOLATION_GATE.md), [test results](TEST_RESULTS.md), [adjudication](ADJUDICATION.md), and the machine-readable [source manifest](SOURCE_MANIFEST.json). The accepted Phase 2A charged run, installed `genie-readonly`, historical stores, core interfaces, and global Codex configuration are not changed.

Phase 2B1 is not Phase 2B completion. No model subprocess, worker/reviewer dispatch, live persistent callback, session driver, automatic progression, HTTP endpoint, main merge, spending, promotion/freeze, or EXP010 activity occurred.

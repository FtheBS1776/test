# Phase 2B2A root adjudication — NONCLAIM

**Decision: ACCEPT the fixture-only process-boundary candidate; stop before live Codex worker/reviewer execution or any event surface.**

The implementation launches only the exact deterministic `NO_MODEL_CALL` fixture through a fixed local CPython path/hash. It uses `-I -S -B`, a complete fixed argv, bounded stdin/stdout/stderr, no shell, a rebuilt minimal environment, a fresh non-repository cwd, and strict response binding. A launcher-local exact-schema claim is committed before Popen; the same persisted launch ID cannot spawn again in the same fresh untampered store. Handled post-claim faults are canonical UNKNOWN with preservation and no new-invocation permission.

The adversarial suite kills bad-input, path/hash/alias, hostile-schema/trigger, injected-hardlink, crossed/concurrent ID, post-commit loss, source-change, transport, cancellation, output-bound, malformed-output, forged-metadata, retry, and deferred-Codex-plan mutants. The final targeted suite is 27/27; the full accepted regression set is 110/110. Independent read-only code/test/evidence reviews found and prompted repairs for site startup, claim triggers/aliases, source check/use gaps, final-envelope bounds, cancellation semantics, self-referential test oracles, and overbroad documentation. Final independent code review found no remaining blocker under the recorded scope.

Acceptance is narrow. Request strings are semantically unverified; the launcher does not prove secrets absent. Hashes do not pin the full CPython/stdlib/OS closure. Path checks cannot defeat hostile same-user concurrent replacement. Direct-child cleanup is one bounded attempt, not descendant-tree control. A new launch ID/store is a new parent decision, so the claim is not global exactly-once, rollback resistance, or caller-proof retry prevention. Same-host review remains common-cause.

The Codex 0.162.1 profile is a non-executable plan only. It performed no authentication, model selection, provider call, process spawn, or effective tool-inventory probe. No persistent Genie state, Phase 2A run, read-only package/state, or historical run was changed.

Do not infer worker observation, model execution, provenance, content truth/quality, review independence, callback acknowledgement, completion, delivery, currentness, hostile isolation, production readiness, or Phase 2B2 completion. No MCP exposure, global registration, session driver, main merge, spending, promotion/freeze, or EXP010 activity is authorized by this checkpoint.

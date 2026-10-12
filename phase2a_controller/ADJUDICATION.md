# Phase 2A root adjudication — NONCLAIM

Decision: **ACCEPT Phase 2A and stop at the controller boundary.**

The implementation reuses the unchanged, hash-pinned `GenieRunController` and exposes it through a distinct local stdio server with exactly one explicitly destructive, non-idempotent tool. The registry binds one fresh synthetic alias to host-owned paths. The existing `genie-readonly` source, installed package, installed state, and all captured historical SQLite state remain byte-identical to their pre-pilot baselines.

The sole recorded call returned a correctly bound `INVOKE_WORKER` action/token. This is an action record, not execution evidence. Persisted state shows one charged reservation and one host-call intent, while worker/reviewer/result fields remain absent and observations, reports, and applications remain zero.

The raw SQLite stores, raw call result, and raw post-call snapshot remain locally preserved in that charged state but are excluded from branch history. The published evidence is bounded and redacted, including exact database hashes, state counts, and one-way binding commitments; this avoids exposing unnecessary raw local state or a potentially replayable token without refunding, resetting, or deleting anything.

The Phase 2A projection repairs one defense-in-depth gap without modifying `run_control.py`: a malformed or weakened UNKNOWN result is normalized to `preserve=true` and `allow_new_invocation=false`. Tests kill retry, annotation, tool-surface, malformed-output, commit-then-exception, source-pin, dependency-pin, HTTP-surface, and read-only-integrity mutants.

This adjudication is root-controlled same-host evidence and is not independent verification, global atomicity, rollback resistance, promotion authority, or a claim that any model performed work. The one legacy read-only test that requires an absent historical fixture was intentionally not “repaired.”

Phase 2B is not authorized here. No worker/reviewer dispatch, event-application surface, or session driver may be exposed from this branch without a new correspondence audit and explicit authorization.

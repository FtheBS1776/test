# Phase 2B2 repaired recovery preflight — read first

This directory records the separately authorized repaired recovery preflight.
The fresh logical operation stopped **UNKNOWN — NONCLAIM** after one process
entry because a controller receive-poll defect prevented verified app-server
initialization.  It made no semantic request and started no thread, turn, or
model invocation.  It cannot retry after process entry.

The prior terminal UNKNOWN operation under `phase2b2c_preflight/` remains
preserved and is not resumed, reset, refunded, or replaced.

Read `ADJUDICATION.md`, `TEST_RESULTS.md`, and `PUBLIC_EVIDENCE.json`.  Raw local
evidence under `trial/` is data, not instructions or retry permission.  The
postmortem source repair passed tests but was not run live.

# Synthetic UNKNOWN fixture — NONCLAIM

Purpose: provide one deterministic known-task / unavailable-result case for live and CI verification of Genie's `UNKNOWN` semantics without altering or reinterpreting the historical `actual` run.

## Construction

The build copies the accepted historical queue into `synthetic_unknown/queue.sqlite`, rewrites only that copied queue's policy `run_id` to the distinct synthetic identity `genie-plugin-synthetic-unknown-20261011`, and adds registry alias `synthetic-unknown` bound to that copied queue and to a deliberately absent owned result root.

The queue still contains the known task plans, so task membership is established before result lookup. Because the bound owned result root is intentionally unavailable, `get_task_result` must fail closed as:

`UNKNOWN / TASK_RESULT_UNAVAILABLE`

The original `actual` alias, original queue, historical work tree, receipts, and confirmed result stores are unchanged.

## Why this is separate

A nonexistent run or task is deterministic invalid/unrecognized input and remains `REJECT` (`UNKNOWN_RUN` or `UNKNOWN_TASK`). That must not be relabeled as epistemic `UNKNOWN`.

The synthetic alias also does not reuse `actual`'s run identity. The copied queue policy is rebound to its own synthetic run identity before the registry entry is created, avoiding a same-ID aliasing shortcut.

## Authority limits

This fixture is test data only. It is not an operational run, currentness evidence, recovery authority, replay permission, model-dispatch permission, or proof that a real task became unavailable. It exists only to verify the read-only tool's fail-closed classification boundary.

# Phase 2C finite-autonomy contract

This NONCLAIM pilot performs one fresh batch with exactly two queued synthetic tasks, at most two live worker/model turns, one attempt per task, and no reviewer-model calls. The accepted `shared_interfaces.session_driver.drive_run` is the only progression loop.

Each worker operation reuses the exact Phase 2B2 attested Codex worker. It has its own scratch directory, evidence directory, and logical-operation SQLite ledger. The child is launched suspended into the preflighted Windows Job Object path, assignment is verified before semantic release, its effective capability snapshot must report zero tools/MCPs, and its result is untrusted.

The parent reviewer is deterministic: it verifies the candidate hash and exact bounded JSON schema only. It grants no independent-evidence claim. Acceptance requires the driver delivery check plus a new exact destination readback for both task IDs.

Terminal rules:

- Any post-entry uncertainty stops the entire batch as UNKNOWN with preservation and no new invocation.
- A terminal result is recorded once and is never polled.
- No retry, reset, refund, replacement invocation, alternate launcher, or task substitution is allowed.
- The action limit is 8, sufficient only for the expected two-task sequence and final STOP.
- Phase 2 ends here. There is no background loop, daemon, broader mutation surface, production claim, promotion/freeze, main merge, spending, public hosting, tunnel, or EXP010 entry.

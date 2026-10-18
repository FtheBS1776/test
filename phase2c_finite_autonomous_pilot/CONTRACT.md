# Phase 2C finite-autonomy contract

This NONCLAIM pilot performs one fresh batch with exactly two queued synthetic tasks, at most two live worker/model turns, one attempt per task, and no reviewer-model calls. The accepted `shared_interfaces.session_driver.drive_run` is the only progression loop.

Each worker operation reuses the exact Phase 2B2 attested Codex worker. It has its own scratch directory, evidence directory, and logical-operation SQLite ledger. The child is created with CREATE_NO_WINDOW, then assigned to the preflighted Windows Job Object; assignment is verified before semantic input is released, its effective capability snapshot must report zero tools/MCPs, and its result is untrusted. This is not CREATE_SUSPENDED and does not prevent execution before Job assignment.

The parent reviewer is deterministic: it verifies the candidate hash and exact bounded JSON schema only. It grants no independent-evidence claim. Acceptance requires the driver delivery check plus a new exact destination readback for both task IDs.

Terminal rules:

- The driver preserves the exact original token and candidate hash. A hash-bound candidate that misses this task's schema receives `REPAIR` with bounded feedback, not acceptance. Strict parsing reuses the driver's duplicate-key/nonfinite rejection helpers, and JSON serialization comparison preserves the distinction between booleans and numbers. Ordinary candidate JSON decode failures are also repair feedback; malformed review envelopes and unexpected runtime failures retain the driver's `UNKNOWN` stop.
- The existing bridge records that review and controls whether the configured attempt budget permits another worker call. At the attempt limit the result is `HOLD / ATTEMPT_BOUND`; at the call limit it is `STOP / CALL_BUDGET_EXHAUSTED`. Reservations remain charged. No new task-rejection state or blanket `REJECT` translation is introduced.
- A hash mismatch remains `REJECT` at the reviewer boundary. The driver independently rejects a token/hash mismatch or unsupported review decision as `UNKNOWN`, before a review callback and without a new invocation. The reviewer does not authenticate tokens or principals; binding remains with the existing driver/event/bridge owners.
- Any post-entry uncertainty stops the entire batch as UNKNOWN with preservation and no new invocation.
- A terminal result is recorded once and is never polled.
- No retry, reset, refund, replacement invocation, alternate launcher, or task substitution is allowed.
- The action limit is 8, sufficient only for the expected two-task sequence and final STOP.
- Phase 2 ends here. There is no background loop, daemon, broader mutation surface, production claim, promotion/freeze, main merge, spending, public hosting, tunnel, or EXP010 entry.


## Current source inspection behavior (R05)

`python -B -m phase2c_finite_autonomous_pilot.verify_sealed --evidence-directory COPY` inspects the selected copy and prints the existing success marker; it creates no report by default. Optional `--report NEW_EXTERNAL_FILE` requires an explicit path outside that evidence directory and exclusive creation. Existing files and symlinks cannot be overwritten. Recorded Windows image paths are parsed as data with PureWindowsPath; that does not rerun or prove Windows execution. Report publication is not claimed atomic or hostile-path safe. Tests inspect byte-verified disposable copies; original verification records remain historical.

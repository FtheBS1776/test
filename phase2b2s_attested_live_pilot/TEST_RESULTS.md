# Phase 2B2S test and execution results

- Focused post-execution suite: 29 passed, zero failures, zero skips.
- Fresh synthetic task: one task, one attempt, one reserved model call.
- Live worker: one process entry and one completed model turn.
- Capability snapshot: exact logical operation, executable, model, sandbox,
  and canonical policy hashes; `tool_count=0`; `tools=[]`.
- Raw JSONL: one snapshot before one `turn.started`, one agent message, one
  `turn.completed`, and no tool item. The single known disabled-Code-Mode
  advisory occurred before the turn and matched the accepted exact text.
- Process evidence: patched `codex.exe` plus `conhost.exe`, both captured and
  hashed while active; zero active members after bounded exit and after the
  single termination call.
- Result evidence: raw stream persisted before interpretation, last-message
  file matched, deterministic common-cause review bound the candidate hash,
  and fresh destination readback returned `CONFIRMED` with content role
  `UNTRUSTED_ACCEPTED_TASK_DATA`.
- Durable ledger: `OBSERVED_ACCEPTED`, `preserve=1`,
  `allow_new_invocation=0`; retry count zero.

No reviewer model was dispatched. No Phase 2C, session-driver autonomy,
historical-run mutation, main merge, promotion/freeze, spending change,
production claim, or EXP010 action occurred.

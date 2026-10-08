# Bounded queue and checkpoint comparison quickstart

This trial authorizes two tasks and at most three model-call reservations: implement the checkpoint comparison CLI, then write this guide. Repairs consume remaining reservations. A reservation stays charged when invocation is uncertain; the count is not a measurement of model calls actually launched, tokens or spending.

The controller reports that task 1 passed its acceptance checks and completed through fresh sink readback, after which the queue selected this guide without another user continuation prompt. This guide's author did not execute those checks or independently verify revised queue code.

## Compare two checkpoints offline

Use Python 3.12 and the reviewed source layout with sibling `run_queue` and `host_adapter` directories. Keep the pinned `host_adapter/verify_checkpoint.py` available; its expected SHA-256 is `6b3c01c598e904c9aa171d7b22995cd0eb918db2c9cabf289c1003987db737b6`. Obtain each ZIP's expected hash from your intended reference record. Replace every placeholder below; hashes must be exactly 64 lowercase hexadecimal characters.

```bash
python3.12 /absolute/path/to/run_queue/compare_checkpoints.py \
  /absolute/path/to/OLD.zip /absolute/path/to/NEW.zip \
  --old-sha256 OLD_EXPECTED_SHA256 \
  --new-sha256 NEW_EXPECTED_SHA256
```

The CLI verifies both archives, then compares manifest mappings from bounded immutable snapshots whose outer hashes match the same anchors. Each compressed snapshot is limited to 64 MiB. It performs no extraction, archive-code execution or network operation.

Successful JSON has `status: PASS`, `old_sha256`, `new_sha256`, sorted `added`, `removed`, `changed` and `unchanged` path arrays, and `evidence_scope: INTEGRITY_COMPARISON_ONLY`. Either changed payload hash or size counts as changed; `MANIFEST.json` is excluded. Equal archives have empty change arrays. Missing inputs, malformed archives, hash mismatches and other ordinary failures produce JSON REJECT and a nonzero exit; preserve the rejection rather than treating missing output as success.

This compares bound bytes. It does not establish semantic progress, correctness, authenticity, authority or promotion. A manifest bundled with its own files is not independent trust.

## Operate and reconcile the queue

The queue selects authorized work and reserves budget. The host journal records invocation permission and observations; only the running controller invokes the model interface. Neither component supplies an always-on service or guarantees continuation after the host ends.

Preserve task, attempt, input digest, call ID and reservation context across interruptions. An uncertain reservation or missing agent requires reconciliation of existing host evidence, not automatic redispatch or a refund. Queue/task ledger updates are separate transactions; there is no cross-store atomicity claim.

The persisted dispatch supplies controller-reviewed policy updates: stopped ACTIVE work returns `RECONCILE_TASK` without fresh invocation; reservation/completion require `run_id`; reservation identity is `(run_id, slot_id)`; completion compares the full reserved/task request; incomplete queue inspection returns UNKNOWN without overwrite. These are attributed controller updates, not this author's revised-source verification.

Scoped HOLDs allow other independently authorized READY tasks to proceed within budget. Respect the persisted stop reason, including budget exhaustion, held-only work, completion or host/authority/dependency boundaries. Worker DONE never completes a task: accepted content and fresh destination readback are required. Queue completion records historical readback; re-observe before relying on current destination state. Shared-model review is not independent evidence or hostile-worker isolation. Production and promotion remain unauthorized.

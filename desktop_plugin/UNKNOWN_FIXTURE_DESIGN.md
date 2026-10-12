# Identity-safe UNKNOWN fixture design

Purpose: add one synthetic, clearly labeled read-only fixture that proves `get_task_result` can return literal `UNKNOWN / TASK_RESULT_UNAVAILABLE` for a **known** task without corrupting or reinterpreting the historical `actual` run.

## Requirements

- The historical `actual` alias and both of its confirmed tasks remain byte-for-byte source inputs; no existing result is degraded to manufacture UNKNOWN.
- The synthetic alias uses its own run identity: `genie-plugin-unknown-fixture-20261011`.
- The synthetic task uses its own task identity: `genie-known-unavailable-fixture-20261011`.
- The queue contains exactly one valid known task plan but no corresponding task ledger/result destination.
- `get_task_result` must therefore pass alias membership and task membership, then fail closed at unavailable result evidence and return exactly `UNKNOWN / TASK_RESULT_UNAVAILABLE`.
- A nonexistent alias remains `REJECT / UNKNOWN_RUN`; a nonexistent task remains `REJECT / UNKNOWN_TASK`.
- The fixture is generated deterministically during package build from the existing pinned queue implementation; it is not claim-bearing historical evidence.
- The fixture grants no model call, execution, delivery, acceptance, promotion, or currentness authority.

This design specifically avoids same-ID aliasing: neither the run identity nor task identity is reused from `actual`.

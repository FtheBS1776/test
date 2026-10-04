# Post-research cross-attack — bounded integration subject

The detailed candidate matrix and limits are in `PASS219_ETCD_CROSS_ATTACK.md` delivered with the review. This document applies that attack to the exact test subject in this package.

## Cross-attack findings

- **Currentness:** the adapter sends a fresh JSON-gateway Range with `serializable: false`, binds the caller's challenge into its returned adapter observation, checks the exact configured authority config and fixture provider/cluster binding, then compares both current bytes and observed mod_revision in the Txn. The challenge is not sent to etcd and is not a provider signature or independent freshness proof. A cached observation cannot be passed to the activation method.
- **Atomicity:** the transaction writes exactly one current key, one transition receipt key, one global execution-consumption key, and at most one outbox key. Compare predicates require the receipt, execution, and any outbox key to be absent. Duplicate mutation/effect identities are rejected before submission. Tests independently read each record and require their modification revisions to match.
- **Unknown commit:** response loss after the gateway response produces `UNKNOWN_COMMIT`; reconciliation reads the stable receipt with linearizable Range; exact retry recovers without a second generation. A simulated pre-submission loss stays UNKNOWN until exact retry. These are adapter-path observations; the response loss hook is not a physical network fault.
- **Identity:** transition ID is separate from challenge; exact request fingerprint is checked; execution key remains global; same ID with a different envelope is rejected. No ID scope relaxation occurs.
- **Scope boundary:** one effect and a 64 KiB request bound are fixed test limits; etcd default op/request ceilings make unbounded Pass 219 equivalence unproved. The test does not rotate authenticated lifecycle roots and does not test production credentials or an independently administered provider.

An implementation review found that the initial candidate did not compare an outbox key against absence, so a preexisting effect key could be overwritten. The candidate was repaired to include an absence predicate for each effect key, reject duplicate effect identities, and classify an existing key as an effect-ID conflict. A dedicated adversarial test preserves the preexisting bytes and verifies that current state does not advance. The broader integration claim remains OPEN: arbitrary effect size, typed root rotation, provider trust/provisioning, multi-member faults, physical durability, and rollback resistance are unresolved.

Disposition: proceed only to deterministic testing and bounded ephemeral-etcd implementation evidence; label all results NONCLAIM and `IMPLEMENTATION_LEVEL_CONFORMANCE_WITHIN_TESTED_SCOPE` after independent adjudication. No promotion or freeze.

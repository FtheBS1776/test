# Required prior-experience correspondence audit

This is the exact-path audit for the bounded Pass 219-to-etcd implementation subject. Full worksheet, invariants, and internal attack hypotheses are in the top-level `PASS219_TO_ETCD_PRE_DESIGN_AUDIT.md` file delivered with the review. The concise mapping below governs this experiment.

| Experience | Governing lesson | Use here |
|---|---|---|
| L7 | Identity/integrity is not authority; exact predecessor binding; no caller-forged state, truth flag, verifier selection, or privileged evidence; direct construction, same-ID aliasing, structural truncation, and coherent rollback remain attacks. | REUSE. Test fixture provider identity and genesis are expressly non-authoritative. Bind the exact current authority value and preserve all fields. |
| L2 | Separate authority/execution/observation/verification; current-parent consumption and transition receipt are atomic; UNKNOWN uses the same identity; effects reconcile after authority commit; projections need coherence tags. | REUSE. Current value, receipt, execution consumption, and tested outbox intent are one etcd transaction. Delivery is not authority. |
| Genie | Conformance is only to explicit tested contract; environment changes do not generalize. | REUSE. One-member localhost observations support only the bounded implementation subject. |
| EXP-010 | Bind commit/workflow/executable/run/attempt/raw evidence and preserve failure chronology; GitHub is executor/transport. | ADAPT. Manual-only workflow and immutable artifact capture bind each run. Do not import beacon/seed/freshness/one-shot scientific rules. |
| Pass 191 | Fresh challenge-bound authoritative read; challenge and transition ID are different identity domains; only lifecycle-configured linearizable provider may yield CURRENT. | REUSE. Each activation performs a fresh Range with `serializable=false`; its transaction compares that exact value/revision. |
| Pass 194 | Exact state/config compare, atomic successor plus complete receipt, stable ID and fingerprint; unknown commit reconciles by receipt. | REUSE. No second transaction creates idempotency. |
| Pass 195–197 | Authority commits once; outbox/projector work reconciles separately and duplicate sink effects need deduplication. | REUSE. Only intent is in the transaction; delivery is not tested here. |
| Pass 218–219 | In-memory lifecycle split caused a TOCTOU seam; Pass 219 closes the tested local seam by serializing lifecycle binding, registry digest selection, head, execution consumption, receipt, and outbox in SQLite. | ADAPT. Move only the carrier operation to an etcd Compare/Txn. The exact full composition remains unproved. |
| Pass 220–222 | Typed root-transition evidence and dual-threshold reference are later than Pass 219's Boolean fixture outputs. | REUSE as a prerequisite. This experiment does not implement or test root rotation because exact source packages were not recovered in the source set. |
| Pass 223 | Result digest does not warrant a successor state absent a separate contract. | REUSE HOLD; no relation is added. |
| Pass 224 | Global execution-ID uniqueness remains stricter than a trust-domain tuple; no host allocation contract permits widening. | REUSE unchanged; key remains globally scoped. |
| Pass 225 | Lifecycle-bound provider config, linearizable Range, exact Compare/Txn, atomic receipt, same-ID unknown resolution, fail-closed behavior; no whole-world rollback claim. | REUSE unchanged. |
| Pass 226–233 | Genesis/root trust, recovery custody, production administration, and physical durability are separate external HOLDs. | REUSE; not inferred from this test. |

No new authority mechanism is introduced. The one-effect/request-size limits narrow this test subject only; they do not claim to redefine Pass 219's general input contract.

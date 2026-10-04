# Internal attack before external research

The attacked claim is that Pass 219's SQLite lifecycle/registry transaction and Pass 230's separate direct-etcd head/receipt tests can be composed by inference. They cannot: an execution where SQLite rotates lifecycle C→D while etcd retains current C, or where etcd advances a head while local execution-consumption/outbox state remains absent, is compatible with each isolated test suite unless a composed adapter transaction is exercised. This is an integration gap, not a reproduced defect in either subject.

Mandatory attack cases for the new bounded subject:

1. Read under lifecycle C, race a lifecycle change to D before the activation Txn; no stale verifier or old config may win.
2. Mutate each authority field independently: generation, head digest, authority config, lifecycle generation, registry digest, provider-binding digest. Any omitted field can permit stale or wrong-provider state.
3. Present wrong cluster, endpoint/config, malformed authority bytes, missing registry digest, wrong registry bytes, old issuer, or invalid signature; fail closed.
4. Request an empty/replayed challenge, rewrap a cached response in a fresh challenge, or make challenge equal transition ID; no CURRENT or transition may result.
5. Force serializable Range; it may be stale and cannot be authority currentness.
6. Race sibling successors from one parent; exactly one may commit current, receipt, execution consumption, and outbox intent.
7. Lose the Txn response after server commit. A matching stable receipt resolves; missing receipt remains UNKNOWN; exact same-ID retry changes no state; same ID with changed request or envelope rejects.
8. Reuse a global execution ID under another envelope/domain; reject. Do not change the key to a domain-scoped tuple.
9. Inject duplicate mutation keys or oversized effects. Never split one authority transition across multiple Txns.
10. Fail etcd Range/Txn or corrupt its response; no SQLite/cache fallback and no PASS from missing evidence.
11. Restore a coherent old etcd world or remove root custody; remain outside this proof and HOLD.
12. Alter commit/workflow/subject/run/attempt or omit evidence files; treat identity mismatch/incompleteness as INDETERMINATE.

The internal counterexample is therefore preserved: per-package test success is not compositional proof. A single bounded adapter experiment is warranted only because Pass 225 explicitly identifies this missing integration boundary and Pass 219 supplies semantics to reuse.

## Post-cross-attack implementation review

The first code review found a concrete lost invariant: an outbox key was written without an absence Compare, which could overwrite a preexisting effect record. Before any execution, the candidate was repaired to compare outbox absence atomically and return a specific conflict when the key already exists. The test suite seeds that key adversarially and checks its bytes and current authority are unchanged.

The first GitHub-hosted run then exercised the real etcd JSON gateway and falsified two assumptions in the candidate tests: default-valued `count`/`kvs` response fields are omitted for empty Range results, and one injected lifecycle-race fixture invoked a helper on the wrong object. Both are corrected; the original capture remains `INDETERMINATE` and is retained in `RUN_HISTORY.md`. No run is treated as a pass until a clean rerun and independent artifact adjudication.

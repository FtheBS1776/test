# Current primary-source research

Retrieved 2026-10-04 UTC. Sources are official etcd v3.6 documentation, aligned with the already measured Pass 230 etcd v3.6.5 release.

GitHub Actions execution behavior was also checked against official GitHub documentation because it changes how the harness can run without altering the controlling branch: the [`workflow_dispatch` event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch) states that its workflow file must be on the default branch for manual dispatch to appear. The [manual run instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow) confirm the UI behavior. The workflow therefore uses a push trigger restricted to the dedicated NONCLAIM branch; it does not require modifying the default branch.

1. [etcd API](https://etcd.io/docs/v3.6/learning/api/) defines Txn as atomic If/Then/Else over a conjunction of comparisons. Multiple writes from one Txn share one revision. Keys mutated in the success/failure blocks must be unique; one key cannot be changed multiple times in one Txn.
2. [etcd API guarantees](https://etcd.io/docs/v3.6/learning/api_guarantees/) says ordinary KV operations are linearizable by default; serializable reads may be served locally and return stale data. A client may be uncertain after timeout/network disruption, and leader-election interruption may not return an abort response.
3. [etcd gRPC gateway](https://etcd.io/docs/v3.6/dev-guide/api_grpc_gateway/) documents `/v3/kv/range` and `/v3/kv/txn`, including base64 byte keys/values and JSON compare/request forms.
4. [etcd configuration](https://etcd.io/docs/v3.6/op-guide/configuration/) documents defaults `--max-txn-ops=128` and `--max-request-bytes=1572864`; actual provider configuration controls the deployed limits and must be bound and recorded.
5. [Transport security](https://etcd.io/docs/v3.6/op-guide/security/) and [RBAC](https://etcd.io/docs/v3.6/op-guide/authentication/rbac/) describe client TLS, CA trust, optional client-certificate authentication, and etcd V3 API authentication. The Pass 230 harness used one HTTP/no-auth localhost member, so production transport/auth behavior remains untested.

## Cross-check after research

- A single Txn can preserve atomic current/head/receipt/consumption/intent updates only when the request fits actual server limits and each changed key is unique.
- Pass 219 permits unbounded effect counts and payloads; full equivalence is not established. This experiment tests a single small effect and rejects larger lists before submission. It never chunks the transaction.
- `serializable=false` is sent explicitly. The observation is still only meaningful under the lifecycle-authorized provider binding; etcd's returned cluster ID and revision are not independent trust roots.
- A timeout is UNKNOWN. A single absent receipt read is not proof that the original operation cannot later commit. The stable same-ID exact-comparison transaction and receipt are retained; a new logical ID is forbidden.
- Client TLS, authentication, provider provisioning, genesis, recovery/custody, and whole-world rollback are not approximated by local declarations or workflow variables.

No new witness, lease, wall clock, side database, consensus system, or authority registry is justified.

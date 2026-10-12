# Genie Phase 2A controller MCP contract — isolated NONCLAIM

## Surface

The server is local stdio only and exposes exactly one tool:

`advance_run({"run_name": <trusted alias>})`

The tool delegates once to the unchanged, hash-pinned `shared_interfaces/run_control.py` `GenieRunController`. Its annotations are exactly:

- `readOnlyHint: false`
- `destructiveHint: true`
- `idempotentHint: false`
- `openWorldHint: false`

There is no read-only catalog, generic executor, path parameter, HTTP listener, worker/reviewer/model client, callback, `apply_run_event`, or `session_driver` surface.

## Authority and mutation

The trusted registry owns the queue path, run ID, and owned root. The Phase 2A registry contains exactly one fresh synthetic alias. The first call may provision the task ledger and sink, mark the task active, persist one charged reservation and host-call intent, and return a bound `INVOKE_WORKER` action/token. That return is not evidence that a worker was invoked.

No second pilot call is authorized. Tests may exercise reconciliation only in disposable temporary runs.

## Failure semantics

- Unsupported tool, malformed input, extra keys, or unknown alias: deterministic `REJECT` before a progression step.
- Source/dependency/registry incompatibility: fail closed.
- Exception, malformed result, or weakened UNKNOWN after delegation: canonical `UNKNOWN`, `preserve=true`, `allow_new_invocation=false`.
- The adapter and server each delegate at most once per tool call and contain no retry branch.
- UNKNOWN never implies rollback, refund, reset, replacement, safe retry, or new invocation permission.

MCP transport success remains separate from the domain result; `REJECT` and `UNKNOWN` use `isError=false`.

## Explicit exclusions

No existing run mutation, model dispatch, reviewer dispatch, callback/event application, delivery, promotion, freeze, main merge, payment, remote deployment, background execution, global atomicity, rollback-resistance, independence, or EXP010 activity is authorized or claimed.

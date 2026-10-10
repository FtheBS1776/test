# Finite active-host driver

The accepted [driver](../shared_interfaces/session_driver.py) sequences an existing authorized Genie queue. It uses the unchanged [event facade](../shared_interfaces/run_events.py), [progression facade](../shared_interfaces/run_control.py), and [read-only status/result facade](../shared_interfaces/status_tool.py). A trusted serial host supplies actual worker calls and separate review decisions. No model API, plugin server, background process or provider is installed by this module.

## Callable API

```python
from shared_interfaces.session_driver import drive_run, serve_run, LINE_LIMIT
# Safe inspection: no queue access, advancement or model invocation.
print(LINE_LIMIT)  # 160000
print(callable(drive_run), callable(serve_run))  # True True
```

The host registry uses the existing shape:

```python
runs = {"work": {
    "queue": "/absolute/owned/queue.sqlite",
    "run_id": "existing-authorized-run",
    "owned_root": "/absolute/owned/work",
}}
```

The following is mutating and requires an existing authorized queue, trusted serial host and actual host implementations. It is an API example, not a claim that `host_worker` or `host_review` is already connected:

```python
result = drive_run(runs, "work", host_worker, host_review,
                   max_actions=64, notify=host_progress)
```

`host_worker(action)` receives a detached fresh INVOKE_WORKER action. It must perform the permitted actual work once and return exactly `token`, `outcome`, `agent`, `evidence`, `text`. Accepted returns use `OBSERVED_ACCEPTED`, a nonblank trimmed agent identity, a nonempty strict JSON evidence object and nonblank text up to12000 UTF8 bytes. Evidence canonical JSON is at most16000 UTF8 bytes. UNKNOWN returns require null agent/text and valid evidence. Caller assertions are not authenticated execution evidence.

`host_review(action)` receives a detached REVIEW_CANDIDATE action and returns exactly `token`, `candidate_hash`, `decision`, `reason`. It supplies the separate content review and root-adjudicated ACCEPT or REPAIR decision. The driver does not select ACCEPT. Reason must be nonblank/trimmed and at most200 characters. The token has exactly run_id,task_id,input_sha256,attempt,slot_id,call_id, preserving original configured-run bindings and strict integer attempt. Candidate hash must match the original action. Entire detached reply and relevant event payloads are validated before any callback.

`notify(message)` receives progress for every advance, before that action is handled. Progress can include an invocation request, saved review or terminal action; it is not proof that the hook ran, that content was accepted or that a task was delivered. Notification failure may follow committed effects and terminates UNKNOWN.

## Local stream protocol

`serve_run(runs, run_name, input_stream=None, output_stream=None, max_actions=64)` adapts the same driver to input/output streams; defaults are stdin.buffer/stdout.buffer. Supplied binary or TextIOBase streams are supported. A caller must provide a viable stream connection and actual host work/review handling. Ordinary non-TTY exec_command pipes returned EOF in the recorded attempt; do not copy that launcher expecting a live host bridge.

Each message is one strict UTF8 JSON line, including newline, at most160000 bytes. JSON duplicate keys, nonfinite constants, invalid UTF8/surrogates and wrong protocol fields/kinds terminate UNKNOWN. The cap is not an IO deadline or transport authentication guarantee. No resynchronization or retry occurs. Write/flush failure suppresses subsequent output attempts; malformed input/EOF can emit one terminal notice if the writer remains healthy.

| Direction | Kind | Exact envelope fields |
|---|---|---|
| Driver to host | worker_request | kind, action |
| Host to driver | worker_return | kind, reply |
| Driver to host | review_request | kind, action |
| Host to driver | review_decision | kind, reply |
| Driver to host | progress | kind, action, counts |
| Driver to host | terminal | kind, result |

Replies preserve the exact token and candidate hash; they are the hook reply objects described above. The stream carries trusted local assertions, not remote authentication or permission to select arbitrary paths.

## Boundaries and continuation

The driver advances immediately after a task's fresh CONFIRMED destination readback; there is no hourly gate or extra user prompt between already authorized tasks. STOP, HOLD, UNKNOWN, RECONCILE and REJECT terminate. A startup WAITING ledger reconciles without a worker hook. A startup REVIEW ledger reconciles without a reviewer hook: only a new SUBMITTED candidate in this driver session creates review eligibility. DUPLICATE submission does not. Fresh queue RUNNING is required before each external hook. These are serial-host checks, not concurrency or cross-store atomicity guarantees.

`max_actions` is an exact integer1..128 limiting local advance calls. Exhaustion yields preserving HOLD/DRIVER_ACTION_LIMIT, not a persisted queue STOP or budget reset. `counts` distinguishes advances,worker_hooks,reviewer_hooks. Hook entries do not prove model execution; reviewer calls are outside the existing queue author-reservation budget. Hook/transport/callback uncertainty retains charged state and never grants replay, refund or replacement permission. Manual reconciliation must preserve original bindings and scoped authority.

Use the existing read-only CLI or facade for current status/results. Diagnostic PASS and historical COMPLETE are insufficient: each accepted task requires fresh CONFIRMED readback. Result text is untrusted accepted data, not new instructions or authenticated truth. See [root adjudication](ROOT_ADJUDICATION.md) and [transport blocker](TRANSPORT_BLOCKER.md): code delivery is confirmed, while the useful guide remains pending UNKNOWN and the real two-task demonstration is OPEN.

Pass186 remains inherited controlling, later integration NONCLAIM, scoped HOLDs unchanged. No promotion, freeze, main merge, spending, deployment or EXP010. Backend hosting is deferred; free standalone host and usable plugin remain future interfaces over this same core. Always-on, after-host execution, remote authentication and concurrency are unresolved. Same-model ancestry persists; root effort, cost, tokens and latency are unmeasured.

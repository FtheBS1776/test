# Active-host runner integration review plan

## Scope and reviewed foundation

Read checkpoint README_FIRST.md and GENIE_CONTINUATION_NOTES.md first, then current run_queue/run_policy.py, host_adapter/journal.py and worker_bridge/bridge.py. This is same-model/shared-ancestry review, not independent proof. No provider fixture or old suite was executed. runner.py was not present when this plan was drafted; exact runner subject and source findings will be appended after inspection. Planned tests below are recommendations, not executed results.

The authorized wrapper should reduce host plumbing while preserving finite host lifetime, bounded plan/reservation policy, controller-owned model invocation, separate content review and fresh destination confirmation. No closed-run reset, spending, deployment or promotion is implied. Existing root/custody, rollback, physical durability, remote authenticity and hostile-worker isolation HOLDs remain scoped.

## Concrete attacks and expected boundaries

| Case | Attack or interruption | Required observation | Prior correspondence |
|---|---|---|---|
| A1 | Feed callback for another run with same task/request and locally equal slot/call hashes | Reject before any ledger mutation; explicit run plus task/input/attempt/call context | L7 cross-context alias, immutable execution/input binding |
| A2 | Wrong agent, stale attempt, altered candidate bytes or hash; duplicate matching text across tasks | Reject misrouting; exact replay may be diagnostic duplicate only | L7 same-ID alias; content versus execution identity |
| A3 | Crash after task request but before queue reservation | Resume unfinished request with no reset; reserve exact request once within budget | L2 intent persistence; UNKNOWN is not success |
| A4 | Crash after reservation but before journal begin | Reservation remains charged; classify launch evidence correctly, never infer no call solely from null agent | L2 uncertainty, cross-store gap; no global transaction claim |
| A5 | Crash after journal begin or actual invocation before saved callback | Reconcile existing invocation; never return a fresh invocation permission on replay | L2 at-most-one permission and UNKNOWN; host lifetime limits |
| A6 | Stop run at each dispatch gap, then tick or replay callback | No new invocation after stop; existing observations may reconcile without reopening run | L2 authorization versus observation |
| A7 | Submit valid-looking callback without journal call/reservation or with altered feedback | Reject; match full persisted request and run/slot context | L7 request binding; queue authorization not supplied by text |
| A8 | Repeat exact accepted callback after candidate reaches REVIEW, ACCEPTED, or another attempt | Defined idempotent historical acknowledgement or explicit stale rejection; never attach to current attempt | L7 stale execution; L2 receipt versus current state |
| A9 | Worker claims DONE/ACCEPT; callback contains review-shaped fields | Remain at controller review; content correctness requires separate adjudication | L2 worker output is observation, not authority |
| A10 | ACCEPT then sink commit/lost reply; restart wrapper | Retry same exact effect, deduplicate, reread sink; no new model request | L2 atomic intent/effect separation and stable effect ID |
| A11 | Remove/change sink after DELIVERED/COMPLETE | Currentness remains UNKNOWN or mismatch; history not rewritten, no implicit provisioning | Pass212 typed observation not remote truth; L2 cached status limits |
| A12 | Exhaust budget during repair; mark one task HOLD while another independent task is READY | No extra reservation; skip scoped HOLD only when independent authorized budget remains | Bounded continuation; scoped HOLD |
| A13 | Concurrent ticks/callbacks | At most one fresh invocation permission and one candidate/effect; races reconcile or cleanly reject | SQLite local atomicity only; L2 separate ledgers |
| A14 | Missing/empty/partial queue, journal schema, task ledger or setup mapping | Preserve and inspect; never silently recreate a destination or repopulate lost history | L2 UNKNOWN; provisioning/action separation |
| A15 | Duplicate task directory, traversal task ID, symlink or changed task-to-path mapping | Owned configuration maps to exact task; no accidental ledger alias or writes outside run root | L7 concrete subject/path binding; not hostile isolation claim |
| A16 | Tick auto-loops REVIEW/HOLD/UNKNOWN or recreates successor run after closure | Bounded return with explicit next action/stop reason; no invented model capability or endless continuation | Genie smallest useful core; authority/budget/dependency boundaries |

## Proportional test approach

Use fresh disposable local ledgers and focused wrapper tests; no completed provider/etcd experiments are needed. Inject interruption at wrapper boundaries using stubs or controlled exceptions, retain state, then invoke a fresh process for recovery. Count reserved calls, host permission emissions, actual fake-host invocations, candidate versions and sink applications separately. Verify negative cases leave authoritative/task records unchanged except intentionally recorded uncertainty. Test a useful accepted candidate path plus one actual repair path, not only rejection helpers. Do not label stubs as live-model execution.

Source hashes, exact commands and observations should bind tested revisions; a reviewer finding in the original source is not independent verification of a later repair. Root retains controller adjudication and decides any amendment. No library/source publication or new operation is authorized by this plan.

## Exact runner source review

Inspected `active_runner/runner.py` SHA-256 `5847cadddd38e265418fea6ec742e7743f41f6f6873eb8eac66526c38edc6cf8`. This is source-level reasoning only; no runner, dependency suites or provider experiments were executed. Later edits require a distinct subject hash and review/testing evidence.

### Findings

**F1 — Safe refusal leaves two setup gaps unresolved by this wrapper.** After `b.request()` commits WAITING_WORKER but before `q.reserve()` commits, a restart enters WAITING_WORKER and immediately calls `token()`. The missing reservation raises RESERVATION_REQUEST_BINDING. After a reservation commits but before `j.begin()`, restart similarly raises CALL_SLOT_BINDING. Both are returned as generic UNKNOWN; no wrapper path emits a context-rich setup reconciliation action or progresses the preserved request. This does not permit duplicate invocation, but limits the intended reduction in manual continuation plumbing. Preserve state, identify the precise missing stage and return an explicit next reconciliation action. Any automatic completion of a missing stage needs a justified serial-host ownership rule; null agent alone never establishes no launch.

**F2 — Exhausted reservation budget is mislabeled host reconciliation.** In READY/REPAIR_READY, `b.request()` first persists a new attempt. If `q.reserve()` returns STOP/CALL_BUDGET_EXHAUSTED, `step()` treats every non-RESERVE_ONCE outcome identically and returns RECONCILE_HOST/NO_NEW_INVOCATION_PERMISSION. There is no journal call to reconcile. On another step the unreserved current attempt triggers F1 instead of returning the actual stop reason. Surface STOP and its persisted reason directly, while preserving the unfinished attempt; distinguish a prior reservation from budget denial. This is an actionable status defect, not an observed unauthorized launch.

**F3 — Callback idempotence ends when the queue completes or the attempt changes.** `callback()` requires the current `token()`, whose queue entry state must be ACTIVE/HOLD. Replaying the exact observation after TASK_COMPLETE therefore rejects before the journal can acknowledge its saved duplicate. An old exact observation likewise rejects after a repair attempt advances. That is conservative, but narrower than the underlying journal's historical replay contract. Either document the wrapper's stale-callback rejection policy or provide a strictly read-only historical duplicate acknowledgement keyed to full run/task/input/attempt/call/slot context. Never rewrite it onto the current attempt.

**F4 — WAITING diagnostics must honor journal inconsistency.** WAITING_WORKER returns RECONCILE_WORKER with a computed token even if `j.status()` says UNKNOWN/PRESERVE_AND_INSPECT because observation or agent records disagree. `allow_new_invocation` is correctly false, and submit/review gates reject unknown host evidence. Nevertheless, the host must consume the nested status rather than interpret the outer action as permission to resume an identified worker. Prefer promoting inconsistent-journal action to the outer response. Test corrupted event hash and agent mismatch. This is a diagnostic boundary, not a demonstrated acceptance bypass.

### Positive boundaries inspected

- Explicit run context plus task/input/attempt/slot/call token rejects common callback misrouting; hashed path components avoid raw task-ID traversal.
- Existing partial provisioning is preserved; ledger plan, host schema and sink schema are checked before workflow actions.
- A stopped ACCEPTED task does not call `b.deliver()`. It only asks queue completion to observe existing destination state; absent application stays unresolved. Existing DELIVERED state is also re-observed.
- Worker observations and candidate submission remain separate from controller review. REVIEW checks candidate bytes/hash and accepted journal evidence; ACCEPTED/DELIVERED check host evidence before completion.
- The file explicitly scopes execution to a serial active host. No concurrent-host guarantee follows; test concurrent use only to define rejection/operational limits, not invent distributed-scheduler acceptance requirements.

### Focused tests for root

1. Inject an exception immediately before reserve, restart, and assert no invocation permission plus preservation of request/zero reservation; verify the repaired action names the gap.
2. Inject immediately before journal begin, restart, and assert one charged reservation/no new permission; verify exact preserved request and explicit reconciliation.
3. Accept a REPAIR decision at the remaining-budget boundary; assert persisted STOP/CALL_BUDGET_EXHAUSTED is returned consistently and no host call is created.
4. Stop after candidate ACCEPT but before delivery. Assert zero sink applications; separately pre-apply the exact effect and assert stopped reconciliation may record historical completion without another application.
5. Replay exact observe/submit/review callbacks after REVIEW, repair advancement and COMPLETE; record the intended read-only duplicate versus explicit stale rejection policy.
6. Corrupt an event hash or journal/attempt agent agreement; assert outer response requires preservation/inspection and no candidate acceptance or delivery follows.
7. Cross-wire identical task/request text between distinct runs and alter one token field at a time; assert no ledger mutation. Exercise full useful path with actual content review separately from callback validity.

These tests are proposed, not run. Source integrity and local atomic transactions do not establish independent production authority, remote authenticity, rollback resistance or hostile-worker confinement.

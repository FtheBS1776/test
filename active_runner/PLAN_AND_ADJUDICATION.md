# Plan, reuse and adjudication scope

Authorized next unit from canonical continuation: reduce repeated queue/journal/bridge plumbing and use it on one useful bounded task. Prior two-task queue run is closed and remains untouched. This unit has an explicit new plan: one read-only status CLI task, at most two workflow reservations/attempts. Source review is separately recorded, not disguised as a workflow reservation. No automatic successor run.

| Responsibility | Treatment |
|---|---|
| Task selection, scoped HOLD and reservation budget | Reuse run_queue/run_policy.py unchanged, pinned source |
| Logical attempt/candidate/review/effect identity | Reuse worker_bridge/bridge.py unchanged |
| Host call uncertainty and observation/agent binding | Reuse host_adapter/journal.py unchanged |
| Observable effect and deduplication | Reuse existing owned report inbox unchanged |
| Active host model execution | Existing collaboration interface; root executes fresh permission |
| Repetitive setup/next-action/callback routing | Small new runner wrapper; no new authority source |
| Useful operator diagnostics | Worker authors read-only status candidate; root inspects/tests/adjudicates |

Before implementation root verified preceding checkpoint against its saved SHA256;39 payload hashes/size/paths/CRC passed. Existing roadmap already incorporates approved amendment. Review plan applies L7 cross-context/content/execution aliasing, L2 UNKNOWN/authority/observation separation and Pass212 sink readback limits. Prior primary SQLite/Python research remains applicable; no new library/version/protocol or distributed concurrency/storage assurance is adopted. Separate transactions cannot be promoted into a global transaction by wrappers. No old provider, timing or sink-loss experiment is repeated.

Original runner review subject is saved in source_v1/runner.py and REVIEW_PLAN.md. Root adjudicated F1 by explicitly naming setup gaps without automatic completion/relaunch; F2 by returning persisted budget STOP; F3 by documenting conservative terminal/stale callback rejection; F4 by promoting inconsistent journal evidence to outer UNKNOWN/preserve. Revised code is covered by root targeted integration checks, not retroactive original-source review. Source-level revised worker review is separately saved. Deterministic tests check routing/state/sink obligations; they do not prove arbitrary candidate text correct.

Remaining limits: serial trusted host and filesystem; no globally atomic operation across stores; interrupted provisioning/setup requires bounded investigation. Ordinary SQLite transactions and release tests are baseline engineering, not measured unique Genie gains. No comparative latency/token/money measurements are exposed. Worker and reviewer share model/ancestry with controller; role count does not establish independence. Host termination does not create background progress.

## Actual useful task result

Run genie-active-runner-20261008 completed genie-run-status-20261008 on first attempt:1 workflow reservation/observed worker call,1 actual destination application, fresh subprocess readback CONFIRMED and persisted ALL_TASKS_COMPLETE. One initial source-review worker turn was separate; revised-source review accompanied the useful code task. No extra user continuation prompt within unit. Role/model ancestry shared; no independent-proof claim.

Worker candidate af0fdad950a7d1849ea04d5e3670acffde5d1bf4c4e9468017a29c70047327cf was inspected before execution and accepted unchanged after14 root checks. It uses explicit mode=ro/query_only transactions, reuses pinned runner paths/queue control/bridge effect validation/sink observer and mirrors the pinned journal's small consistency check because the existing journal status helper opens mode=rw. This diagnostic copy is not a new authority or acceptance implementation; dependency hash changes require deliberate review. Top-level PASS means diagnostic completed, not that every store/effect is confirmed. Per-task UNKNOWN/MISMATCH is preserved separately. No payload, candidate or evidence body is displayed.

Root32 runner checks cover exact callback identity/replay, wrong run/agent/hash, actual stubbed request/reservation/journal interruptions, corrupt records, repair budget exhaustion, stopped delivery/readback and preserved partial stores. These are local controller fixtures, not live-model calls. Actual useful task had one model call; source review is counted separately. DB byte hashes unchanged before/after actual fresh status command. Detailed records and original source review remain in evidence.

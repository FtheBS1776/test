> Current source candidate: selected reuse from fa4e291cfd1aa7147f39f359008f8d74a2f69798. Imports and transitive source pins are reconciled; queue policy validation is reused, and stop is exposed without a model. Use `python -m standalone_app.cli` from the repository root. Native publication and current composition evidence are named in the root README; Linux injection alone never establishes Windows coverage.

# Minimal standalone Genie owner — NONCLAIM contract

## Purpose

Compose the already accepted canonical-state provisioner and shared Genie core into the first local standalone-owner surface. This is an owner/lifecycle layer, not a second reasoning engine.

The unit supports only:

1. creating the **first new canonical run** from trusted local policy/task data;
2. reading its existing Genie status;
3. advancing the existing Genie controller by exactly one governed step;
4. stopping future dispatch through the existing queue without invoking a model.

No model/provider is invoked by this unit. If the existing controller returns `INVOKE_WORKER`, that is an action/request for a later host/provider adapter; it is not executed here.

## Dependency / authority chain

The owner does not depend on the MCP/plugin projection and does not import mutable core semantics by filename without verification. It exact-byte pins the existing transport-neutral `run_control.py`, which then retains its already accepted internal source-binding chain:

`run_control.py` (exact SHA-256) -> `status_tool.py` -> `run_status.py` -> `runner.py` -> queue/journal/bridge/reused core.

This layering is intentional: the standalone owner and plugin are sibling interfaces over one core; neither interface depends on the other.

The canonical-state namespace is acquired only through `canonical_state_provisioner.begin()`.

No alternate queue, ledger, worker, reviewer, completion, or STOP semantics are introduced.

## First-run creation

`create_first_run(spec)` accepts one strict detached JSON-like object with exactly:

- `run_name`: trusted local alias string;
- `policy`: the existing queue policy object;
- `plans`: nonempty list of existing Genie task-plan objects.

It accepts **no filesystem path** and no provider/model configuration.

Before acquiring the one-shot staging witness, the owner performs a bounded deterministic precheck. Plan validation delegates to the existing pure queue validator. Policy precheck reuses the existing queue's pure `valid_policy` validator; `initialize` remains authoritative once staging is acquired.

Creation sequence:

1. load the exact accepted transport-neutral controller/core chain;
2. precheck run alias/policy and validate every plan;
3. acquire the fixed canonical staging capability from the accepted provisioner;
4. create fixed direct children `queue.sqlite` and `work` inside staging;
5. initialize the existing queue with the supplied policy;
6. enqueue each validated plan through the existing queue API;
7. write the fixed `REGISTRY.json` mapping the supplied alias to `queue.sqlite`, the policy run ID, and `work`;
8. re-open/validate the initialized queue through existing runner context/status semantics;
9. publish once through the accepted canonical provisioner;
10. re-open through the accepted fixed-root live-state binder and require exact alias/run binding plus a real existing Genie status read.

After staging acquisition, any creation failure is preserve-only. The owner does not remove staging, retry creation, substitute a different run, or silently repair partial state.

After publication, any live-binding/status verification failure is `OWNER_PUBLISHED_UNVERIFIED_PRESERVE`; the canonical root is not recreated or replaced.

## Status

`status(run_name)` loads the fixed canonical live-state registry and delegates to the existing `GenieStatusTools.get_run_status` semantics. It adds no completion inference and does not transform UNKNOWN/MISMATCH.

## One-step advance

`advance(run_name)` loads the fixed canonical live-state registry and delegates exactly once to the existing `GenieRunController.advance_run` surface.

The owner does not loop, retry, invoke a model, apply a callback, review a candidate, or reinterpret the returned action. Existing `INVOKE_WORKER`, `REVIEW_CANDIDATE`, `RECONCILE_*`, `STOP`, `UNKNOWN`, and HOLD semantics remain intact.

The returned `INVOKE_WORKER` token/request is data for a future separately reviewed provider/host adapter. This unit grants no network/model authority.

## CLI

A minimal local CLI exposes `create`, `status`, `advance`, and `stop`. `create` reads its strict creation object from stdin; no pathname argument is accepted. `status`/`advance` accept only a run alias.

Unexpected failures after owner entry are UNKNOWN with preservation/no-new-invocation flags and exit 3, including a lost acknowledgement after a committed stop. Malformed stdin/arguments reject before entry; known deterministic owner rejections remain REJECT. Stdin decoding reuses the maintained strict registry parser helpers.

The CLI is an engineering owner shell, not the final GUI/installer. It is intended to prove that the shared core can be operated without this chat before model-provider integration is added.

## Nonclaims

This unit does not establish:

- migration/import of historical user state;
- creation on the user's physical machine;
- creation of additional runs after the first canonical root exists;
- pause/resume semantics;
- model/provider dispatch;
- autonomous continuation after `INVOKE_WORKER`;
- authenticated remote worker identity;
- rollback/currentness or crash-durability guarantees;
- hostile local-user confinement;
- plugin installation/connection;
- final GUI/installer/production readiness;
- authority promotion, freeze, main merge, or EXP010 execution.

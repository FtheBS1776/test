# Minimal standalone Genie owner — NONCLAIM contract

## Purpose

Compose the already accepted canonical-state provisioner and shared Genie core into the first local standalone-owner surface. This is an owner/lifecycle layer, not a second reasoning engine.

The unit supports only:

1. creating the **first new canonical run** from trusted local policy/task data;
2. reading its existing Genie status;
3. advancing the existing Genie controller by exactly one governed step.

No model/provider is invoked by this unit. If the existing controller returns `INVOKE_WORKER`, that is an action/request for a later host/provider adapter; it is not executed here.

## Dependency / authority chain

The owner does not import mutable core semantics by filename and trust them implicitly. It loads the already accepted source chain through the same exact-byte bindings used by the MCP path:

`mcp_consumer.py` (exact SHA-256) -> `function_adapter.py` -> `run_control.py` -> `status_tool.py` -> `run_status.py` -> `runner.py` -> queue/journal/bridge/reused core.

The canonical-state namespace is acquired only through `canonical_state_provisioner.begin()`.

No alternate queue, ledger, worker, reviewer, completion, or STOP semantics are introduced.

## First-run creation

`create_first_run(spec)` accepts one strict detached JSON-like object with exactly:

- `run_name`: trusted local alias string;
- `policy`: the existing queue policy object;
- `plans`: nonempty list of existing Genie task-plan objects.

It accepts **no filesystem path** and no provider/model configuration.

Creation sequence:

1. load the exact accepted Genie core chain;
2. validate run alias, policy and every plan using existing core validators;
3. acquire the fixed canonical staging capability from the accepted provisioner;
4. create fixed direct children `queue.sqlite` and `work` inside staging;
5. initialize the existing queue with the supplied policy;
6. enqueue each validated plan through the existing queue API;
7. write the fixed `REGISTRY.json` mapping the supplied alias to `queue.sqlite`, the policy run ID, and `work`;
8. re-open/validate the initialized queue through existing runner context/status semantics;
9. publish once through the accepted canonical provisioner;
10. re-open through the accepted fixed-root live-state binder and require exact alias/run binding.

After staging acquisition, any creation failure is preserve-only. The owner does not remove staging, retry creation, substitute a different run, or silently repair partial state.

## Status

`status(run_name)` loads the fixed canonical live-state registry and delegates to the existing `GenieStatusTools.get_run_status` semantics. It adds no completion inference and does not transform UNKNOWN/MISMATCH.

## One-step advance

`advance(run_name)` loads the fixed canonical live-state registry and delegates exactly once to the existing `GenieRunController.advance_run` surface.

The owner does not loop, retry, invoke a model, apply a callback, review a candidate, or reinterpret the returned action. Existing `INVOKE_WORKER`, `REVIEW_CANDIDATE`, `RECONCILE_*`, `STOP`, `UNKNOWN`, and HOLD semantics remain intact.

The returned `INVOKE_WORKER` token/request is data for a future separately reviewed provider/host adapter. This unit grants no network/model authority.

## CLI

A minimal local CLI may expose `create`, `status`, and `advance` only. `create` reads its strict creation object from stdin; no pathname argument is accepted. `status`/`advance` accept only a run alias.

The CLI is an engineering owner shell, not the final GUI/installer. It is intended to prove that the shared core can be operated without this chat before model-provider integration is added.

## Nonclaims

This unit does not establish:

- migration/import of historical user state;
- creation on the user's physical machine;
- pause/resume semantics;
- model/provider dispatch;
- autonomous continuation after `INVOKE_WORKER`;
- authenticated remote worker identity;
- rollback/currentness or crash-durability guarantees;
- hostile local-user confinement;
- plugin installation/connection;
- final GUI/installer/production readiness;
- authority promotion, freeze, main merge, or EXP010 execution.

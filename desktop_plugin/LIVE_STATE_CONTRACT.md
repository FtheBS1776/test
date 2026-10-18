# Genie Desktop live-state binding contract — NONCLAIM

## Purpose

Bind the local read-only Desktop plugin to one existing Genie-owned Windows state root without copying authoritative stores into plugin cache, accepting a model-supplied pathname, or requiring ongoing synchronization.

This unit does not create Genie state, migrate old state, mutate a run, install a plugin, or grant new authority.

## Fixed Windows root

The plugin derives the current user's `FOLDERID_LocalAppData` with the Windows Known Folder API and appends the fixed components:

`GenieReasoningEngine/state-v1`

The production path is therefore selected by the operating system plus fixed owned names. It is not read from model/tool input, ambient `%LOCALAPPDATA%`, a plugin manifest variable, or `PLUGIN_DATA`.

The resolved state root must remain under the resolved `FOLDERID_LocalAppData` path. Missing, partial, malformed, or escaping state is rejected. The plugin never creates or repairs this root.

## Required root records

The state root must contain these exact direct children:

- `GENIE_STATE.json`
- `REGISTRY.json`

`GENIE_STATE.json` must be a strict JSON object with exactly:

```json
{"format":"GENIE_LOCAL_STATE_V1","registry":"REGISTRY.json","scope":"GENIE_OWNED_LOCAL_STATE"}
```

The marker is a format/binding guard, not cryptographic authenticity or rollback/currentness proof.

## Registry confinement

`REGISTRY.json` retains the existing Genie registry schema and is parsed by the existing strict registry parser. This binding layer adds Windows-local confinement before any Genie store read:

- aliases must be nonempty trimmed strings of at most 200 characters;
- each record remains exactly `queue`, `run_id`, and `owned_root`;
- `queue` and `owned_root` must each be a safe direct-child name, not an absolute or multi-component pathname;
- slash, backslash, colon, NUL, `.`/`..`, trailing dot/space, and Windows reserved device basenames are rejected;
- the resolved queue and owned-root targets must remain direct children of the resolved fixed state root;
- queue must be an existing regular file and owned_root an existing directory;
- the paths produced by the existing registry parser must exactly match the independently confined resolved targets.

This prevents configuration from turning the read-only MCP surface into arbitrary-path filesystem authority. It does not claim hostile-filesystem race resistance after validation; existing Genie trusted-owned-local assumptions remain controlling.

## Plugin storage

`PLUGIN_DATA` is not an authoritative Genie state replica in this design. The live read-only process does not seed, copy, merge, repair, or synchronize Genie state into it. Plugin updates therefore do not create a second currentness domain.

A compatible host may still create `PLUGIN_DATA` as required by Agent Plugins; this unit simply leaves it outside Genie authority.

## Runtime behavior

A valid live binding returns detached absolute run records to the existing accepted read-only MCP consumer/server. The exposed tools remain exactly:

- `get_run_status`
- `get_task_result`

No setup/bind/import pathname tool is added to MCP.

Missing or invalid live state terminates the local MCP process with a fixed non-sensitive reason code. There is no fallback to the bundled historical fixture and no automatic retry/repair permission.

## Limits

This contract establishes deterministic Windows-local path selection and bounded configuration confinement only. It does not establish source authenticity, hostile local-user confinement, rollback resistance, custody continuity, remote authenticity, code-signing trust, installation compatibility, production readiness, promotion, freeze, main merge, or EXP010 execution.

Provisioning/migrating real user state into the fixed root remains a separate later unit. Actual ChatGPT Desktop installation/connection remains a separate explicit user action after live binding is verified.

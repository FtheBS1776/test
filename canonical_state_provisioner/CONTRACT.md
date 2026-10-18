# Canonical Windows state provisioner contract — NONCLAIM

## Purpose

Provide the future trusted standalone Genie owner with a one-time capability to construct and publish the shared canonical Windows local state root consumed by the already accepted read-only Desktop binding.

This unit is **not** an MCP tool, model-callable setup API, legacy-state importer, synchronization service, recovery service, installer, or currentness/rollback authority.

## Prior-experience correspondence

This design preserves the inherited L2/L7 filesystem and transition lessons:

- authority, execution, observation, and verification stay separate;
- arbitrary caller/model pathnames are not authority;
- a fixed owned namespace plus exact direct-child names is preferred to caller-selected paths;
- interrupted provisioning is evidence to preserve, not permission to replay or silently finish;
- commit visibility is not crash-durable currentness;
- UNKNOWN/uncertain commit outcomes do not authorize automatic retry, overwrite, cleanup, or replacement;
- Windows conclusions are platform-specific and are not generalized to Linux/macOS.

External correspondence used for this design:

- Microsoft documents `MoveFileEx` for moving directories and requires the destination directory not already exist; directory moves remain on the same drive.
- Microsoft documents reparse points as a source of nonordinary filesystem behavior and provides explicit reparse-point handling primitives.
- Microsoft strongly recommends alternatives rather than new dependencies on Transactional NTFS (TxF).
- MIT crash-consistency work illustrates that application-visible rename/atomicity and post-crash durability are distinct properties; this unit therefore makes no power-loss durability/currentness claim.

## Fixed namespace

The provisioner uses the same Windows Known Folder binding as the read-only plugin:

`FOLDERID_LocalAppData / GenieReasoningEngine`

Within that app directory:

- final canonical root: `state-v1`
- fixed staging witness: `.state-v1.init`

No caller supplies or overrides these names.

The app directory may be created by this unit if absent. If it already exists it must resolve as the exact fixed direct child of the Known Folder root and must not itself be a Windows reparse point.

The final canonical root and staging witness are never replaced.

## Begin semantics

`begin()` performs only namespace acquisition:

1. derive the Known Folder base;
2. validate/create the fixed `GenieReasoningEngine` app directory;
3. reject if `state-v1` already exists;
4. reject if `.state-v1.init` already exists;
5. create `.state-v1.init` with exclusive directory creation;
6. validate that the created staging object is an ordinary directory, not a reparse point;
7. return an in-process `ProvisioningSession` owned by the trusted local host.

A fixed staging name deliberately acts as a cross-process exclusion/interruption witness. Two concurrent `begin()` calls cannot both obtain the same staging directory. A later process that sees a pre-existing staging directory does not delete, merge, resume, or overwrite it.

The session may expose its staging path to the trusted local Genie core so the core can create its own queue/work stores. This is an in-process owner capability, not a serializable remote authorization token and not an MCP/model argument.

## State population

This provisioner does not import from another filesystem path. It does not copy a repository fixture into production state. It does not accept arbitrary source paths.

The trusted owner/core is responsible for populating the staging root with the existing Genie registry/store format. Before publish:

- `GENIE_STATE.json` must not already exist; the marker is provisioner-owned;
- the registry and configured direct-child queue/root bindings must pass the same structural/confinement validation used by the read-only live-state binder, with marker validation temporarily omitted;
- malformed/incomplete staging state is preserved and publish fails closed.

## Publish semantics

`session.publish()` takes no pathname argument.

The operation:

1. revalidates the exact app/staging objects and rejects reparse substitution;
2. requires final `state-v1` still be absent;
3. validates staging registry/direct-child bindings without a marker;
4. creates the exact `GENIE_STATE.json` marker exclusively in staging and flushes that marker file;
5. validates the complete staging root including the marker;
6. calls `MoveFileExW(staging, final, MOVEFILE_WRITE_THROUGH)` with **no replace-existing flag**; source and destination share the same parent/volume;
7. on reported success, validates the final canonical root and returns a non-authorizing publication record.

The record is local setup evidence only. It is not a receipt proving rollback resistance, custody continuity, power-loss durability, or external authenticity.

## Failure and retry rules

Before staging is created, deterministic validation failures may be corrected by the owner and `begin()` may later be called again.

After `.state-v1.init` has been created, the provisioner never automatically removes it on error. A failed/aborted/crashed population leaves the staging witness for explicit inspection.

If `MoveFileExW` does not report success, the result is `PUBLISH_UNKNOWN_PRESERVE`. The provisioner does not retry, replace, delete staging, delete final state, or infer rollback.

If the move reports success but post-publish validation fails, the result is `PUBLISHED_UNVERIFIED_PRESERVE`. The provisioner does not roll back or republish.

A later `begin()` rejects whenever either final state or a staging witness exists. Recovery/adjudication is a separate future mechanism.

## Reparse / hostile-local limits

This unit rejects reparse points at the fixed app/staging/final boundaries and relies on the live-state binder's direct-child validation for required state entries. This narrows accidental/path-aliasing failures.

It does **not** claim confinement against a hostile local principal racing namespace objects after validation. Strong hostile-local Windows confinement would require a separate handle/ACL/threat-model design and remains outside this NONCLAIM unit.

## Nonclaims

This unit does not establish:

- migration of the user's existing historical Genie state;
- power-loss durable all-or-nothing multi-file state creation;
- rollback/currentness resistance;
- root/custody continuity;
- hostile local-user confinement;
- remote authenticity;
- plugin installation or ChatGPT connection;
- autonomous model dispatch;
- production readiness, promotion, freeze, main merge, or EXP010 execution.

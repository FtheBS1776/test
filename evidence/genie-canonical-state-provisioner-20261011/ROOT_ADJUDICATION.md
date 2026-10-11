# Root adjudication — Genie canonical Windows state provisioner

Disposition: **ACCEPT_NONCLAIM_CANONICAL_STATE_PROVISIONER**

Accepted subject: the trusted-local Windows fixed-namespace provisioner at exact tested commit `250e9c237ef0fe1c9cfade8cccb900e05a0c7e38`, workflow run `38173150758`, job `114569836417`.

## Accepted narrow conclusions

- The provisioner adds no third-party runtime dependency and is not exposed through MCP, model input, CLI pathname arguments, or `PLUGIN_DATA`.
- It derives the same fixed `FOLDERID_LocalAppData/GenieReasoningEngine` namespace used by the accepted read-only live-state binder.
- It acquires exactly one fixed staging witness, `.state-v1.init`, with exclusive directory creation; concurrent or abandoned staging is preserved rather than cleaned/replayed.
- It never replaces an existing final `state-v1` root.
- The provisioner itself accepts no source/import pathname. A trusted local owner receives only an in-process staging capability and is responsible for writing new Genie state into that workspace.
- The publication marker is provisioner-owned, must be absent before publish, is created exclusively, flushed/fsynced, and then validated with the complete staging state.
- Same-parent publication uses `MoveFileExW(..., MOVEFILE_WRITE_THROUGH)` with no replace-existing flag.
- A reported move failure is `PUBLISH_UNKNOWN_PRESERVE`: staging evidence remains and no automatic retry/cleanup is authorized.
- After a reported successful move, every verification failure is `PUBLISHED_UNVERIFIED_PRESERVE`: the committed final namespace is preserved and no rollback/republish is inferred.
- A valid one-time publish remains readable by the existing Genie read-only status/result surfaces; the deterministic test's SQLite bytes survive the namespace move unchanged and later read-only calls do not mutate the published tree.
- The inherited Windows live-state binding regression remains green.

## Test evidence

Final tested environment: Windows Server 2025 / `windows-2025-vs2026`, exact CPython `3.12.10`.

- `PROVISIONER_STATIC_BOUNDARY_PASS`
- inherited live-state regression: 4/4 PASS
- canonical provisioner adversarial suite: 11/11 PASS
- `PROVISIONER_IMPORT_CLOSURE_PASS`

The suite includes exclusive/concurrent begin, pre-existing final state, abandoned staging, real Windows app-directory junction rejection, incomplete staging, preseeded marker, destination race, reported move failure, forced post-move validation failure, and successful publication/readback.

## Preserved defect history

The initial green run (`38172996815`, job `114569366426`) passed 10/10 provisioner tests but did not directly attack post-move verification classification. Internal cross-attack identified that after `MoveFileExW` returned success, a failure while reopening/revalidating the final root could escape as generic `PROVISION_NAMESPACE_INVALID`, understating that publication might already be committed.

Repair commit `06897c27d4cf514acdbc883c7e074cdb290d1d76` moved every post-move verification operation behind the committed-but-unverified boundary. The final tested head `250e9c237ef0fe1c9cfade8cccb900e05a0c7e38` adds the explicit mutant and proves `PUBLISHED_UNVERIFIED_PRESERVE` while preserving the committed final state and denying retry.

## Authority / claim limits

This disposition does **not** establish or perform:

- migration/import of the user's existing historical Genie state;
- actual canonical-state creation on the user's machine;
- standalone Genie application composition;
- power-loss durable all-or-nothing creation of the multi-file state;
- rollback/currentness resistance;
- root/bootstrap/custody continuity;
- confinement against a hostile local principal racing namespace objects;
- plugin installation or actual ChatGPT Desktop connection;
- model dispatch/autonomous continuation;
- production readiness, authority promotion, freeze, main merge, or EXP010 execution.

`MoveFileExW` namespace publication and marker fsync are intentionally not interpreted as proof of crash-durable currentness. The published record's scope remains `FIXED_NAMESPACE_VISIBLE_PUBLICATION_NOT_CRASH_DURABILITY`.

The test uses `host_return/trial` only as deterministic bytes written by the TEST into the provisioner's trusted staging workspace. The implementation has no fixture-copy/import function or caller-selected source pathname. Passing tests therefore do not mean fixture data is live user state.

Pass 186 remains inherited controlling. This unit remains NONCLAIM.

## Next frontier

Compose the provisioner into the future standalone Genie owner. New runs should be constructed directly inside the acquired staging capability using the existing shared Genie core, then published once into canonical state. This is the preferred route because it creates no second engine and no synchronization domain.

Existing-state migration remains a separate future authority surface. It must not be silently folded into the provisioner. Actual ChatGPT Desktop installation remains later, after real canonical user state exists.

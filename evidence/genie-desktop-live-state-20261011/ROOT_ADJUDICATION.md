# Root adjudication — Genie Desktop fixed-root live-state binding package

Disposition: **ACCEPT_NONCLAIM_LIVE_STATE_BINDING_PACKAGE**

Accepted subject: the Windows-local read-only live-state binding mechanism and frozen package built from exact tested commit `18012ed3bb648a284124d9690fdc12344e6ba00d`, workflow run `38172329559`, job `114567355097`.

## Accepted narrow conclusions

- The package uses the Windows Known Folder API to derive the current user's `FOLDERID_LocalAppData`, then appends fixed owned components `GenieReasoningEngine/state-v1`; no MCP/model tool argument selects a filesystem path.
- The package does not use `PLUGIN_DATA` as an authoritative Genie state replica and contains no fixture seed/bootstrap path.
- Existing Genie registry parsing remains controlling after an independent fixed-root/direct-child confinement layer.
- Missing state, malformed marker state, traversal/absolute/reserved-name registry paths, and a real Windows directory-junction escape fail closed.
- A valid historical test fixture deliberately placed at the canonical fixed root drove the actual frozen executable successfully through stdio MCP.
- Exactly `get_run_status` and `get_task_result` were exposed.
- The test run returned PASS and a confirmed task returned CONFIRMED with `UNTRUSTED_ACCEPTED_TASK_DATA`; accepted task text was not duplicated into model-facing text.
- The canonical test live-state tree remained byte-identical across successful frozen tool calls and a second independent MCP process launch.
- Host-created `PLUGIN_DATA` remained byte-identical and outside Genie authority/state.
- The final package stages exactly three files: `plugin.json`, `mcp.json`, and `bin/genie-mcp.exe`.
- The exact tested Windows runtime/build closure count remained 36 and `pip check` passed.

## Ephemeral build identities

- Executable SHA-256: `f67f46793497963fc0ae638e22c3434907d24e28740a441940b80aacd0a4ba97`
- Executable size: `22100172` bytes
- CI ZIP SHA-256: `cb8439cdbdcfa955d7291d37c256ebcc6a5354ad756f4029e3bd21be51dda0d7`
- CI ZIP size: `21805992` bytes

The successful workflow explicitly recorded `LIVE_PACKAGE_NOT_UPLOADED_NONCLAIM`. These are ephemeral CI identities only; they are not user-delivery anchors.

## Preserved failure history

The first dedicated live-state workflow run (`38172231755`, job `114567060156`, head `b413355a815ec4f10c1dd2478d3f14ff5bb48c12`) failed before invoking the frozen executable because the Python test harness supplied an incomplete `PYTHONPATH`; `live_state_windows` could not import `shared_interfaces`. That failure remains evidence and is not rewritten as a product defect or success. The repair changed only the test harness search path to include both repository root and `desktop_plugin`. The live-state/confinement implementation was unchanged. The repaired exact tested head `18012ed3bb648a284124d9690fdc12344e6ba00d` then passed the complete workflow.

## Authority and claim limits

This acceptance is for the **binding mechanism**, not proof that the user's actual Genie state is currently bound. The CI test deliberately placed historical test state at the canonical root and removed it afterward.

This disposition does **not** establish:

- provisioning or migration of the user's actual Genie state into the canonical root;
- currentness against whole-store rollback;
- root/bootstrap/custody continuity;
- hostile local-user or TOCTOU/race confinement after validation;
- remote authenticity or hostile-worker isolation;
- code-signing or installer trust;
- behavior on the user's physical computer;
- actual ChatGPT Desktop installation/connection;
- remote/web/mobile availability;
- production readiness, authority promotion, freeze, main merge, or EXP010 execution.

Pass 186 remains inherited controlling. This entire unit remains NONCLAIM.

## Next frontier

The next legitimate unit is **canonical state ownership/provisioning**, preferably owned by the eventual standalone Genie application rather than by the read-only plugin. It must establish/populate `FOLDERID_LocalAppData/GenieReasoningEngine/state-v1` through an explicit trusted local setup/migration path without model-supplied arbitrary pathname authority, silent overwrite, implicit repair, or fallback to repository fixture data.

Because no authoritative live user state source is available to this repository/CI branch, repository tests cannot honestly complete the final user-state provisioning step. Actual ChatGPT Desktop installation/connection is therefore still premature and remains an explicit external user-action boundary after real canonical state exists.

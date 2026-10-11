# Build-component adoption decision — PyInstaller

Decision: **ADAPT (build-time only)**

This record applies `shared_interfaces/EXTERNAL_INTEGRATION_POLICY.md`.

1. **Need** — A local ChatGPT Desktop plugin should launch Genie through a plugin-relative executable without requiring the user to install or maintain Python and MCP packages manually.
2. **Replacement** — A frozen executable removes the system-Python prerequisite and recurring manual dependency installation from the plugin runtime.
3. **Cost** — PyInstaller and its hook package are free/open-source build tools. Standard GitHub-hosted runners for this public repository are used; no paid builder, signing service, hosting service, or runtime subscription is introduced.
4. **User burden** — PyInstaller is never required on the user's machine. It runs only in CI. The plugin runtime is a bundled executable and persistent state lives under host-provided `PLUGIN_DATA`.
5. **Semantic boundary** — PyInstaller may package bytes but must not alter Genie tool schemas, UNKNOWN semantics, state bindings, untrusted-data labels, provenance, authority, STOP/budget, or currentness claims.
6. **Version strategy** — PyInstaller `6.22.3` and `pyinstaller-hooks-contrib==2026.8` are exact-pinned together with the reviewed Windows build/runtime closure. Future build-tool or runtime upgrades require a new package build and frozen-behavior regression pass before adoption.
7. **Failure mode** — A dependency, source-binding, build, or frozen-runtime mismatch fails CI. A plugin runtime that cannot verify its embedded seed or sees partial/interrupted pre-existing persistent state fails closed without overwriting that state.
8. **Authority** — Build tooling has no Genie authority. A successful build or executable hash is packaging evidence only.
9. **Decision** — `ADAPT`: use PyInstaller only to produce a self-contained Windows stdio executable for the local Desktop package. Do not make PyInstaller part of the Genie core or runtime semantics.

## Accepted internal build evidence — 2026-10-11

Tested commit: `0578b62ea033c69601c0eaef6ab75658c0c8c8df`
Workflow run: `38171427730`
Workflow job: `114564670784`
Platform: Windows Server 2025 / `windows-2025-vs2026`
Python: exact CPython `3.12.10`

The build ran in an isolated virtual environment. `pip check` passed. The explicit combined Windows runtime/build acceptance set contained 36 distributions, including Windows-only `pywin32==312`, and matched exactly before freezing.

Pinned build-only additions were:

- `altgraph==0.17.5`
- `packaging==26.3`
- `pefile==2024.8.26`
- `pyinstaller==6.22.3`
- `pyinstaller-hooks-contrib==2026.8`
- `pywin32-ctypes==0.2.3`
- `setuptools==84.0.0`

`pywin32==312` is a Windows runtime dependency of the reviewed MCP closure, not a PyInstaller-only semantic dependency.

The successful frozen package passed `DESKTOP_PLUGIN_FROZEN_PASS`. Ephemeral executable identity was `1add37f928a70d02c275a133612fa353d17b5d4b338c7a4149c8e8f47e6e0b6b` (22,122,614 bytes). Ephemeral CI ZIP identity was `71c92139425bb530d55132beaa791e6ebf81662f84b99ab225ab5855049c5ca0` (21,826,678 bytes). The workflow explicitly recorded `PACKAGE_NOT_UPLOADED_NONCLAIM`; these identities bind the ephemeral successful CI outputs but are not user-delivery anchors.

## Preserved build-learning correspondence

- Do not broadly collect all `mcp.*`: that pulled unused optional `mcp.cli` and its CLI-only `typer` dependency. The accepted build freezes only the required MCP surface.
- Do not normalize pinned source bytes inside verifiers. Cross-platform checkout uses `.gitattributes` to preserve LF Python source bytes so the existing raw SHA-256 bindings remain meaningful.
- Dynamically hash-verified Genie core source is carried as raw data. Imports only visible inside that dynamic path must be explicitly represented in the freezer. The accepted package therefore collects standard-library `sqlite3`; this repaired the pre-acceptance frozen-only `CORE_FAILURE` without changing core semantics.
- Do not interpret a successful binary build as behavioral acceptance. Acceptance requires the frozen stdio lifecycle test, persistent-state replay test, partial-state preservation test, and interrupted-provisioning preservation test.

PyInstaller remains a replaceable build mechanism. If a later packaging method removes more complexity, cost, or maintenance while preserving the same Genie semantics, the adoption decision may be revisited through the standing external-integration gate.

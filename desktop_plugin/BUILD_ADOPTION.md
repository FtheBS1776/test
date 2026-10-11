# Build-component adoption decision — PyInstaller

Decision: **ADAPT (build-time only)**

This record applies `shared_interfaces/EXTERNAL_INTEGRATION_POLICY.md`.

1. **Need** — A local ChatGPT Desktop plugin should launch Genie through a plugin-relative executable without requiring the user to install or maintain Python and MCP packages manually.
2. **Replacement** — A frozen executable removes the system-Python prerequisite and recurring manual dependency installation from the plugin runtime.
3. **Cost** — PyInstaller and its hook package are free/open-source build tools. Standard GitHub-hosted runners for this public repository are used; no paid builder, signing service, hosting service, or runtime subscription is introduced.
4. **User burden** — PyInstaller is never required on the user's machine. It runs only in CI. The plugin runtime is a bundled executable and persistent state lives under host-provided `PLUGIN_DATA`.
5. **Semantic boundary** — PyInstaller may package bytes but must not alter Genie tool schemas, UNKNOWN semantics, state bindings, untrusted-data labels, provenance, authority, STOP/budget, or currentness claims.
6. **Version strategy** — Pin PyInstaller `6.22.3` and `pyinstaller-hooks-contrib==2026.8`, then bind the full observed build dependency closure before accepting a distributable artifact. Future build-tool upgrades require a new build/behavior regression pass.
7. **Failure mode** — A build or frozen-runtime mismatch fails CI. A plugin runtime that cannot verify its embedded seed or sees partial pre-existing persistent state fails closed without overwriting that state.
8. **Authority** — Build tooling has no Genie authority. A successful build or executable hash is packaging evidence only.
9. **Decision** — `ADAPT`: use PyInstaller only to produce a self-contained Windows stdio executable for the current local Desktop proof. Do not make PyInstaller part of the Genie core or runtime semantics.

Current researched release inputs (2026-10-11): PyInstaller `6.22.3`; `pyinstaller-hooks-contrib==2026.8`. Exact CI-resolved build closure must be recorded before package acceptance.

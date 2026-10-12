# Desktop package build reproducibility note — 2026-10-11/12 UTC

Status: **NONCLAIM / LIMITATION RECORDED**

Two independent green Windows builds of the v0.1.1 host-compatibility package were compared.

## Build A — accepted delivery artifact

- tested commit: `a98d11782443a1084518a910d1b4196c07974ea9`
- workflow: `38194737754`
- frozen lifecycle: `DESKTOP_PLUGIN_FROZEN_PASS_WITH_UNKNOWN`
- ZIP SHA-256: `b3945f3b107d178ac99634b12666631191c80359f8456fde2f0a076c83251bbb`
- EXE SHA-256: `c45a34d56bb161e195b8b49fa11c5b0cac57e340974d8c7fe02133c20c2828f5`

## Build B — current-tip documentation-triggered rerun

- head: `31102e45fe97a379d6cf87cb07a80bc378310647`
- workflow: `38194908968`
- all workflow steps: SUCCESS, including frozen lifecycle and upload
- ZIP SHA-256: `b4d70e6fe5a4ccb60c978726fd15f8372f6a11f993d445717a377c38c00e9db9`

Independent extraction and per-file hashing showed the following four package files are byte-identical between the two builds:

- `.codex-plugin/plugin.json` — `135d4a351b22189e397dd8ae9289847bc880c6d1d2648653f09284cb66b42545`
- `.mcp.json` — `84b460f3f2f878551d51504f93fbeb4409d07d422e41b78b61c16541df0cdd75`
- `mcp.json` — `01988257925720558f3d171a1b7611b86f464f304b579e60f25c5d7f19968133`
- `plugin.json` — `7e8bdcc53c9a2c70ac8d863872d72c8192f3d5b0e684627800dc6854a25af2fd`

Only the frozen executable differs:

- Build A EXE: `c45a34d56bb161e195b8b49fa11c5b0cac57e340974d8c7fe02133c20c2828f5`
- Build B EXE: `d351ab01f02f0bd8f14004eb9666e4e2d2d9b9f7a7acb092c6930ff64a37c7ef`

No non-EXE file content difference was found.

## Consequence

The current PyInstaller lane establishes **behavioral/conformance reproducibility**, not bit-for-bit executable reproducibility. Do not predict a future executable or ZIP digest from source identity alone. Each distributable binary must be tested and independently hash-bound after that exact build.

This does not invalidate either green build and does not indicate Genie semantic drift. It is a packaging/provenance limitation to preserve for any later production/signing/release design.

The first accepted v0.1.1 delivery artifact remains the package bound in `HOST_COMPAT_VERIFICATION_20261011.md` (`b3945f3b...251bbb`). Do not silently substitute a later green binary under that digest.

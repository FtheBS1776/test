# Host-registration finding — 2026-10-11

Status: **NONCLAIM / OPEN HOST VERIFICATION**

The first post-install verification attempt did not observe any Genie tools or a running `genie-mcp.exe`, but that attempt ran in a cloud-hosted Work environment rather than a local Desktop Work/Codex execution surface. Therefore it does **not** establish that the installed Windows package is defective.

Current official OpenAI plugin documentation distinguishes portable Agent Plugins packaging from the Codex compatibility scaffold used by Plugin Creator and says local marketplaces are consumed by supported local clients, including Codex in the ChatGPT desktop app. Existing sessions do not reload changed plugin tools.

Engineering response:

1. Preserve the portable root `plugin.json` + `mcp.json` package.
2. Add the currently supported Codex compatibility fallback `.codex-plugin/plugin.json` + root `.mcp.json`, both pointing to the same bundled stdio executable.
3. Do not change Genie authority, tool schemas, read-only behavior, result trust labels, or state semantics.
4. Rebuild and re-run the frozen lifecycle tests before delivery.
5. Require a fresh **local Desktop Work/Codex** session for the real host-registration test.

The compatibility overlay is transport/discovery metadata only. If the local Desktop host still exposes zero Genie tools after this package is installed/refreshed and a new local session is started, that becomes evidence of a genuine host-registration defect.

# Current external specification check — 2026-10-11

Primary sources consulted after the internal correspondence attack:

- OpenAI Plugins quickstart and custom MCP guidance: https://developers.openai.com/plugins/quickstart and https://developers.openai.com/api/docs/guides/custom-mcp-server
- OpenAI MCP server/plugin tool guidance: https://developers.openai.com/plugins/build/mcp-server
- OpenAI plugin reference and guidelines: https://developers.openai.com/plugins/reference and https://developers.openai.com/plugins/plugin-guidelines
- MCP Python SDK request-context and low-level server docs: https://py.sdk.modelcontextprotocol.io/handlers/context/ and https://py.sdk.modelcontextprotocol.io/advanced/low-level-server/

Current facts used by this unit:

1. ChatGPT plugins can use MCP-backed tools; a remote server/tunnel is a later connection step, not required to define a local consumer contract.
2. Tool metadata includes name, description, input schema, and accurate safety annotations. For these two bounded read-only Genie tools: `readOnlyHint=true`, `destructiveHint=false`, `openWorldHint=false`.
3. MCP tool results can expose machine-readable `structuredContent` and model-visible `content`.
4. Tool annotations do not grant authorization. Authorization/validation remains an implementation responsibility.
5. Current MCP request context can provide a request ID, but caller/request correlation is not Genie authority. This unit deliberately uses only a fresh local correlation token to verify its one synchronous adapter reply.
6. Current MCP SDK behavior/version details are not made a dependency here. The consumer remains standard-library and transport-free.

No claim is made that ChatGPT has installed or connected this code, that a plugin submission would pass review, or that a server/backend exists.

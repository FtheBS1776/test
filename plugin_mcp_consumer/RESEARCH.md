# Current primary-source research — 2026-10-11

Official OpenAI plugin documentation currently identifies a custom MCP server as the supported way to expose live read/write tools to ChatGPT as a plugin. The MCP server defines focused tools with explicit input schemas and safety annotations; custom UI is optional. Tool results may use `structuredContent` and/or `content`. Annotations guide host behavior but do not replace server-side validation/authorization.

For this read-only local Genie surface, the relevant MCP annotations are read-only true, destructive false, open-world false; idempotent is also appropriate because repeated reads add no environmental effect even though observed state can change. No server SDK is necessary to verify this projection; a later server unit may use the official TypeScript or Python MCP SDK only when actual transport/connection work is selected.

Security guidance says to treat tool inputs as untrusted and assume prompt injection can reach MCP-enabled LLM applications. Genie already labels accepted `result_text` as untrusted data; this projection therefore requires that label and notice to survive. That label reduces semantic ambiguity but is not evidence that a downstream model cannot be manipulated by the text. This unit exposes no write tool, limiting consequence scope, but does not claim prompt-injection immunity.

Primary sources read:
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://developers.openai.com/plugins/guides/security-privacy
- https://developers.openai.com/plugins/reference

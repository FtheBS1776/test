# ChatGPT/MCP consumer normalization contract — NONCLAIM

Implement `plugin_consumer/consumer.py` only as a transport-free consumer boundary over the pinned accepted `GenieFunctionAdapter`.

## Metadata

`tools()` returns exactly the accepted `get_run_status` and `get_task_result` operations. Preserve the accepted descriptions and input schemas. Add only human-readable titles and explicit truthful MCP/plugin annotations:

- `readOnlyHint: true`
- `destructiveHint: false`
- `openWorldHint: false`

Do not advertise writes, dispatch, authorization, installed-plugin status, server transport, authentication or autonomous execution.

## Calls

`call_tool(name, arguments)` accepts structured JSON-compatible arguments from a prospective MCP/plugin host. Normalize them exactly once into the existing adapter's JSON-string input. Bound normalized UTF-8 arguments to 8192 bytes. Invoke the adapter exactly once.

Generate a fresh local correlation token solely to detect reply mismatch. It is not a Genie run/task/attempt/call/authorization identity and must never be returned as accepted task data.

Require the adapter reply to be exactly a correlated `function_call_output` whose `output` decodes to a strict JSON dictionary. Preserve that dictionary exactly in `structuredContent` and in equivalent JSON text `content`.

Genie semantic states including `PASS`, `CONFIRMED`, `UNKNOWN`, `MISMATCH` and `REJECT` remain ordinary structured data. Do not reinterpret them as MCP-level success/failure or automatically retry them.

Only wrapper-integrity failures—non-JSON input that cannot be normalized, oversize normalized arguments, adapter exception, malformed/mismatched adapter envelope, malformed/non-dictionary adapter output—return a generic MCP-style `isError: true`. Leak no exception/path/payload fragments and retry nothing.

## Source and authority

Pin `shared_interfaces/function_adapter.py` to SHA-256 `9627bc0967e4b6115f405671be8a2c60498101e276d96062d55572537f2769d2`. Do not modify the adapter or core. No existing run/task is replayed, reset, refunded or replaced.

Serial local use only for this unit. No concurrency, server, remote-authentication, deployment or hostile-client claim.

Pass186 remains inherited controlling; this later interface is NONCLAIM. No promotion, freeze, main merge, production deployment, spending, EXP010 execution, beacon/seed action or canonical-save retry is authorized.

# ChatGPT MCP read-only consumer projection — NONCLAIM

Concrete consumer: a future ChatGPT custom MCP plugin exposing Genie's existing `get_run_status` and `get_task_result` read-only operations. This unit implements only the dependency-free projection between the accepted local `GenieFunctionAdapter` and MCP tool descriptor/result semantics. It is not an MCP server, transport, tunnel, deployment, authentication layer, model API client, plugin installation, or backend.

## Reuse

- Pin and load the maintained `shared_interfaces/function_adapter.py` exactly; do not call the core or stores through a second path.
- Preserve exactly two tool names, descriptions, and input schemas from `GenieFunctionAdapter.tools()`.
- Preserve complete result dictionaries from `GenieFunctionAdapter.handle()` without truncation or semantic rewriting.
- `result_text`, when present, must retain `content_role=UNTRUSTED_ACCEPTED_TASK_DATA` and a nonempty notice or the consumer withholds the result as UNKNOWN.

## MCP projection

`tools()` returns exactly two detached descriptors with `name`, human title, `description`, `inputSchema`, and explicit annotations: `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`, `openWorldHint=false`. These annotations describe behavior only; they do not authorize anything.

`call(name, arguments)` accepts one of the two names and a JSON-object argument mapping. It creates a fresh ephemeral correlation ID solely for the accepted adapter envelope, delegates exactly once, requires the correlated `function_call_output`, strict-decodes the output dictionary, and returns `{structuredContent: <complete dictionary>}`. It emits no `_meta`, raw paths, secrets, server instructions, UI, or extra prose. It never retries an UNKNOWN or malformed adapter outcome.

The correlation ID is not a Genie run/task/attempt/call authority token, not durable identity, and not evidence that an MCP host or model executed anything.

## Acceptance

1. Exact adapter SHA-256 binding and constructor use; no second core path.
2. Exactly two tool descriptors and exact name/description/schema correspondence.
3. Correct explicit MCP annotations for both read-only bounded-workspace tools.
4. Fresh detached metadata/results; caller mutation cannot alter later output.
5. Invalid names/non-object arguments reject without adapter delegation.
6. Valid calls delegate once; adapter correlation is fresh and reply must match it exactly.
7. Malformed/uncorrelated/non-dictionary output becomes sanitized UNKNOWN with no retry or fragments.
8. Complete PASS/REJECT/UNKNOWN/CONFIRMED dictionaries survive unchanged inside `structuredContent`.
9. Accepted task text remains visibly untrusted; missing untrusted-data label/notice fails closed.
10. No network, SDK, model call, server, authentication, store mutation, old task replay, canonical save retry, deployment, spending, promotion/freeze/main merge, or EXP010 action.

Pass186 remains inherited controlling; this unit is later NONCLAIM. Root/bootstrap/custody, rollback, physical power loss, remote authenticity, hostile-worker isolation, real MCP connectivity, host lifetime and unattended execution remain outside this unit.


## Recovery candidate consolidation (R08)

Maintain the existing shared consumer/server route. Before delegation, use the accepted adapter's strict JSON-tree predicate and its 8192-byte argument limit; do not coerce tuple values or non-string keys. Core REJECT/UNKNOWN remain structured data; malformed/correlated wrapper outcomes remain sanitized UNKNOWN. The server's existing safe-text projection remains the text surface; this consumer does not add the alternate wrapper's duplicated text or isError shape.

An eight-case corpus compared the exact shared baseline at ad508c63024087d0d38f489f6b42ee7c5f9af662, alternate at b6aa50858737a1f613ea36cbfacaba2486649448, and candidate with a deterministic adapter double. This compares boundary behavior, not real-host compatibility or complete downstream semantics. Both alternatives passed a valid call; the alternate rejected tuple/non-string-key/oversized inputs before delegation while the baseline delegated. The shared baseline withheld unlabeled task text while the alternate projected it. Both checked duplicate replies/correlation with their different declared wrapper-error contracts. Candidate combines the applicable safeguards under one owner. Alternate source and historical evidence remain unchanged; this is not a universal winner or performance claim.

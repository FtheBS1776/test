# Phase 2B1 event-surface contract — NONCLAIM

Expose exactly one local stdio MCP tool, `apply_run_event`, through a separate controller-only process. Reuse the unchanged, hash-pinned `shared_interfaces/run_events.py`; do not invent a generic mutation API. The one tool retains the accepted separate operations `observe`, `submit`, and `review` with the existing exact supplied-token and payload schemas.

The tool is write/destructive/non-idempotent/closed-world. MCP transport success is separate from domain `APPLIED`, `REJECT`, or `UNKNOWN`. `APPLIED` is callback acknowledgement only. The `review` operation applies a separately supplied controller decision; this server neither invokes a reviewer nor chooses ACCEPT. “Controller-only” is a trusted deployment/configuration assumption, not authenticated caller identity or hostile isolation.

Pin `run_events.py` SHA-256 `913b4d89bc5bbec0c37141f7914fd111a342d2fced80d25e404d2d25d704f760`, the exact 1,449-byte canonical input-schema hash `59fd685d201f46cfac160c371f25de5dc55a108c90ad3f28dcb1403331089634`, and the exact MCP 2.3.0 closure plus Windows `pywin32==312`. The event consumer and server each validate allowed result shapes, request/ack operation correspondence, and non-duplicate review decision correspondence.

Reject bad tool names, non-object/strict-JSON failures, extra or malformed fields, unknown aliases, invalid tokens, invalid operation payloads, source mismatches, and dependency mismatches fail-closed. Delegate at most once. Once callback entry may have occurred, exception, malformed output, weakened UNKNOWN, operation mismatch, or review-decision mismatch returns canonical UNKNOWN with `preserve=true` and `allow_new_invocation=false`. Never retry, refund, reset, replace, or infer rollback.

No `advance_run`, worker/reviewer/model dispatcher, session driver, automatic loop, network listener, read-only Genie tool, generic path input, global registration, or persistent pilot run is part of Phase 2B1. All event calls in verification use fresh disposable temporary stores and deterministic inputs explicitly labeled `NO_MODEL_CALL` and `independent_proof:false`.

The three-operation synthetic test may reach task state `ACCEPTED`; it intentionally performs no subsequent progression. Queue state remains ACTIVE, the single reservation remains charged, and reports/applications remain zero. This is not task/run completion, delivery, fresh destination confirmation, model execution, content quality, provenance, independent review, production readiness, or authority promotion.

# Genie Phase 2A local controller pilot

This directory records a bounded NONCLAIM write-boundary pilot. The separate `shared_interfaces.mcp_controller_server` process is stdio-only and exposes exactly `advance_run`. It pins the accepted `run_control.py`; the existing `genie-readonly` server/package is not modified.

The tracked `trial` registry contains one fresh synthetic run only. Its policy is one task, one reservation, and one attempt. The recorded live pilot makes one MCP call, expects a bound `INVOKE_WORKER` action/token, and stops without dispatching a worker or applying an event.

The charged raw SQLite stores, raw call result, and raw post-call snapshot remain preserved on the originating pilot host and are gitignored rather than published. `PRE_CALL_STATE.json`, `CALL_RESULT_REDACTED.json`, and `POST_CALL_STATE_REDACTED.json` are the bounded branch evidence; they contain state counts, exact database hashes, and one-way binding commitments without exposing the live action token.

Use `test_controller_mcp.py` for disposable positive, negative, uncertainty, mutation, and Windows stdio checks. Those tests may create temporary runs; they never address historical aliases. Do not make a second call against the recorded trial. Inspect its persisted local state or the bounded snapshots instead.

Phase 2B remains a separate authorization boundary. Nothing here exposes `apply_run_event`, worker/reviewer dispatch, or `session_driver`.

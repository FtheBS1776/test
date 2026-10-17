# Phase 2B2 attested live pilot — complete NONCLAIM

The single authorized live worker turn completed on 2026-10-16 and stopped
before Phase 2C. The exact patched Codex executable was independently rehashed,
passed a zero-model contained preflight, and then entered one fresh synthetic
worker operation using the user's existing Codex authentication.

The emitted pre-turn capability snapshot bound the exact executable, logical
operation, `gpt-5.6-sol`, read-only sandbox, and canonical empty-tool policy;
it reported `tool_count=0` and `tools=[]`. No tool activity appeared in the raw
event stream. The process tree contained exactly the live-observed patched
`codex.exe` and `conhost.exe`, reached zero active members, and received one
bounded termination call. The fixed output remained untrusted and was accepted
only after fresh destination readback.

This is common-cause same-host/same-provider evidence, not independent proof,
general sandboxing, hostile pre-assignment containment, a production claim, or
authorization for autonomous Phase 2C progression.

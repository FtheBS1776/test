# Phase 2B2 recovery-preflight results

## Before process entry

- The published Phase 2B2 terminal-UNKNOWN branch was independently verified at
  `dada320b2e9ee39215fbf5d1d451f19ede326159`.
- Codex executable size and SHA-256 remained exactly 333,479,728 bytes and
  `dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`.
- Five new static/adversarial tests proved the read-only protocol surface,
  zero-turn binding, corrected global-option ordering, strict model pagination,
  and terminal duplicate-ledger behavior.
- The combined inherited and new suite passed 142/142 with zero skips.

## Sole process entry

- Operation ID:
  `81aafe7820cd9e54f14bd364061219d409cdd2b58bd544cfe082c0b16f3d9e24`.
- Root PID: `48528`; Job assignment was verified before protocol traffic.
- Result: terminal `UNKNOWN` after app-server EOF.
- Preserved stderr: `Error: Unknown feature flag: browser_use_mcp_client`.
- Exit code: 1.
- Job accounting after termination: two total processes, zero active.
- Fresh OS readback found PID 48528 absent.
- Semantic requests, threads, turns, and model turns: all zero.
- Retry count: zero; ledger is `UNKNOWN`, `preserve=1`,
  `allow_new_invocation=0`.

## Postmortem repair

The new recovery adapter now removes only the empirically rejected
`browser_use_mcp_client` disable pair from the otherwise bound command.  The
repair passes all 142 tests but was deliberately not exercised with another
Codex process.  It is preparation for a separately authorized operation, not a
retroactive success claim.

# Recovery-verification preflight results

## Before process entry

- The published repaired-preflight frontier was independently fetched and
  verified at commit `97aa1c135b766113ec57d5197df24e697ac5c4b3`, tree
  `eeafeb5b306cf73408e7cf6aa2a3d316176106e1`, parent
  `b5904f2589be79df699d38899c51ee15805ca887`.
- The Codex executable remained 333,479,728 bytes with SHA-256
  `dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`.
- The fresh operation context was incorporated into the hashed binding; neither
  prior UNKNOWN ledger nor operation identity was reused.
- The full focused/regression suite passed **149/149**, zero skips.

## Sole process entry

- Logical operation:
  `b2321feff8b148eea319fd0557e4294e2469a79843d75beaaa86f897d650fce5`.
- Root PID 40416 was assigned to the kill-on-close Job before protocol traffic.
- All four allowed requests were sent: `initialize`, `config/read`,
  `mcpServerStatus/list`, and `model/list`.
- The process stopped terminal `UNKNOWN` because effective MCP inventory was
  nonempty.  Isolation was therefore not accepted.
- No semantic request, thread start, turn start, or model turn occurred.
- Exact member identities were not fully preserved; Job accounting observed
  seven total processes and zero active after the single termination.
- Fresh OS readback found PID 40416 absent.  The isolated scratch directory was
  empty.  Retry count is zero; the ledger is `UNKNOWN`, `preserve=1`, and
  `allow_new_invocation=0`.

## Postmortem source repair — not executed live

Official documentation confirms `--ignore-user-config` prevents loading
`$CODEX_HOME/config.toml` while preserving authentication through `CODEX_HOME`.
The future-only command now includes that flag.  It also records non-secret
inventory counts before validation and preserves partial member evidence when a
short-lived member cannot be queried.  The final source passed **152/152**
focused/regression tests with zero skips.  No second Codex process was launched.

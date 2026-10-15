# Repaired recovery-preflight results

## Before process entry

- The published recovery frontier was independently fetched and verified at
  commit `b5904f2589be79df699d38899c51ee15805ca887`, tree
  `0f8ced3b0ae70ff3623984cc6c2b3e8950a4bcc6`, parent
  `dada320b2e9ee39215fbf5d1d451f19ede326159`.
- The Codex executable remained 333,479,728 bytes with SHA-256
  `dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`.
- The fresh operation context was incorporated into the hashed binding; the
  prior UNKNOWN ledger and operation identity were not reused.
- The established 129-test regression set, eight live-worker tests, five
  recovery tests, and two fresh-operation tests passed: **144/144**, zero skips.

## Sole process entry

- Logical operation:
  `d8de3ff965dd993c1a62eb31107b9d27f6e73bb38a6b9d33790fcdbdc994d883`.
- Root PID 49156 was assigned to the kill-on-close Job before protocol traffic.
- The process stopped terminal `UNKNOWN` after the controller's first bounded
  receive poll raised `queue.Empty`.  This was a controller defect, not a
  verified Codex rejection or a successful initialization.
- No semantic request, thread start, turn start, or model turn occurred.
- Effective MCP/tool/app inventory was **not observed**, so isolation is not
  accepted.  Exact member identities were also not preserved; Job accounting
  observed six total processes and zero active after the single termination.
- Fresh OS readback found PID 49156 absent.  The isolated scratch directory was
  empty.  Retry count is zero; the ledger is `UNKNOWN`, `preserve=1`, and
  `allow_new_invocation=0`.

## Postmortem source repair — not executed live

The receive loop now treats an empty 250 ms poll as “keep waiting” until the
bound deadline.  Failure-member evidence is captured before Job termination,
and the root process receives a bounded wait after termination so its exit code
and Python handle lifecycle can settle.  Two tests cover the receive behavior
and capture ordering.  The final source passed **146/146** focused/regression
tests with zero skips.  No second Codex process was launched.

# Isolation-verification preflight results

## Before process entry

- The published recovery-verification frontier was independently fetched and
  verified at commit `22893c65c67b09758dff072db9a75cb0f62dc94f`, tree
  `e2996ab34c10027c533078633fe7685de89e3b79`, parent
  `97aa1c135b766113ec57d5197df24e697ac5c4b3`.
- The Codex executable remained 333,479,728 bytes with SHA-256
  `dd13bdb162a184fa04039488b234a8258ef9b76f84e926c505d5742b19249a6a`.
- The fresh operation context and repaired command were incorporated into the
  hashed binding; no prior UNKNOWN ledger or operation identity was reused.
- The full focused/regression suite passed **154/154**, zero skips.

## Sole process entry

- Logical operation:
  `51e92f02e99d9f362ec01eece83ef1a69c9f90e257489e06da191f91b9810bc8`.
- Root PID 53572 was assigned to the kill-on-close Job before protocol traffic.
- Only `initialize` was sent.  The bound Codex 0.162.1 executable rejected
  `--ignore-user-config` as an unexpected argument and exited with code 2.
- The process stopped terminal `UNKNOWN`.  Initialization and effective
  inventory observation did not complete, so isolation was not accepted.
- No semantic request, thread start, turn start, or model turn occurred.
- Member identity queries returned `PermissionError`; Job accounting observed
  two total processes and zero active after the single termination.
- Fresh OS readback found PID 53572 absent.  The isolated scratch directory was
  empty.  Retry count is zero; the ledger is `UNKNOWN`, `preserve=1`, and
  `allow_new_invocation=0`.

## Postmortem correction — not executed live

The current official CLI reference documents `--ignore-user-config`, but the
exact bound 0.162.1 executable does not accept it.  Future source now explicitly
marks the bound runtime as unsupported and removes the unusable flag so tests do
not make a false compatibility claim.  The final source passed **154/154**
focused/regression tests with zero skips.  No alternative user-config isolation
mechanism was implemented or exercised, and no second Codex process was
launched.

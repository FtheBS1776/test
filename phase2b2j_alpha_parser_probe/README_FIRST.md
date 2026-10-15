# Phase 2B2J: one-launch alpha parser probe

Status: **PARSER PROBE INCONCLUSIVE - NONCLAIM**.

The exact audited alpha executable was launched once with a fresh empty
`CODEX_HOME`, credential variables removed, outbound proxy variables pointed
at a closed local endpoint, and the arguments
`--ignore-user-config --version`.

The root parser rejected `--ignore-user-config` and exited with code 2.  The
official CLI reference places this option on `codex exec`, so this observation
does not establish whether `codex exec --ignore-user-config --help` would parse.
No retry or alternate ordering was attempted.

No installation, app-server, authentication change, prompt, worker, model
turn, Genie action, or historical-run mutation occurred.

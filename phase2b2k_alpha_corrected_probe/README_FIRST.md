# Phase 2B2K: corrected alpha exec parser probe

Status: **EXEC PARSER ACCEPTED - NONCLAIM**.

The exact audited alpha executable was launched once with the help-only vector
`exec --ignore-user-config --help`, a fresh empty `CODEX_HOME`, credential
variables removed, and outbound proxy variables pointed at a closed local
endpoint.

It exited 0 and its `exec` help listed `--ignore-user-config`.  This establishes
argument-parser support only.  It does not establish config non-loading,
effective MCP/tool isolation, authentication behavior during a run, process
containment, or worker/model suitability.

No prompt, model turn, installation, app-server, Genie action, or historical
run mutation occurred.

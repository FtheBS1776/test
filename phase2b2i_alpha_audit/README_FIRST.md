# Phase 2B2I: alpha suitability audit

Status: **STATIC CANDIDATE FOUND - NONCLAIM**.

This directory records a bounded, static audit of exact package
`@openai/codex@0.163.0-alpha.11` and its Windows x64 payload.  The archives
were downloaded, integrity-checked, path-validated, unpacked without lifecycle
scripts, and inspected as data.  The alpha executable was never installed or
run.

The static evidence is sufficient only to nominate the alpha for a separately
authorized offline parser probe.  It does not establish that the executable
accepts `--ignore-user-config`, starts correctly, isolates authentication,
produces an empty effective MCP/tool inventory, or is suitable for a worker or
model turn.

No Genie run, historical state, authentication, configuration, app-server,
worker, reviewer, model, destination, or EXP010 artifact was touched.

# Isolation recovery design

## Observed boundary

Only non-secret local metadata was inspected.  The current Codex home has a
file-backed authentication cache, no explicit credential-store override, four
MCP configuration sections, and fifteen plugin/app configuration sections.
No credential content was read or recorded.  Official documentation says
`CODEX_HOME` contains configuration, authentication, logs, sessions, skills,
and package state, and says a file-backed `auth.json` contains access tokens and
must be treated like a password.

Sources checked 2026-10-15:

- <https://learn.chatgpt.com/docs/auth>
- <https://learn.chatgpt.com/docs/config-file/environment-variables>
- <https://learn.chatgpt.com/docs/cli/reference>

## Decision

The preferred mechanism is the existing authenticated user home combined with
a documented, executable-supported `--ignore-user-config` boundary.  The bound
Codex 0.162.1 executable empirically rejects that flag, so the mechanism is not
currently available.  The next action, if separately authorized, is limited to
upgrading or rebinding Codex and verifying the replacement executable's exact
path, version, hash, and help/argument behavior without a model turn.

Copying `auth.json` into an otherwise empty isolated `CODEX_HOME` is rejected
for this pilot.  Although OpenAI documents credential-cache copying for trusted
headless machines, here it would duplicate a password-equivalent bearer secret,
may be rewritten during token refresh, and creates unresolved preservation and
secure-cleanup obligations after post-entry `UNKNOWN`.  Windows secure deletion
cannot be inferred from ordinary file deletion.  No credential copy is
authorized or implemented.

Keyring reuse is also not claimed.  The documentation does not establish that
an empty isolated home would resolve the same keyring entry, and the current
configuration does not explicitly bind keyring storage.  No empirical auth
probe was performed.

## Future gated sequence

1. Separately authorize upgrade/rebind only; do not launch a worker.
2. Bind exact executable path, version, and SHA-256.
3. Verify offline that the executable accepts the documented bypass option and
   that no wrapper substitutes another binary.
4. Re-run the standing correspondence audit and create a new logical-operation
   identity.  Never reuse any terminal `UNKNOWN` identity.
5. Separately authorize one no-model isolation preflight.
6. Assign the suspended child to the Windows Job before protocol traffic.
7. Allow only initialization and inventory-read protocol messages.  Observe
   effective MCP/tool/plugin/app inventory; do not infer it from arguments.
8. On any uncertainty after process entry, record terminal `UNKNOWN`, preserve
   evidence, set `allow_new_invocation=false`, and do not retry, refund, reset,
   replace, or use an alternate launcher.

This design does not authorize any step in that sequence.

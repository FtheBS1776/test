# Phase 2B2 Codex upgrade/rebind - read first

Classification: **NO-CHANGE REJECT - NONCLAIM**.

The authorized software-only recovery boundary completed without changing the
installed Codex package.  The bound 0.162.1 executable's documented self-update
command could not detect its npm installation method.  Fresh readback proved
the executable remained byte-identical.  The npm registry's `latest` stable tag
also resolves to 0.162.1, and the only other official local executable found is
byte-for-byte identical.

The unchanged stable executable rejects `--ignore-user-config` with exit code
2.  The registry exposes an alpha build, but prerelease installation or binding
was not authorized and was not performed.

No login/logout, credential read or copy, app-server start, logical operation,
inventory request, model turn, Genie mutation, or historical-run mutation
occurred.  Read `ADJUDICATION.md` and `TEST_RESULTS.md` before any next step.

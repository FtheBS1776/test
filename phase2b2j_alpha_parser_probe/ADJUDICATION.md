# Adjudication

Decision: **PARSER_PROBE_INCONCLUSIVE_NONCLAIM**.

The authorized executable was launched exactly once and deterministically
rejected the supplied root-level `--ignore-user-config` argument with exit code
2.  This proves that exact root argument vector is not accepted by this build.

It does not prove the documented `codex exec --ignore-user-config` surface is
absent, because the option belongs to the `exec` subcommand in the official CLI
reference.  Treating the result as general flag rejection would overclaim.

The process exited, no matching alpha process remained, the original auth and
configuration hashes were unchanged, and the fresh probe home contained only
the alpha's temporary argument-zero wrappers.  No prompt or model path was
entered.

There is no retry under this authorization.  The next possible boundary is
`ONE_CORRECTED_ALPHA_EXEC_HELP_PARSER_PROBE`, using only
`exec --ignore-user-config --help`.  It requires separate explicit
authorization.

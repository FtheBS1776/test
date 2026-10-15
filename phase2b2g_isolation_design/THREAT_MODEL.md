# Threat model and fail-closed controls

| Threat | Required control | Current disposition |
|---|---|---|
| User MCP/plugin/app configuration reaches child | Documented config bypass plus observed effective empty inventory | Blocked on executable support |
| Genie authority reaches child | Exclude tokens, paths, tools, callbacks, registries, and authority secrets from environment, argv, cwd, and request | Synthetic validator only |
| Credential disclosure through evidence | Never read, serialize, log, publish, or hash into public evidence the credential contents | Enforced by artifact design |
| Password-equivalent credential duplication | Do not copy `auth.json` | Rejected |
| Assumed keyring reuse | Require documented or independently verified lookup behavior | Deferred |
| Project-local `.codex` configuration | Empty scratch cwd outside repository and owned roots; fresh readback before launch | Future gate only |
| Executable or wrapper substitution | Bind path, version, hash, and argument behavior | Future gate only |
| Process escapes containment | Assignment before release; exact Job membership and bounded kill-on-close evidence | Reuse accepted 2B2B contract |
| Stale or duplicate operation | Fresh hashed logical identity and one-shot ledger | Reuse accepted Phase 2B2 contract |
| Post-entry ambiguity | Terminal `UNKNOWN`, `preserve=true`, `allow_new_invocation=false`, no retry | Reuse accepted Genie semantics |
| Model or child output treated as authority | Untrusted data plus fresh destination readback | Future live pilot requirement |
| Same-host evidence mistaken for independence | Label common-cause and non-independent | Permanent limitation |

No production sandbox, network isolation, hostile pre-assignment containment,
independent provenance, or secure-deletion claim is made.

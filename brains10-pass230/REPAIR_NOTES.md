# Documented harness repair

- Retain exact original Pass230 ZIP and select separately identified R2 repaired gate; do not claim original passed.
- Replace unspecified container startup with a real native server from the same pinned release archive as client. This removes separate image/default/listen ambiguities. Both listen endpoints use loopback. No persistent infrastructure/global installation.
- Pin official action commits, disable checkout credential persistence, manual-only trigger, contents:read, no other permissions/secrets.
- Verify exact source-manifest digest before loading execution code, validate all payload hashes and gate ZIP/manifests. SHA256 establishes bytes, not authorization.
- Set explicit bounded command/readiness/job timeouts. Create evidence exclusively, record raw stdout/stderr and command status, server config/logs, versions and measured hashes. Preserve early failures and partial captures; separate capture completeness from adjudication.
- A source manifest excludes the workflow to avoid a self-hash cycle. Returned workflow bytes and its SHA are independently bound to the provider's run commit/workflow reference on retrieval.
- GitHub environment variables are recorded declarations, not independent proofs. Local rehearsal is explicitly labelled and excluded from GitHub claims.
- Record single-node scope and avoid claiming the serializable read was stale, a distributed linearizability test occurred, or an unknown-commit fault was induced.
- Repository publication and billing are unresolved operational choices. Existing public test contains a prior provider-capture workflow; this does not establish permission to publish newly uploaded project inputs. Private R1 avoids publication but available included quota is unverified.

Cross-check after first rehearsal: command timeout must end the entire command process group so a child gate cannot continue writing after capture finalization. Adapted timeout cleanup and added a harmless delayed-child regression. The first local rehearsal remains retained; second rehearsal validates the exact final candidate.

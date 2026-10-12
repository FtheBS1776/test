# Phase 2B2A prior-experience correspondence audit

This audit was completed on 2026-10-12 before inspecting the Phase 2B1 branch head and before repository edits. It applies brains10-pass230/PRE_RESEARCH_AUDIT.md, active_runner/REVIEW_PLAN.md, evidence_summary/CORRESPONDENCE.md, run_control/PRIOR_CORRESPONDENCE.md, run_events/PRIOR_CORRESPONDENCE.md, session_driver/PRIOR_CORRESPONDENCE.md, session_driver/TRANSPORT_BLOCKER.md, worker_bridge/CORRESPONDENCE_AND_PLAN.md, worker_substitution/PLAN_AND_CORRESPONDENCE.md, shared_interfaces/EXTERNAL_INTEGRATION_POLICY.md, and the Phase 2A/2B1 records.

1. Exact executable, source, request, and response identity are necessary but do not create launch authority, execution proof, content truth, review independence, or completion.
2. Controller authority, process entry, child execution, child output, callback application, review, and verification remain distinct. Phase 2B2A exercises only a deterministic child-process boundary.
3. A saved Genie token is not fresh permission. The typed API has no dedicated run alias/ID, token, queue/root path, registry, policy, budget, callback-authority, or MCP field. Its strings remain opaque: they can contain paths, tokens, or secrets if a trusted parent puts them there, so semantic redaction is an unverified parent responsibility.
4. Only a bounded parent-provided worker-proposal request and opaque parent-generated launch ID are accepted. The launcher does not add the launch ID to child argv/stdin; opaque caller strings can still contain the same bytes. The request classification is `BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT`, not a sanitization claim.
5. The executable, executable digest, fixed argument vector, fixture digest, environment allowlist, output schema, limits, and working-root policy are trusted parent configuration rather than caller-selected inputs.
6. The request travels through bounded stdin, never argv. Process creation uses an argument vector with no shell and a fresh non-repository working directory.
7. Under a fresh, untampered launcher-owned disposable claim store, a launcher-local SQLite claim is committed before process creation. Reuse of that exact launch ID never spawns again. This is trusted local bookkeeping, not global at-most-once, rollback resistance, or physical-durability proof; a fresh launch ID or different store is a distinct trusted-parent decision. The claim does not create Genie authority and verification uses disposable stores only.
8. Validation failures before the claim are deterministic REJECT. Once claim commit or process entry may have occurred, handled timeout, crash, nonzero exit, pipe failure, malformed/oversize output, cancellation, or lost response is canonical UNKNOWN with preservation and no new invocation permission. Forced process termination can prevent a domain return.
9. A valid fixture return is untrusted deterministic NO_MODEL_CALL output. It is not a worker observation, model result, provider receipt, independent proof, callback acknowledgement, or review decision.
10. OpenAI documentation supports pinned headless CLI use with stdin and structured output, while sandbox guidance requires workload/credential separation. Those are design inputs, not proof that future Codex child isolation is effective. The fixture launch suppresses `site` startup, pins the local interpreter path/executable bytes, and validates the fixture bytes; it does not pin the full CPython/standard-library closure and only attempts bounded cleanup of the direct child, not a hostile descendant tree.
11. Same-host or same-agent review remains common-cause rather than independent evidence. Local hashes, one successful fixture return, and SQLite history establish neither future currentness nor live-model behavior.

## Disposition

- Host-internal worker-proposal fixture launcher and disposable tests: **ADAPT**.
- Pure, non-executable plan for the pinned future Codex CLI command: **ADAPT**.
- Reviewer launching, live codex exec, authentication provisioning, provider/model selection, callbacks, persistent runs, MCP exposure, session_driver, and automatic progression: **DEFER**.
- Caller-selected executable/argv/env/cwd, shell construction, inherited environment, prompt-in-argv, retries after claim/UNKNOWN, refund/reset/replacement launch, hostile-isolation claims, main merge, promotion/freeze, spending, and EXP010: **REJECT**.

## Exact head inspected after this audit

- Local branch: nonclaim/genie-phase-2b1-event-surface-20261012
- Local commit: eef5ac5e432a0d66ab5e41c808a26cbb6712ee40
- Tree: d89b516ddb17c57d781dfba01276a44651baf941
- Published equivalent commit: 196b4b8f5ec16c8dbc3bf3458d968e7965a73976
- Worktree: clean
- New branch: nonclaim/genie-phase-2b2a-isolation-launcher-20261012


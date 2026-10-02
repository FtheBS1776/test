# Pass 230 GitHub execution candidate — NONCLAIM

Pass 186 controls. This prepares implementation-level observation only. Original independent-provider HOLD remains. No promotion/freeze.

The original amendment and Pass230 identities are documented in PRE_RESEARCH_AUDIT.md. original_gate.zip preserves all original Pass230 bytes. repaired_gate.zip is the previously checked R2 repair (SHA256 9e78ad38390a26bd84db56b8fa468af7d6d378a7e5edabc191cf3c87fb36284b), unchanged here. It is NOT the historical original subject.

Read PRE_RESEARCH_AUDIT.md, RESEARCH_AND_CROSSCHECK.md and REPAIR_NOTES.md before running. The workflow is manual-only and must be registered on the selected repository's default branch for workflow_dispatch. Files live under brains10-pass230; only the new workflow goes under .github/workflows. Existing EXP010 workflows are not modified or executed.

The workflow uses a standard Ubuntu 24.04 hosted runner, a checksum-pinned official etcd 3.6.5 server/client release, loopback-only single member and an exclusive temporary data directory. No production secrets, OIDC, beacon, seed, or scientific execution.

Capture completion is not conformance adjudication. Retrieve the artifact AND provider run/job metadata, verify artifact SHA256 against provider metadata and every EVIDENCE_MANIFEST entry, and bind run ID, attempt, commit, workflow source, gate ZIP and binary identities to the intended execution. Missing artifacts, mismatch, cancellation, timeout or uncertain identity are INDETERMINATE. Never infer production properties from a green job.

For raw gate observations independently inspect all six RANGE_JSON records: exact keys and values, explicit read modes, consistent cluster/member identity, initial head revision, successor/receipt shared modification revision, and unchanged revisions and versions after failed replay. Confirm TXN_INIT SUCCESS, TXN1 SUCCESS and TXN_REPLAY FAILURE. Verify result seal binds log and embedded gate manifest. Stable replay only: this gate does not induce an unknown-commit network fault, concurrency, follower staleness or failover.

Evidence collection may fail on runner cancellation/loss. Artifact upload failure cannot be repaired by interpreting a green capture line. Retain all failed attempts separately. No retry automatically reruns this workflow.

Execution is pending repository visibility/cost selection and access to workflow dispatch. The exposed GitHub tools do not dispatch workflows; the browser fallback requires user approval. No GitHub run has occurred merely because these files exist.

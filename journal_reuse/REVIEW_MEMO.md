# Revised journal reuse review — bounded source finding

Task `genie-journal-reuse-review-20261009`, attempt 1. No blocking behavior weakening found in the inspected refactor and its supported diagnostic call path. Root remains adjudicator; this is a source-review recommendation, not executed verification or production acceptance. It is separate from the pre-design audit and uses the same model/shared ancestry, not independent proof.

## Exact input and revision

Computed canonical manifest digest `14f844e35e5eb81c508982c057ef725ce60e3dc75a74e5caa575850126ed16f9` matches dispatch, plan and token. All seven manifest file hashes match. Canonicalization is sorted compact UTF-8 JSON. The policy permits one task/reservation and the plan one attempt; the earlier pre-design review is a separate activity, not hidden inside this count.

| Inspected revised source | SHA-256 |
|---|---|
| host_adapter/journal.py | 1d7825208cfac386acf0cd83b3505064de8c147ebb35fc6fe54864dd3950cc98 |
| active_runner/run_status.py | 717461b56e191ff011c9b91330d0051f05a0ca03143883566778092e9af2b18e |
| run_queue/run_policy.py | e9105931aea517fe5bdcb9e1cf9065ab8b8d67cf6a91f4bb8765aefe1e5f3a63 |
| active_runner/runner.py | e315b0f30403028169d9bde17f73e13b618ed419ace4fb489f7c0878f2d6fd29 |

Baseline hashes match the earlier inspected subjects: journal `8e5d5b2fc39dce31f2a1bce4617ec60e726dd84c5f60be914fb1eb0c1fc9e1d7`; diagnostic `af0fdad950a7d1849ea04d5e3670acffde5d1bf4c4e9468017a29c70047327cf`; queue `ac708a3b3ad4927d58ead75a89825ffcbf43fa79a34f6a606567a38d282af543`; runner `d5450a38cf5aa4e9f6356b213fb15ddee2b751ba5101e6e17991ee6922363cd3`. I inspected source diffs against those preserved snapshots; prior-source review is not substituted for this revision review.

## Extraction and adapter behavior

The journal diff moves the existing transaction body, with indentation adjusted and a new docstring, into `status_db(db)`. `status(path)` retains its existing `b.transaction(path, False)` ownership and delegates. Shared validation still reads current task/call/attempt, compares canonical call identity and request, checks each event hash and context, and verifies observed agents against the bound agent. It performs SELECTs and computation only: no connection creation, commit, rollback or close. Initial reads remain outside its narrower exception handler, preserving the journal wrapper's existing exception behavior. EXTRACTION_CHECK.json reports AST identity; I read that controller record but did not execute an AST check myself.

The diagnostic passes its existing mode=ro/query_only connection to the shared helper. Its prechecks still inspect both journal schemas before the no-call return. A valid schema without a call still yields NO_RECORDED_HOST_CALL. Partial schema or malformed journal records remain nested UNKNOWN with preserve=true rather than provisioning anything.

Diagnostic-only strictness remains explicit: request attempt and every event attempt must have exact Python int type, excluding boolean and floating equivalents; request goal must equal the validated plan goal. Shared validation then supplies equality to the current attempt and task/input binding. Thus consistently rehashed true/1.0 attempts and altered/missing goals do not gain acceptance through the narrower shared journal contract.

Malformed JSON objects, arrays/null causing AttributeError, schema/SQLite failures and shared validation failures remain inside the diagnostic adapter's broader catch. Shared HOST_RECORD_INCONSISTENT is translated to HOST_RECORD_UNKNOWN_OR_INCONSISTENT. The adapter's initial null agent/call, zero count and UNKNOWN status survive failure; it does not copy a stored but unvalidated call ID from the journal error output. Valid results copy only host_outcome, agent, call_id and observation_count, adding OBSERVED; no candidate, payload or event evidence body is exposed. A consistent call without accepted events remains OBSERVED with UNKNOWN host outcome, as before.

The normal caller validates task count, exact saved plan, state and attempt before calling the adapter, in the same transaction. The shared helper rereads current task context from that same snapshot. This is important: equivalence is scoped to that supported call path, not arbitrary callers passing fabricated task/plan/attempt arguments to an internal function.

## Independent observations and source pins

Workflow, journal and sink remain separate observations. ACCEPTED/DELIVERED still validate the accepted effect and open a fresh read-only sink observation even when the journal result is UNKNOWN. Queue COMPLETE is historical, not an aggregate completion claim. Missing/changed sink evidence can remain UNKNOWN/MISMATCH. Queue and task/sink observations are separate transactions, not a global snapshot. Wrong-run rejection and missing-store preservation paths are unchanged by the diff.

Pin propagation is consistent with computed bytes: diagnostic pins revised runner; runner pins revised queue; queue pins revised journal; journal retains bridge pin `6cbc9f8b0d6f2beb85e5e60927fbc3bf4ac21628daaf3f12c8aefd3780df4b89`, which matches the local bridge file. Queue and runner diffs change only those pins. These are trusted-owned-source integrity checks, not authenticated provenance or hostile-source isolation.

## Results attribution and residuals

Root reports 25 differential/read-only checks, 46 runner/status regressions and 17 direct journal checks. Root also reports preserving an initial unittest discovery that ran zero journal tests and correcting it with the direct script. Zero discovered tests are not verification. I did not execute or independently reproduce any of these counts; my actions were reading, diffing, hashing and writing this memo/status.

The refactor still parses/scans events once for diagnostic strictness and again for shared validation, and the shared helper materializes rows/events. This is a bounded maintenance tradeoff, not a claimed throughput improvement. The shared journal intentionally retains its original weaker goal/type contract and narrower exception surface; only the diagnostic adapter adds stricter handling. The caller owns transaction snapshot/lifetime. Retain regression coverage for these boundaries if the internal API changes.

No new authority mechanism, model invocation, provider fixture, old experiment, publication, spending, deployment or EXP010 action is established by this source review. No further source defect requiring repair was identified within its inspected scope.

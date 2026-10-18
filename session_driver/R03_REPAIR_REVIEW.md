> Predecessor record: this describes the isolated R03 v2 candidate before the later standing repair authorization. Subsequent R05/R06/R07/R08/R10 changes and transitive pin updates are recorded in the root README and combined test log. The original v2 diff is preserved; this record is not the current unified status.

# R03 isolated repair review — candidate v2

Status: local source candidate. Not committed, pushed, independently reviewed, merged, promoted or production-authorized.

## Identity, authority and correspondence

- Repository: FtheBS1776/test. Base commit: ad508c63024087d0d38f489f6b42ee7c5f9af662. Base tree: 2b1bad31e09f6c3bd98e1aa22e85640fec547b50.
- Checks ran on Linux with Python 3.12.14, not Windows.
- Authorized scope: isolated R03 patch and focused no-model checks. No live pilot, paid/model/provider call, scientific execution, master-roadmap mutation, main merge or deployment.
- Existing owners retained: PilotHooks produces task-specific review; events validate callbacks; the driver binds the submitted candidate/token; the bridge persists ACCEPT/REPAIR; the queue reserves bounded calls.
- Reuse the driver's strict duplicate-key/nonfinite JSON helpers. No new parser service, authority mechanism, budget service, external dependency, phase or parallel roadmap. Existing source pins are unchanged.

## Settled negative paths

A hash-bound candidate which fails this exact task schema receives REPAIR. Strict parsing rejects duplicate keys and nonfinite constants. JSON serialization comparison preserves boolean-versus-number distinctions which Python object equality loses. Ordinary candidate decode failures are repair feedback; unexpected runtime failures retain UNKNOWN.

Token/hash mismatches and unsupported decisions are not repair feedback. The driver returns UNKNOWN before review mutation. The producer retains REJECT for its hash mismatch; no blanket REJECT translation or new persisted terminal-rejection state is introduced.

At the attempt cap, REPAIR leads to HOLD / ATTEMPT_BOUND. With attempts remaining but no call slot, the existing queue returns STOP / CALL_BUDGET_EXHAUSTED. With both permissions remaining, the next repair has a distinct existing token/call identity and the original feedback. Lost review acknowledgement stops the current driver at UNKNOWN even if REPAIR committed. Reservations remain charged, with no reset, refund or second invocation in that uncertain call.

## Preserved failure evidence

The earlier candidate's composed test used a substitute reviewer returning REPAIR; it did not exercise PilotHooks.reviewer. Direct attacks showed the real producer accepting authority_request=0 and a conflicting duplicate authority_request field. The stronger real-producer composed test then failed three subcases: integer_for_boolean, float_for_boolean and duplicate_conflicting_key. Each reached STOP / ALL_TASKS_COMPLETE where HOLD / ATTEMPT_BOUND was required. This supersedes the earlier adequacy claim without erasing the previous test result.

The original delivered v1 diff remains separately available as R03_REVIEW_PATCH.diff, SHA256 83280c3d6ffe7647af0bd58b1a7d1ecbd7301a9324dc479c82644cdbe7a95b81. Historical Git evidence and trial artifacts are unchanged.

## Final observed checks

`python3 -B -m unittest phase2c_finite_autonomous_pilot.test_phase2c session_driver.test_r03_review_semantics -v`

Result: 10 test methods passed. Composition uses the actual patched producer, active parser, driver, bridge and queue with deterministic fake worker hooks and fresh temporary SQLite stores. No live worker method is called.

Coverage: seven invalid candidate forms (wrong schema, wrong boolean, integer/float for boolean, conflicting duplicate key, nonfinite constant and malformed JSON); valid ACCEPT with temporary destination readback; legitimate two-attempt REPAIR/ACCEPT; both attempt and call caps; token/hash/unsupported-REJECT mismatches without review mutation; committed REPAIR followed by injected lost acknowledgement without another invocation. Invalid candidates at the one-attempt cap create no sink application. New test connections close explicitly.

`python3 -B worker_bridge/test_bridge.py`

Result: PASS, 25 existing checks, rerun after the v2 producer correction. Includes binding, bounded repair, uncertain dispatch and delivery deduplication.

## Limits and next action

- Same-thread critical review is not independent or strict-blind review. A host/model change does not establish independence. Fresh external review remains pending before a transition requiring it.
- These Linux results neither establish Windows compatibility nor repair the historical six Windows cleanup failures. No Windows or live pilot was rerun.
- Evidence covers this bounded task-specific schema and composition. Direct upstream worker JSON equality checks remain outside this patch and retain weaker validation; no general conformance claim is made.
- Private parsing helpers are a source compatibility dependency. Reuse avoids another parser; later helper changes require regression review. No source pin was weakened.
- The existing driver remains a trusted serial-host controller, not principal authentication, independent execution proof or a monetary budget gate. Call counts do not guarantee invoices.
- UNKNOWN requires preservation and reconciliation. This patch adds no new durable guard against a caller improperly re-entering the driver after UNKNOWN.
- Pass186 inheritance, later NONCLAIM status, EXP010 and other scoped HOLDs remain unchanged.

Next R03 action: review this exact diff and contract. Publishing, integration, main merge and deployment remain outside authorization. Independent read-only R05/R06/R07 work may proceed; their source repairs require a separate scope.

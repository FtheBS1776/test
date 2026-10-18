# Separate source-only contract review

Disposition: NO_DEFECT_FOUND

This is a bounded review of the supplied selected source against its supplied
REVIEW_CONTRACT.md. No concrete contract violation was demonstrated. This is not
a claim that all requirements have complete runtime coverage. Native Windows and
the exact pinned MCP SDK/transport remain INDETERMINATE coverage on this host.

## Exact input and verification

- Input: `GENIE_REPAIR_REVIEW_INPUT_v5_20261018.zip`.
- Expected and observed outer SHA256:
  `c85056c21b14868eea476341bc64f9814dab8f70471eb79f9759499e65dcb51f`.
- Supplied source commit identity: `5327f897fd3874cf25326872730f68a0617333a2`.
- Supplied source tree identity: `be7f76873b671e5e9719efc330000d261d23e605`.
- The commit/tree above are declarations in the supplied manifest, not separately
  authenticated Git provenance or a claim that this selected tree is complete.
- All ZIP entries were checked for absolute/traversing/non-normalized paths,
  backslashes, duplicates and symlinks before extraction. CRC verification passed.
- All 53 manifest entries matched exact byte lengths and SHA256 values. The
  manifest file set exactly matched extracted files except the manifest itself.
  `01_manifest_verification.json` retains every exact individual identity and
  the manifest's own SHA256. `00_archive_verification.json` retains ZIP checks.
- README_FIRST.md and REVIEW_CONTRACT.md were read before subject module imports.
- All 53 input files were rehashed after testing and remained unchanged. No
  bytecode files were written into the input tree.

The exclusive review directory was newly created as
`/workspace/scratch/27265db857a2/review_v5_separate`.

## Boundary and attack model

Only the supplied source and contract were used. No parent repository, other
package/review, pre-existing project test, prior result, audit, history, memory,
outside description or author explanation was consulted. No further delegation
occurred. Tests were created from this source inspection, not copied from omitted
author tests.

The adversary here is malformed or identity-confused task/callback/tool data,
replayed reservations, changed quote aliases, uncertain hook outcomes and local
publication failures in the specified trusted serial-local host model. The
review does not extend that model to hostile store rewriting, concurrent hosts,
restored-store resistance, hostile filesystem races or authentic provider
invoices. Fresh disposable stores and deterministic fake workers/reviewers were
used throughout. An audit hook blocked process launches and socket connection or
binding if a tested path reached them. No subject main, workflow, live pilot,
provider, model turn, installation, deployment or publication workflow ran.
The publication tests used only fresh local fixture directory renames behind a
fake move collaborator; they did not publish application state or artifacts.

## Findings and reproduction evidence

No actionable defect finding was established. The independently created
`adversarial_review.py` contains eight test groups. There was one execution
attempt; its complete stdout is `attempt_01.stdout.jsonl`, stderr is
`attempt_01.stderr.txt` (empty), and detailed observations are also retained in
`test_records.json`. Exit code was zero. The final raw output was:

```json
{"tests": 8, "failed": [], "effects": "local deterministic fakes only"}
```

All fresh fixture stores remain under `fresh_stores/`; nothing was retried by
resetting, refunding or deleting stores. The test source itself creates fixtures
exclusively; to reproduce, use a fresh copy of this review directory without its
existing `fresh_stores`, not an existing subject store, then run
`python -B adversarial_review.py` from the review root. The preserved input source
and unchanged pins must remain in their supplied relative layout.

| Area | Independent attacks and observed result |
|---|---|
| Queue monetary admission | Unknown, boolean, negative, fractional and oversized bounds denied. Every token identity field was changed independently and denied. Changed approved quote bounds/references denied. First exact charge admitted, exact replay reconciled without permission, changed action binding denied. Author/reviewer/repair reservations shared a ceiling of 9; a fourth charge was denied and the charged total stayed 9. A stopped run and a queue with its cost schema absent granted no admission. Default driver cost configuration called no hook. |
| Driver identity and uncertainty | A fake exact candidate completed with one worker and one reviewer hook. Wrong worker call identity, unsupported review decision, wrong candidate hash and a throwing worker all returned UNKNOWN. Restarting each existing run invoked no hook and kept monetary reservations charged. A stop in the progress callback before hook entry prevented dispatch. |
| Deterministic task review | The exact attested marker object was ACCEPT. Numeric 0 and 0.0 in place of boolean false, visible tools, an extra field, duplicate keys, NaN, malformed JSON and a non-object became bounded REPAIR. A candidate hash mismatch became REJECT. A fake schema defect followed by an exact candidate exercised a valid two-attempt REPAIR then ACCEPT path through the real finite driver. |
| Material bridge | Missing, incomplete and hash-mismatched materials failed before any call reservation or hook. Correct text/hash/UNTRUSTED_TASK_INPUT labels reached both hooks. Mutation of the worker's detached material dictionary did not alter the reviewer's copy. |
| Read-only MCP and adapter | Exact two-tool catalog retained. Unsupported tool, oversized and nonfinite arguments rejected. Duplicate/nonfinite/overflow/non-object encoded arguments rejected. A downstream fake with wrong correlation, duplicate reply keys or unlabeled accepted data produced UNKNOWN. Reading a completed task labeled its result UNTRUSTED_ACCEPTED_TASK_DATA and left all three underlying store files byte-identical. Genuine pinned source loaders were used; no pin was disabled or rewritten. |
| Fixed live-state shape | Valid structural fixture normalized correctly without store reads. Traversal, absolute, reserved-device, alternate-stream-like, dotted and slash-containing child names rejected. Duplicate marker keys rejected. Known Folder API coverage was not synthesized as native Windows evidence. |
| One-time publication | With fake platform attributes/validation/move, a reported false move returned PUBLISH_UNKNOWN_PRESERVE and retained staging. Reported true move followed by failed validation returned PUBLISHED_UNVERIFIED_PRESERVE with final state retained. A valid fake publication returned PUBLISHED. Every session rejected a second publish before any second move. These are portable state-machine tests, not native MoveFileExW tests. |
| Paid-capable public entry points | `shared_interfaces.live_codex_worker.run_once`, `alpha_exec_worker.run_once`, `recovered_worker.run_once` and `attested_worker.run_once` returned LIVE_COST_BOUND_UNAVAILABLE with process_entry=false, preserve=true and allow_new_invocation=false, even with nonexistent executable/config/scratch paths and an invalid token. The fresh ledger directory stayed empty. |
| Sealed inspection | A fresh invalid terminal fixture failed with TERMINAL_INVARIANT and retained exact input bytes/file set. Inspection source uses read-only SQLite and closing handles; report-path restrictions were inspected statically because subject mains were prohibited. |

Selected concrete raw successful-path outputs:

```json
{"action":"STOP","background_execution":false,"counts":{"advances":4,"reviewer_hooks":1,"worker_hooks":1},"reason":"ALL_TASKS_COMPLETE","run_id":"run-fresh"}
{"action":"STOP","background_execution":false,"counts":{"advances":6,"reviewer_hooks":2,"worker_hooks":2},"reason":"ALL_TASKS_COMPLETE","run_id":"run-fresh"}
{"reason":"PUBLISH_UNKNOWN_PRESERVE","state":"UNKNOWN"}
{"reason":"PUBLISHED_UNVERIFIED_PRESERVE","state":"PUBLISHED_UNVERIFIED"}
```

The publication tests patched only platform/effect collaborators. The material
tests patched live registry discovery to fresh local records. MCP reply attacks
replaced a downstream adapter instance after genuine pinned construction. These
fake dependencies limit what each test establishes; they do not substantiate
native platform behavior or source-pin enforcement against a malicious host.

## Coverage limits and source-only observations

The most concentrated inspection was of the queue, active runner/journal/task
ledger, driver/events/controller, deterministic reviewer, read-only adapter/MCP
consumer/server, standalone owner/bridge, live-state binder, provisioner and
sealed inspector. Source read paths and pinned dependency relationships were
examined before relevant function execution. This was not an exhaustive audit of
every branch in every supplied file.

- Runtime: Linux x86_64, Python 3.12.14; full details are retained in
  `02_execution_metadata.json`.
- Native Windows Known Folder, ctypes ABI, Job Objects, COM ownership, reparse
  behavior and MoveFileExW semantics: INDETERMINATE. The actual Known Folder
  function rejected with LIVE_STATE_PLATFORM. Fakes do not clear this limit.
- Exact SDK/stdio runtime: INDETERMINATE. `_require_sdk()` rejected with
  MCP_SDK_VERSION_BINDING. No packages were installed, no version checks changed,
  and no transport was started. This missing capability was not counted as a
  source defect or native PASS.
- CLI classification, standalone first-run integration and plugin bootstrap were
  read statically, not run through their mains. The committed-stop response-loss
  branch, native first publication and live plugin transport were not exercised
  end to end. The owner's first-run path visibly uses queue initialization and
  the one-shot provisioner; the CLI's generic post-entry failure branch visibly
  produces UNKNOWN with no-new-invocation flags. These are source observations,
  not complete runtime proof.
- Sealed inspection's positive historical-evidence case and report creation were
  not executed; no archived evidence was supplied or reconstructed. Failed
  inspection immutability was tested. No crash durability, authenticity,
  hostile-path race, atomic report publication or rollback/currentness conclusion
  follows.
- Tests did not change subject source or pin constants. Neither scientific code
  nor live preflight launch functions ran. No paid capacity was used.

## Independence limits

This review was performed in a separate agent context on the same host and with
the inherited model configuration/model family as the parent review workflow
(GPT-6-family Codex context; exact backend identity is not independently
attested). The source and contract share their supplied ancestry. The fake tests
and this assessment share one reviewer/model's assumptions and can have common
errors. A separate role/context label is not an independent evidence root, and
neither the manifest nor the report authenticates project or provider history.
The result means no defect was found within the stated bounded review and test
coverage; the explicitly indeterminate native coverage remains unresolved.

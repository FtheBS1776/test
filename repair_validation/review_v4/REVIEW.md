# Source-only review

Disposition: DEFECT_FOUND

The exported alpha Codex worker still bypasses the required cost gate. A deterministic local reproduction reached its real operation-ledger claim and its fake process-launch boundary without any quote, queue, authorization reference, reservation, or enforceable charge bound. No actual child process or provider was invoked.

## Input identity and integrity

The sole review input was `/workspace/scratch/27265db857a2/GENIE_REPAIR_REVIEW_INPUT_v4_20261018.zip` (138,234 bytes). Independently computed SHA-256:

`acaa546b3aa8abab8947b821c6bbe5c2c9f962e05d02c763929e5ddf4a274b0d`

This exactly matches the caller-provided expected value. The archive has 51 entries, 388,131 uncompressed bytes, 126,164 compressed-entry bytes, and a 25,136-byte maximum entry. Paths are unique, canonical relative paths without traversal, backslashes, drive syntax, normalized/casefold collisions, or symlinks. Every entry was fully read and all CRCs passed. All 50 manifest-listed files match both their declared byte lengths and independently computed SHA-256 hashes; there are no missing or unlisted payload files. The manifest excludes itself as described.

The manifest's own independently computed SHA-256 is `96a04051b84c6307589426c96c221c1c70c2aaa153bcecd46b885ef3e22d4373`. Its declared source commit is `51ffb4274d91de9769cb45dc13ab9641abe9de4b`; declared source tree is `d6e345245a2f018cd9bc42efed7c840a9fac3c98`. These are package declarations, not independently authenticated repository ancestry. `manifest_verification.json` preserves every recomputed individual file identity. `verify_input.py` and `input_verification_final.json` preserve the repeatable complete verification and confirm the extracted payload still matches the ZIP byte for byte after testing.

Extraction used a newly, exclusively created `review_v4_separate` directory. README_FIRST.md and REVIEW_CONTRACT.md were read before any subject source execution. No parent repository, alternate input package, historical fixtures, existing tests/logs, project memory, prior review, or outside project description was consulted. No subject source was repaired.

## Attack model

The contract establishes a trusted serial local host and owned local stores. I attacked accidental authority widening through malformed and aliased identities, unknown effects, replay, incomplete cost configuration, mismatched quotes, exhausted shared ceilings, stopped runs, untrusted JSON, changed materials, source-binding failures, and uncertain publication outcomes. I did not assume a hostile operating system, adversarial filesystem races, authenticated provider invoices, store rollback resistance, or cross-store atomicity.

All runtime inputs were newly created, deterministic local data. Workers and reviewers were local functions. The finding uses a plain text fake executable that is hashed but never executed, a fake Windows Job object, and a Popen sentinel that raises before any OS process creation. Subject source/version pin checks remained enabled. Tests that deliberately supplied wrong source bytes verified rejection rather than disabling pin enforcement.

## F-01 — exported alpha worker permits unbounded execution entry

Severity: High within the supplied trusted-local contract.

Affected file: `source/phase2b2m_alpha_live_pilot/alpha_exec_worker.py`, SHA-256 `644ea76b5c09fea1de50338751f68dc08efb050d371370c92a768552054d0021`.

`run_once` starts at line 226 and is expressly exported in `__all__`. At lines 229–238 it resolves/hashes the caller's executable, constructs `OperationLedger`, and calls `ledger.claim`. At lines 240–241 it writes `output-schema.json`; at lines 249–256 it constructs `WindowsJob` and invokes `subprocess.Popen` with the Codex model command. There is no cost admission call or denial guard before these operations, and its signature accepts no queue-bound cost context. No reviewed enforceable total-charge bound is established on this path.

This violates the requirement: “Current public Codex entry points deny before process/ledger entry while total exposure lacks a reviewed enforceable bound.” The distinction is observable in the same supplied package: the public `shared_interfaces.live_codex_worker.run_once` and `phase2b2s_attested_live_pilot.attested_worker.run_once` both return `LIVE_COST_BOUND_UNAVAILABLE` before creating a ledger or entering a process. Those two paths passed the negative-entry probe. They do not mediate the separately importable/exported alpha entry point.

Reproduction:

1. Create fresh sibling scratch and evidence directories plus a plain text fake executable file.
2. Call the actual alpha `run_once` with those valid local paths, a deterministic fake token/version, and no costs, authorization reference, queue, or reservation.
3. Replace only native WindowsJob/Popen effects with deterministic fakes. The fake Popen inspects the real newly created ledger and records `[('CLAIMED', 1, 0)]` before raising `DETERMINISTIC_FAKE_STOP_BEFORE_OS_PROCESS`.
4. Observe the schema file, the recorded command containing `exec --model gpt-5.6-sol`, and the returned `UNKNOWN/POST_ENTRY_UNCERTAINTY` with `evidence.process_entry=true` and `semantic_release=false`.

The observed process-entry flag belongs to the subject's boundary bookkeeping; it is not a claim that an OS process ran. The fake Popen was reached and stopped execution before native spawning. Actual Windows behavior and provider billing were neither exercised nor needed to establish the missing pre-entry gate. Returning UNKNOWN and preserving the operation afterward does not provide the required denial before ledger/process entry.

Independent reproduction source: `review_tests.py`, method `test_DEFECT_alpha_exec_bypasses_cost_gate_and_enters_ledger_and_popen`. Raw reproduction: `finding_reproduction_output.txt` and `stores_finding_final/test_DEFECT_alpha_exec_bypasses_cost_gate_and_enters_ledger_and_popen/reproduction.json`; the adjacent real SQLite ledger and scratch schema are preserved. An earlier complete reproduction is also preserved in `finding_alpha_exec_reproduction.json` and its corresponding stores. No repair was attempted.

## Coverage and results

The completed suite contains 24 tests; `test_output_complete.txt` records `Ran 24 tests ... OK` and exit status was zero. One passing test deliberately asserts the unwanted boundary entry to reproduce F-01; passing the suite therefore does not mean the subject satisfies the contract. `finding_reproduction_output.txt` separately records the final focused reproduction using the final test source.

| Surface | Exercised evidence and result | Limits |
|---|---|---|
| Queue monetary admission | Unknown costs deny hooks; unapproved zero quotes deny; quote aliases/replay grant no new invocation; shared 10-unit ceiling prevents the second 7-unit action; absent legacy cost schema denies. | Trusted quote correctness remains a precondition; no invoice or concurrency claim. |
| Driver/events/bridge identity | Every token field mutated independently; reviewer token/hash mismatches and unsupported decision produce UNKNOWN without completion. Unknown worker retains the reservation and gets no second worker hook on replay. Wrong configured run identity reserves nothing. | Targeted deterministic cases, not exhaustive state-space proof. |
| Valid progress and repair | Valid exact task JSON completes; a bound schema mismatch permits one authorized repair and subsequent completion. | No model was involved. |
| Deterministic task review | Exact marker/object accepts; numeric zero/zero float/null/true/nonfinite/overflow/duplicate/trailing/malformed/non-object/nonempty-tool variants produce repair feedback when hash-bound; candidate-hash mismatch rejects. | Tests target the actual PilotHooks reviewer, not the disabled live parser's historical acceptance code. |
| Operator stopping | Stop after progress prevents worker dispatch; stop during a returned worker hook prevents reviewer dispatch; reservation remains charged. | In-flight cancellation is not asserted. CLI exception mapping was inspected in source only; no CLI main was executed. |
| Standalone owner/material bridge | Bad create specs fail before staging acquisition; bad/missing/extra/hash-mismatched materials reserve nothing. Valid detached material reaches both hooks with original token identity. Source pin failures block owner/bridge entry. | Native first-run publication was not exercised. |
| Read-only consumer | Exactly two tool names; strict JSON/UTF-8/argument bounds; rejected mutation name; mismatched reply correlation becomes UNKNOWN; confirmed accepted data retains the untrusted-data label. Five repeated reads leave all fresh store bytes unchanged. | SDK transport unavailable as described below. |
| Windows state binding | Pure binding validates a fresh root; traversal, absolute path, separators, reserved names, stream syntax, trailing dot, and duplicate registry keys reject; valid reads leave bytes unchanged. Fixed Known Folder selection and environment independence inspected in source. | Native Known Folder/COM/reparse behavior is INDETERMINATE on this Linux host. |
| One-time publication | Fakes exercise existing-final preservation, failed-move preserve-only UNKNOWN, move-success/post-validation-failure committed-but-unverified classification, and closed-session replay refusal. | Native MoveFileExW and Windows visibility behavior are INDETERMINATE. Fakes establish Python branching only. |
| Sealed inspection | Failed invariant inspection preserves every supplied fake input byte. Read-only SQLite ownership/closing and explicit external exclusive report-path guards inspected in source. | Successful scientific/historical sealed evidence was not supplied or reconstructed. No subject main/report publication was executed. |
| Plugin composition/build source | Entry binding precedes self-test/transport; shared read-only server/stdio ownership, fixed live root, absent bundled state, and package manifests inspected. | Frozen Windows executable, installation, lifecycle, native SDK sessions, and workflows are INDETERMINATE/unexecuted. |

The actual host was Linux (`os.name=posix`), Python 3.12.14, kernel `Linux-6.18.55-x86_64-with-glibc2.39`. The unchanged SDK check raised `MCP_SDK_VERSION_BINDING`, so pinned native MCP SDK/stdio semantics were not dynamically covered. No substitute SDK or dependency installation was used. All 38 supplied Python files were parsed without executing subject main functions; `source_inventory.json` records the inventory. Static inspection is not equivalent to runtime platform validation.

No workflows, installations, deployments, scientific programs, providers, live-pilot mains, paid calls, promotion, publication, or external writes were executed. Test logs and fresh stores from all test attempts remain present. `test_output_initial.txt` includes an early harness error from supplying an invalid scratch directory to the unguarded alpha path; the later valid-input reproduction resolves that uncertainty. `test_output_final.txt` is an incomplete capture and is not used as the complete-suite result; `test_output_complete.txt` is the complete preserved raw run.

## Separate-context limits

This was a fresh separate source-only review context with independently derived tests, not a claim of independent evidence roots. The same platform, model family, host, and common ancestry can share correlated mistakes. A separate role or model label does not establish independent evidence roots. Archive hashes establish byte identity, not source authenticity, custody, scientific validity, or correctness. The finding establishes a concrete contract violation; uncovered native capabilities remain INDETERMINATE rather than PASS or automatic defects.

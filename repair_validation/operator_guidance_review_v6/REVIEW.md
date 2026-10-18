# Operator-guidance review v6

**Disposition: NO_DEFECT_FOUND**, bounded to the six supplied operator documents and the requirements in `REVIEW_CONTRACT.md`. No concrete current-guidance contradiction was found. This is a separate-context documentation review, not a strict-blind runtime audit, provider-cost certification, installation receipt or authorization to launch models. Native Windows/SDK/user-host compatibility remains untested by this review.

Review agent: `/root/operator_guidance_review_v6`; date: 2026-10-18 UTC. Only the supplied archive and the three explicitly permitted official pages were read. No parent repository/history, other packages, author tests/results/logs/triage, memory or additional agents were consulted.

## Exact identities

Input: `GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018.zip`, 178202 bytes.

Outer SHA256: `e2fd22c1b50698de5afc4539e3604ff8207aca3b2012182ef30ee239625c10f5`.

Manifest SHA256: `42fa20de5fdaea750707a98079a5a438b38ad6cf03ae036929066df8b65e45c0`.

Manifest-declared source commit `57b5da491562c0edd476596da74a2923eb472b8d`, tree `42a16574860ae2d6b0f644c0ea6c81783fe17153`: identity labels only, not independently authenticated Git evidence.

Paths below are relative to the archive root; these are the exact documentation subjects:

| Path | Bytes | SHA256 |
|---|---:|---|
| source/README.md | 27182 | `8519432ecdcaeaf560adbf52d0bb6d29ff9d7630db92f6bfad911f3fa8ec60a0` |
| source/active_runner/README_FIRST.md | 2593 | `276a0a4f4656fac8be29528fa050b5c59682a750702f17770fcc22408aad886f` |
| source/run_queue/README_FIRST.md | 5007 | `40c8424b3212d11fbccb286660917134540734f323fa6db0fd4b3ad1f53dc890` |
| source/worker_substitution/QUICKSTART.md | 15070 | `843fbbfe56076d127e6a8f40eae0619906d09d4a9482a5d2e78311701c58a94a` |
| source/session_driver/USAGE.md | 7930 | `7268bc97eae51376e2c5cea2599f2d8e93a5570907cfebcf30aa84e9a5c3f946` |
| source/desktop_plugin/README_FIRST.md | 7920 | `3a8299e6f182e2f3780b8aa96d4bf70949bac755d486f63691f8ed2232a9a6ae` |

## Integrity and procedural limitation

`integrity.raw.json` records all 60 unique canonical ZIP members, no symlinks, successful CRC, all 59 manifest payload lengths/hashes, the exact payload set and equality with the original extracted bytes. The full manifest excludes only itself. The original selected input, including manifest and contract, remains in `input/`.

**The initial extraction order deviated from the supplied README.** Outer hash, path/uniqueness/symlink/CRC checks preceded extraction, but full manifest verification did not. The supplied README, contract and manifest were then read; the complete manifest and extracted-byte equality were checked before subject documentation/source review or execution. `INITIAL_PROCESS_RECORD.md` preserves the original commands/program and clearly labels its transcribed observations; it is not original raw stdout. The original extraction was preserved.

On explicit parent follow-up, `verify_then_extract_again.py` performed complete manifest verification directly from ZIP before creating a second exclusive extraction. `ordered_followup.raw.txt` preserves PASS and equality between all 60 archive members, initial inspected bytes and `verified_second_extraction/`. This verifies unchanged identity in the required order and does **not** erase or retroactively cure the initial ordering deviation. No checks were broadly rerun.

## Attack model and findings

The relevant failure is an operator following current instructions into external worker/reviewer entry from a workflow offer, progress message, unapproved quote, uncertain replay or stopped run; or mistaking deterministic/historical/package observations for useful model reasoning or account compatibility. Host-provided bounds and quote provenance are trusted preconditions. Hostile host bypass, arbitrary historical scripts, rollback, concurrency and external authenticity are outside the documented enforcement claim.

No blocking contradictions were found:

- The root's current section and actual host sequence, active-runner guide, queue guide and quickstart route external entry through the existing shared driver and immutable approved role quotes. They expressly separate workflow reservation from monetary admission and progress from entry. `shared_interfaces/session_driver.py:drive_run` validates/binds the action, checks RUNNING and calls `_admit` before either hook. `run_queue/run_policy.py:admit_action` owns durable monetary reservations in the same queue; it denies unknown bounds, quote mismatch, stopped entries and replay. No new authority/budget owner is documented.
- `session_driver/USAGE.md` gives the matching callable/stream signatures, costs argument, role names and default fail-closed behavior. Its response envelopes, token/candidate binding and byte bounds match `session_driver.py`, `run_control.py` and `run_events.py`. `work_host.py` exposes registry/run/max-actions only and invokes `serve_run` without costs, matching the documented inability to authorize hook entry.
- Reviewer admission is distinct from author-attempt slots. The driver uses role `reviewer` and operation `review:<candidate_sha256>` for each eligible review; author/repair use `worker`. The documents retain original token/hash bindings, charged uncertainty, valid ACCEPT and bounded REPAIR. They do not promise arbitrary replay or refunds.
- Static inspection of the four exported `run_once` paths (original, alpha, recovery and attested) shows the unknown-bound call to the same queue owner and `LIVE_COST_BOUND_UNAVAILABLE` return before later process/ledger work. These adapters were not invoked in this review. Their availability is not inferred from old source receipts.
- Plugin current guidance matches `entry.py` and `live_state_windows.py`: existing fixed Windows canonical root, no seed/cache fallback, read-only status/result projection and no model dispatch. Root continuation explicitly keeps useful model work and plugin compatibility separate. Hosted VM, source and packaging evidence are not presented as account/user-computer connection evidence.
- A competing reading is that the plugin's later “Next boundary” or root's older continuation text authorizes outdated operation. The plugin explicitly marks that whole package record historical/superseded, and the root current section explicitly supersedes older next-action wording. Under the supplied contract these are preserved historical scopes, not current contradictions. Old hashes were not demanded to match maintained runtime.
- The no-model quickstart is clearly labeled a simulated protocol exercise. Historical review/test counts and purported earlier successful/failed runs in the subject were treated as unverified claims to assess for scope, never acceptance evidence. The subject retains scoped HOLDs and common ancestry; it does not promote deterministic callbacks to useful autonomous reasoning or create scientific/runtime acceptance from a doc edit.

## Actual validation and raw evidence

Linux x86_64, Python 3.12.14. `fresh_guidance_checks.py` was written from the inspected source and executed once with `python -B`. No subject main, embedded recipe, historical fixture, child process, model/provider, SDK transport, installation or workflow was executed. Original transitive source-pin checks remained enabled; source files were not edited. All fresh SQLite stores and complete stdout/stderr are retained.

`fresh_guidance_checks.raw.jsonl` ends with `PASS`, eight fresh scenarios; stderr is empty:

| Fresh scenario | Observed result |
|---|---|
| Omitted costs | INVOKE_WORKER progress emitted, then unknown-bound HOLD; zero hooks/cost actions, one preserved workflow slot. |
| Approved zero quotes | One fake author and reviewer entered; two distinct zero-cost action records, one author slot; exact accepted delivery completed and STOP persisted. |
| Asserted unapproved zero | COST_QUOTE_NOT_APPROVED; zero hooks/cost actions. |
| Reviewer lacks quote | Author admitted once; review denied before hook; one monetary record/author slot. Reentry reconciled review with zero hooks. |
| Hook raises after admission | UNKNOWN; monetary charge and slot retained; reentry reconciled original worker with zero new hooks. |
| Valid bounded REPAIR | Two author attempts and two separate reviews; roles author/reviewer/repair/reviewer; four charged monetary records, two workflow slots; valid ACCEPT and STOP retained. |
| Stop at progress | Run stopped before admission/entry; zero hooks/cost records despite prior workflow offer. This test callback deliberately stops the local queue; it performs no external work. |
| Stream without costs | Only progress and terminal HOLD, no worker/review request; omitted configuration fails closed. |

Function signature assertions and `LINE_LIMIT == 160000` also passed. These deterministic observations validate selected guidance behavior, not actual LLM reasoning, invoice bounds or the full runtime suite. No earlier author suite was rerun.

The exact allowed official pages were opened on 2026-10-18; retrieved output is retained in `official_docs_open.raw.json` and `official_docs_find.raw.json`. Narrow paraphrases supporting the plugin prerequisite wording:

- https://developers.openai.com/plugins/deploy/desktop-only — local execution and locally running desktop threads for desktop-only plugins.
- https://learn.chatgpt.com/docs/plugins — desktop-only plugins require the desktop app and are unavailable on mobile.
- https://learn.chatgpt.com/docs/extend/mcp — local STDIO/configuration is documented; cloud access to local servers/transports is conditional and separately checked.

These pages establish product prerequisites only. No linked page, broader source, paid connector or package/account compatibility test was used.

## Decision limits

NO_DEFECT_FOUND supports only the bounded current operator-guidance disposition above. The incomplete selected application and unavailable author evidence prevent independent historical-claim confirmation. Native Windows APIs, compiled package behavior, actual SDK connection, user account/client/computer, provider-price provenance, enforceable real external-action bounds and useful-model task completion were not tested. Missing native/SDK ability is untested, not an automatic defect or PASS.

The review uses a separate task context but shares the parent execution host/filesystem and inherited model/model-family ancestry. Exact model identity was not independently attested. Supplied historical claims necessarily create subject-text exposure; author/reviewer/controller roles and the same supplied runtime retain common-cause risk. Neither different role names nor fresh deterministic stores establish independent evidence roots. This report grants no paid capacity, live pilot, deployment, binary publication, main merge, promotion, freeze, master mutation or scientific execution.

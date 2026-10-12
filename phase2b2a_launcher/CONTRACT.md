# Phase 2B2A fixture-launch contract — NONCLAIM

## Accepted boundary

`NoModelFixtureWorkerLauncher.launch_worker(launch_id, request)` accepts one lowercase 64-hex parent-owned launch ID and one exact request object with `instruction`, `materials`, and `constraints`. Types, field counts, NULs, individual UTF-8 sizes, and a 65,536-byte canonical envelope bound are checked before a claim. The strings are opaque. `BOUNDED_PARENT_REQUEST_UNVERIFIED_CONTENT` means the launcher does not prove semantic sanitization or absence of secrets, paths, tokens, or instructions.

The immutable local profile binds:

- exact Phase 2A CPython path and executable SHA-256;
- `-I -S -B` startup flags;
- exact repository fixture path and fixture SHA-256;
- fixed argv with a closed mode enumeration and no request text in argv;
- `shell=False`, closed file descriptors, pipes, and a fresh non-repository child directory;
- an environment built from scratch containing only `GENIE_EXECUTION_CLASS` and Windows `SystemRoot`/`WINDIR` when present;
- a disposable launcher root under the local temporary directory and one fixed claim-store filename.

No caller can select arbitrary argv, environment keys, child cwd, fixture path, interpreter path, or claim filename through `launch_worker`.

## Claim and result semantics

The launcher opens the fixed SQLite store with `BEGIN IMMEDIATE`, creates or verifies one exact table with no extra table/index/view/trigger, and commits `CLAIMED` before process creation. Existing non-SQLite, aliased/hard-linked, malformed, extra-object, or integrity-failing stores are rejected without replacement.

The launch ID is the trusted parent's stable logical-operation identifier. In the same fresh, untampered store, its reuse—including with crossed request content—returns canonical `UNKNOWN` and never spawns again. A new launch ID or new store is a new trusted-parent decision and can spawn the same request again. Therefore this is launcher-local same-ID suppression, not global at-most-once or caller-proof no-retry enforcement.

Preclaim input/profile failures return `REJECT`. Once a claim may have committed, handled crash, timeout, nonzero exit, pipe/cleanup failure, `KeyboardInterrupt`, malformed/duplicate/nonfinite/oversize output, validation mismatch, or lost return-recording produces exactly:

```json
{"allow_new_invocation":false,"preserve":true,"reason":"ISOLATED_WORKER_OUTCOME_UNKNOWN","status":"UNKNOWN"}
```

The launcher has no retry, refund, reset, replacement, or claim-deletion path. `SystemExit`, forced host termination, power loss, or process kill can prevent any domain return; a persisted same-ID claim remains suppressive on later readback. A valid response is `RETURNED / UNTRUSTED_NO_MODEL_FIXTURE_OUTPUT / NO_MODEL_CALL`; it is not a worker observation, model result, provenance, truth, quality, callback acknowledgement, review, delivery, or completion.

## Explicit boundary limits

The implementation makes one direct-child kill-and-bounded-reap attempt on transport uncertainty; cleanup failure remains `UNKNOWN`. It does not install a Windows Job Object and does not prove descendant-tree control. Source and claim files are revalidated near use, but check/use cannot be atomic through Python path APIs; concurrent same-user filesystem replacement remains outside the trusted-local-filesystem assumption. The pinned fixture source has no subprocess, network, OpenAI, or Codex path, but the executable hash does not pin the full CPython, standard-library, Windows, or filesystem closure. A minimal environment is not a hostile OS sandbox. Same-host hashes and tests are common-cause local evidence, not independent verification or future currentness.

`deferred_codex_worker_plan()` verifies the reviewed local Codex 0.162.1 executable path/hash and returns a non-executable argv template. It performs no spawn, authentication, model/provider selection, effective-tool probe, or isolation proof.

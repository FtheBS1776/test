# Phase 2B2 test and execution results

## Predesign and regression

- Published frontier independently verified: branch
  `nonclaim/genie-phase-2b2b-containment-preflight-20261012`, commit
  `c147d06b242539cb80da5e8ca115828acfef954b`, tree
  `ae0f5bc4e3b2c1ce01b43f83a4ea3abfbf97d219`.
- Accepted Phase 2A/2B1/2B2A/2B2B files were unchanged.
- Exact accepted CPython 3.12.14 environment: 137/137 focused and regression
  tests passed after evidence packaging (the prior 129 plus eight Phase 2B2
  tests), zero skips.
- New adversarial checks cover every token field in logical identity, duplicate
  and replacement claims, secret-free environment construction, explicit
  feature disables, nonempty/paginated MCP rejection, exact/duplicate result
  rejection, post-entry assignment failure, and uncertain `Popen` with exactly
  one attempt.

## Sole live process entry

- Logical operation:
  `55e73a140f052d840d6fbe0cb1c1710e10c5189af8a9f597a5c58fc4b6fb6d12`.
- Root PID: `48008`; assigned to the Job before protocol/semantic release.
- Result: `UNKNOWN` (`APP_SERVER_EOF`) during initialization.
- `semantic_release=false`; no thread/turn was started and no model result was
  produced.
- The Job termination path was attempted once; retry count is zero.  Fresh OS
  process-table readback later found PID 48008 absent, but this is not a claim
  of complete Job-member evidence.
- Durable ledger readback is `UNKNOWN`, `preserve=1`,
  `allow_new_invocation=0`.  Genie remains `WAITING_WORKER`; fresh destination
  readback is `UNKNOWN / TASK_RESULT_UNAVAILABLE`; no acceptance callback or
  statement occurred.

## Defects found and bounded repair

The failed command placed global Codex flags after the app-server subcommand,
used the trial directory as child cwd, did not preserve stderr/member evidence
on the early-failure path, and set the closed Python process handle to `None`,
causing a destructor warning.  The unexecuted postmortem repair orders global
flags before the subcommand, requires a separate empty scratch directory that
is neither ancestor nor descendant of the Genie trial, captures bounded failure
stderr/member/accounting evidence, and closes the handle without rebinding it.
Tests pass on the repaired source, but the repair was deliberately not validated
with another Codex process because the original logical operation forbids retry.

The four pilot databases are retained byte-for-byte with `.preserved` suffixes;
their sizes/hashes are in `trial/PRESERVED_STATE_MANIFEST.json`.  Renaming them
after final read-only inspection keeps the accepted 27 historical `*.sqlite`
files and their aggregate integrity unchanged; it does not reset their content.

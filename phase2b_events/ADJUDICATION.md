# Phase 2B1 root adjudication — NONCLAIM

**Decision: ACCEPT the bounded event-transport candidate; stop before live dispatch or persistent callback.**

The implementation reuses the unchanged accepted `GenieRunEvents` primitive through a distinct stdio MCP process exposing exactly `apply_run_event`. Source and canonical schema are hash-pinned, the MCP closure is exact, annotations accurately mark a write/destructive/non-idempotent closed-world tool, and both projection layers independently validate result shape, requested-operation correspondence, review-decision correspondence, and canonical UNKNOWN preservation.

The adversarial suite kills extra-tool, annotation, schema, source-pin, dependency-pin, crossed-token, malformed/weakened-output, operation/decision mismatch, delegate-mutation, retry, HTTP, dispatch, driver, progression, and unsafe-text mutants. Independent read-only review found no remaining code blocker. The accepted test set is 83/83.

The real local stdio evidence is transport evidence with deterministic synthetic inputs on disposable stores. `APPLIED` records callback acknowledgement only. The harness-provided agent/evidence/candidate/ACCEPT are not a model execution, authenticated provenance, truth, independent review, user authorization, completion, delivery, or currentness claim. “Controller-only” remains a trusted configuration assumption.

Phase 2A and `genie-readonly` remain byte-identical at their recorded aggregates. The charged Phase 2A run is untouched. No persistent Phase 2B1 run, global registration, model invocation, session driver, automatic progression, HTTP endpoint, main merge, spending, promotion/freeze, or EXP010 activity occurred.

The next boundary is Phase 2B2: a separately authorized live isolated worker/reviewer pilot. It must keep Genie tokens and all mutation tools in the parent controller, prove the child’s effective tool inventory, preserve no-retry semantics, and retain the same-model/common-cause NONCLAIM. Phase 2C autonomous driving remains later.

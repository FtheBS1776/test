# Genie operator quickstart — bounded prototype

## Goal and present capability

Genie aims to support useful work that survives interruption while preserving reasoning, review and adjudication roles. One-LLM operation is the next useful path; more roles do not establish model diversity or evidential independence.

The completed hosted fixture deterministically turns a verified pending-transaction result into one report-inbox item. `report_worker.py` produces fixed Markdown bytes; the host recomputes them and binds input, result, program and execution identities. An unchanged authority adapter commits head, receipt, execution and outbox records atomically. A separately provisioned SQLite sink stores the report and application record together, rejects mismatched retries, and compares full destination contents before completion. Worker stdout cannot authorize completion. The exported `REPORT.md` is a view of that stored report, not another delivery.

## Exact evidence identity

- Repaired R2: run **37575403051**, source **8a676ca5dddbbaff3d4e286ee3f256605a7341b6**.
- R2 artifact SHA-256: **31729b27549fe35065d229aa0ae0401ff01acd8e0a90591fcba28eadf5e713a2**.
- Preserved attempt01: run **37550186839**, source **4e93fb1e3793fc5fef009cf97729c7908079de97**; original precheck **FAILURE**, before provider preparation.

`R2_ADJUDICATION.json` reports bounded PASS and eight rejected semantic mutations; the controller reports successful local replay. This guide's author inspected source and that adjudication, but did not independently replay or execute the fixture. The canonical roadmap now marks this bounded deterministic integration COMPLETE for R2. Preserve the failed run alongside the repaired run.

## Offline inspection and replay

Use a reviewed, identity-checked source directory and an already downloaded, safely extracted R2 capture. Use the tested Python 3.12 interpreter (host: 3.12.3; local replay: 3.12.14), with SQLite support, the existing `cryptography` dependency, all source modules and `VERIFIED_INPUT.json`, and the complete observations tree including its SQLite database. No etcd binary, provider account or network is needed for semantic replay. If prerequisites are missing, stop at that dependency boundary.

Before executing Python, inspect archive inventory/path safety and compare the original artifact hash, captured job/source identity, workflow, source manifest and capture manifest against trusted records. A manifest bundled with its own files is not independent authenticity evidence. Review the verifier and imported modules; never execute returned capture code simply because it includes a verifier.

Set paths explicitly to the reviewed source, captured observations and a fresh output directory outside the capture:

```bash
GENIE_REVIEWED_SOURCE=/absolute/path/to/reviewed/agent_demo
GENIE_OBSERVATIONS=/absolute/path/to/R2/observations
GENIE_REPLAY_OUT=/absolute/path/to/fresh/replay-output
mkdir "$GENIE_REPLAY_OUT" &&
python3.12 -B "$GENIE_REVIEWED_SOURCE/verify_demo.py" \
  "$GENIE_OBSERVATIONS" --output "$GENIE_REPLAY_OUT/verification.json"
```

Expect exit 0, `status: PASS`, eight rejected negative controls, one authority transaction, three delivery attempts and one application. The verifier checks evidence inventory, bindings, chronology, authority bytes and fresh read-only database contents. It reads `VERIFIED_INPUT.json` and program hashes beside its own source. Any rejection remains a rejection; preserve output rather than editing evidence to pass. Do not place replay output inside observations: that changes its inventory.

After successful replay, optionally run the reviewed local sink checks, protecting any existing result:

```bash
test ! -e "$GENIE_REPLAY_OUT/sink-tests.json" &&
python3.12 -B "$GENIE_REVIEWED_SOURCE/test_sink.py" \
  --output "$GENIE_REPLAY_OUT/sink-tests.json"
```

This exercises ten local sink checks using temporary databases and child processes; it does not repeat hosted integration. Do not run `run_capture.py`, `run_demo.py` or `coordinator.py` for offline replay: those paths prepare or contact the provider.

## Task, attempts, effects and recovery

The fixed task/transition is `genie-report-task-01`; its execution identity ends in `-execution`. Its effect ID derives from that task, `publish` and `genie-report-inbox`. Three delivery attempts are retries of one effect, not three tasks or applications.

The first sink commits then exits 73 without acknowledgement; coordinator one exits 75 before readback. Fresh coordinators resume and repeat with the same persisted plan, candidate and identities. Both receive `DUPLICATE`, then independently read the exact destination before marking completion. Missing or uncertain destination evidence stays UNKNOWN. Do not create a new effect ID, silently recreate a missing sink, or trust cached completion. These restarts occur within one owned fixture lifetime, not after arbitrary infrastructure loss.

## Scope and next direction

This guide is an in-session model-authored candidate for separate review/adjudication; it is not the hosted deterministic worker, which made zero runtime LLM calls. Neither finite host supplies an always-on service. Arbitrary generated-text correctness, hostile-worker confinement, authenticated remote receipts, production administration, whole-store rollback recovery, physical-power-loss durability and universal exactly-once effects remain unsupported. Production acceptance, promotion and freeze are not authorized.

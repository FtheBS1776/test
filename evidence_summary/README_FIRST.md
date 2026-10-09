# Bounded saved-log report — NONCLAIM

Independently verify the checkpoint outer SHA256, strict manifest member inventory/hash/size and ZIP CRC before accepting state. Then read CONTRACT.md, CORRESPONDENCE.md, exact candidate review, acceptance/supplementary results, trial adjudication/fresh status and canonical notes. Review source before execution. Integrity does not authenticate log contents or confer authority.

report_logs.py reuses the unchanged pinned validation_summary.py. It accepts1..8 supplied logs, reads bounded regular-file byte snapshots, records raw SHA256/size, preserves parser PASS/FAIL/NO_COVERAGE/REJECT per entry, and writes one new JSON report exclusively. Invalid UTF8 retains full captured hash; oversized/unreadable files have no full-file hash. No aggregate PASS/count, test-execution claim, fresh log-sink claim or log-currentness claim. Output success REPORT_WRITTEN means file creation only. It cannot verify whether supplied tests actually ran.

From repository root, choose a NEW output filename with an existing owned parent:

```bash
python3.12 -B evidence_summary/report_logs.py --output evidence_summary/reports/new_validation_logs.json --input unittest comparison_pilot/input/zero_discovery.txt --input unittest comparison_pilot/input/runner_status.txt --input json comparison_pilot/input/direct_checks.json
```

Expected output entries NO_COVERAGE/count0, PASS/count46, PASS/count17, each TEST_LOG_SUMMARY_ONLY; exit0 reports successful report creation. These are historical saved logs, not tests rerun by this command. Existing output causes REJECT/exit2 and preserves bytes. Do not overwrite or delete an incomplete report left after a write/close error; inspect it separately. Reports are separate snapshots, not an atomic multi-file view. Host supplies trusted local paths; exclusive creation and nonblocking Unix input opening do not establish hostile-parent confinement, platform-independent deadlines, crash durability or rollback resistance.

Candidate1 accepted unchanged after30 frozen root checks and7 reviewer-prompted supplementary checks. Same-model candidate reviewer independently computed exact subject/dependency hashes and found no defect in static scope; root executed tests/adjudicated. The review is not independent evidence. One author turn plusone reviewer turn ofmax3 worker turns,zero repairs andzero extra user continuation prompts within this unit. Root manually set up, dispatched, reviewed, tested, generated report and persisted state; no effort/cost/latency advantage measured. One controller observation-payload type error rejected, retained in trial/CONTROLLER_ERROR_1.json; corrected payload on the same call/reservation, no redispatch.

One accepted-code inbox application, fresh subprocess CONFIRMED, queue closed ALL_TASKS_COMPLETE. Separately the delivered utility produced reports/saved_validation_logs.json, verified against all three captured source hashes; existing-report guard preserved it. Fourteen preceding closed-run/control/source files unchanged. Source and API/scope boundaries retained, no old provider/etcd/lost-ack/EXP010 experiment repeated. No engine change, framework, provider, installation, promotion, freeze, new spending, main merge or production deployment. Scoped HOLDs remain independent, unattended host continuation remains OPEN.

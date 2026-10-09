# Matched useful task pilot — NONCLAIM

Start by independently verifying the checkpoint outer SHA256, strict manifest inventory, sizes, member hashes and ZIP CRC. Read PROTOCOL.md, PRE_RUN_FREEZE.json and RESULTS.json before accepting state. Source review precedes executing code; this archive's integrity is not authenticity or semantic proof.

One matched validation-log summarizer task, ordinary one-model practices versus the existing Genie runner. Both candidates passed 51/51 frozen checks on attempt1, required zero repairs, rejected 4/4 common wrong-metadata probes, resumed the saved worker record in a fresh coordinator process without relaunch, and reached fresh exact delivery confirmation. Tie on these measured outcomes; no general superiority or measured labor/cost/latency saving. One design reviewer plus two author turns,3/5 maximum worker turns used. Root static review, tests and adjudication are distinct from the design reviewer. Same model/host/shared ancestry; procedural file scopes are not hostile isolation. Host stayed alive; no unattended service or host-death recovery tested.

Plain baseline had ordinary saved plan/control, hashes, same tests and owned-file fresh readback. Genie added queue, journal, full callback tokens and report sink. Its five token probes are separate, never baseline failure criteria. Root manually performed task setup, dispatch, review, checks, delivery and persistence; zero extra user continuation prompts is not zero controller labor. Exact controller effort, tokens, money and comparable latency were not measured. Ordinary binding adapter was implemented after dispatch but before outputs were read, following predefined probes; frozen brief/oracle/protocol never changed after dispatch.

Maintain one utility: validation_summary.py is an exact copy of the accepted Genie candidate, with both original arm sources preserved under output/. This maintenance choice (including its API size guard) is not an advantage established by the frozen suite. It supports only the task's finite log forms. It never executes input logs or verifies their authenticity. A FAIL log summary can be successful parser behavior; NO_COVERAGE must remain distinct from PASS.

From repository root:

```bash
python3.12 -B comparison_pilot/validation_summary.py comparison_pilot/input/runner_status.txt --format unittest
python3.12 -B comparison_pilot/validation_summary.py comparison_pilot/input/zero_discovery.txt --format unittest
python3.12 -B comparison_pilot/validation_summary.py comparison_pilot/input/direct_checks.json --format json
```

Expected PASS/count46/exit0, NO_COVERAGE/count0/exit1, PASS/count17/exit0; all scope TEST_LOG_SUMMARY_ONLY. Input files are existing historical logs, not tests rerun by these commands.

Genie run closed ALL_TASKS_COMPLETE with one reservation, one observed author call, one exact sink application and fresh subprocess CONFIRMED. Plain control closed with one author and fresh owned-file confirmation. Previous closed stores unchanged; no budget reset, provider/etcd/lost-ack/EXP010 experiment repeated. Original approved direction and all scoped authority, custody, rollback, power-loss, remote-authenticity and hostile-isolation HOLDs preserved. No promotion, freeze, new spending, main merge or production deployment.

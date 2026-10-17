"""Run exactly one finite two-task Phase 2C live batch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
ALIAS = "phase2c-finite-live-20261016"
TASK_IDS = ("genie-phase2c-finite-task-1-20261016",
            "genie-phase2c-finite-task-2-20261016")


def _registry():
    record = json.loads((TRIAL / "REGISTRY.json").read_text())[ALIAS]
    return {ALIAS: {"queue": str(TRIAL / record["queue"]),
                    "run_id": record["run_id"],
                    "owned_root": str(TRIAL / record["owned_root"])}}


def _write_once(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    if Path(path).read_bytes() != raw:
        raise RuntimeError("EVIDENCE_READBACK_MISMATCH")


class PilotHooks:
    def __init__(self, artifact_directory, codex_home):
        self.artifact_directory = artifact_directory
        self.codex_home = codex_home
        self.worker_calls = 0
        self.reviewer_calls = 0
        self.live_results = {}

    def worker(self, action):
        from phase2b2s_attested_live_pilot.attested_worker import AGENT, run_once
        self.worker_calls += 1
        task_id = action.get("token", {}).get("task_id")
        if self.worker_calls > 2 or task_id not in TASK_IDS:
            raise RuntimeError("WORKER_BOUND_EXCEEDED")
        number = self.worker_calls
        evidence_dir = TRIAL / f"operation-{number}"
        evidence_dir.mkdir()
        scratch = Path(tempfile.mkdtemp(prefix=f"genie-phase2c-live-{number}-"))
        live = run_once(token=action["token"],
            artifact_directory=self.artifact_directory, codex_home=self.codex_home,
            working_directory=scratch, ledger_path=evidence_dir / "operation.sqlite",
            evidence_directory=evidence_dir, timeout_seconds=240)
        _write_once(evidence_dir / "LIVE_WORKER.json", live)
        self.live_results[task_id] = live
        if live.get("status") != "OBSERVED_ACCEPTED":
            return {"token": action["token"], "outcome": "UNKNOWN",
                    "agent": None, "evidence": {"preserve": True,
                    "allow_new_invocation": False, "retry_count": 0,
                    "logical_operation_id": live.get("logical_operation_id"),
                    "classification": "LIVE_WORKER_TERMINAL_UNKNOWN"}, "text": None}
        evidence_hash = hashlib.sha256(json.dumps(live["evidence"], sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED",
                "agent": AGENT, "evidence": {"logical_operation_id":
                live["logical_operation_id"], "worker_evidence_sha256": evidence_hash,
                "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER"},
                "text": live["result_text"]}

    def reviewer(self, action):
        from phase2b2s_attested_live_pilot.attested_worker import EXPECTED_RESULT
        self.reviewer_calls += 1
        candidate = action.get("candidate")
        candidate_hash = hashlib.sha256(candidate.encode()).hexdigest()
        accepted = (candidate_hash == action.get("candidate_sha256")
                    and json.loads(candidate) == EXPECTED_RESULT)
        return {"token": action["token"], "candidate_hash": candidate_hash,
                "decision": "ACCEPT" if accepted else "REJECT",
                "reason": "BOUNDED_SCHEMA_MATCH_COMMON_CAUSE" if accepted
                          else "BOUNDED_SCHEMA_MISMATCH"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    args = parser.parse_args(argv)
    preflight = json.loads((HERE / "NO_MODEL_PREFLIGHT.json").read_text())
    if (preflight.get("status") != "OBSERVED_ACCEPTED"
            or preflight.get("model_turns") != 0
            or preflight.get("classification") !=
               "PHASE2C_NO_MODEL_PREFLIGHT_ACCEPTED_NONCLAIM"
            or (TRIAL / "PROGRESS.jsonl").exists()
            or (TRIAL / "TERMINAL.json").exists()):
        raise ValueError("LIVE_BATCH_PRECONDITION")
    progress_path = TRIAL / "PROGRESS.jsonl"
    progress = open(progress_path, "xb")
    def notify(value):
        raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        progress.write(raw)
        progress.flush()
        os.fsync(progress.fileno())
    from shared_interfaces.session_driver import drive_run
    from shared_interfaces.status_tool import GenieStatusTools
    hooks = PilotHooks(args.artifact_directory, args.codex_home)
    terminal = None
    try:
        terminal = drive_run(_registry(), ALIAS, hooks.worker, hooks.reviewer,
                             max_actions=8, notify=notify)
    finally:
        progress.close()
    # The driver terminal is final. Do not poll it. Read destinations once only on success.
    evidence = {"driver_terminal": terminal, "worker_model_calls": hooks.worker_calls,
                "reviewer_model_calls": 0, "deterministic_reviewer_calls":
                hooks.reviewer_calls, "retry_count": 0, "preserve": True,
                "allow_new_invocation": False,
                "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER"}
    if (terminal.get("action") == "STOP"
            and terminal.get("reason") == "ALL_TASKS_COMPLETE"
            and hooks.worker_calls == 2 and hooks.reviewer_calls == 2):
        tools = GenieStatusTools(_registry())
        run = tools.call("get_run_status", {"run_name": ALIAS})
        tasks = [tools.call("get_task_result", {"run_name": ALIAS,
                 "task_id": task_id}) for task_id in TASK_IDS]
        evidence.update({"run_readback": run, "task_readbacks": tasks})
        if (run.get("status") == "PASS"
                and all(item.get("status") == "CONFIRMED"
                        and item.get("content_role") == "UNTRUSTED_ACCEPTED_TASK_DATA"
                        for item in tasks)):
            evidence["frontier"] = "PHASE_2_COMPLETE_NONCLAIM"
            evidence["accepted_only_after_fresh_destination_readback"] = True
            _write_once(TRIAL / "TERMINAL.json", evidence)
            print("PHASE_2_COMPLETE_NONCLAIM")
            return 0
    evidence["frontier"] = "PHASE_2C_TERMINAL_UNKNOWN_NONCLAIM"
    _write_once(TRIAL / "TERMINAL.json", evidence)
    print("PHASE_2C_TERMINAL_UNKNOWN_NONCLAIM")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        terminal = TRIAL / "TERMINAL.json"
        if not terminal.exists():
            _write_once(terminal, {"frontier": "PHASE_2C_TERMINAL_UNKNOWN_NONCLAIM",
                "failure_class": type(exc).__name__, "failure_reason": str(exc)[:200],
                "preserve": True, "allow_new_invocation": False, "retry_count": 0})
        raise

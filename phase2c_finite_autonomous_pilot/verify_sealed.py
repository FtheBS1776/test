"""Read-only verification of the sealed Phase 2C evidence."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sqlite3


HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
ALIAS = "phase2c-finite-live-20261016"
TASK_IDS = ("genie-phase2c-finite-task-1-20261016",
            "genie-phase2c-finite-task-2-20261016")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_sealed(evidence_directory=HERE):
    """Inspect a supplied local evidence copy; return data without report writes."""
    trial = Path(evidence_directory) / "trial"
    terminal = json.loads((trial / "TERMINAL.json").read_text())
    if (terminal.get("frontier") != "PHASE_2_COMPLETE_NONCLAIM"
            or terminal.get("driver_terminal", {}).get("action") != "STOP"
            or terminal["driver_terminal"].get("reason") != "ALL_TASKS_COMPLETE"
            or terminal["driver_terminal"].get("counts") != {
                "advances": 7, "worker_hooks": 2, "reviewer_hooks": 2}
            or terminal.get("worker_model_calls") != 2
            or terminal.get("reviewer_model_calls") != 0
            or terminal.get("retry_count") != 0
            or not terminal.get("accepted_only_after_fresh_destination_readback")):
        raise RuntimeError("TERMINAL_INVARIANT")
    lines = [json.loads(line) for line in (trial / "PROGRESS.jsonl").read_text().splitlines()]
    actions = [line["action"]["action"] for line in lines]
    if actions != ["INVOKE_WORKER", "REVIEW_CANDIDATE", "TASK_COMPLETE",
                   "INVOKE_WORKER", "REVIEW_CANDIDATE", "TASK_COMPLETE", "STOP"]:
        raise RuntimeError("PROGRESS_SEQUENCE")
    logical_ids, call_ids = [], []
    operations = []
    for number, task_id in enumerate(TASK_IDS, 1):
        directory = trial / f"operation-{number}"
        live = json.loads((directory / "LIVE_WORKER.json").read_text())
        evidence = live["evidence"]
        snapshot = evidence["capability_attestation"]["snapshot"]
        member_names = sorted(PureWindowsPath(item["image"]).name.lower() for item in evidence["members"])
        with closing(sqlite3.connect(
                (directory / "operation.sqlite").resolve().as_uri() + "?mode=ro", uri=True)) as db:
            rows = db.execute("SELECT logical_id,state,preserve,allow_new_invocation FROM operation").fetchall()
        if (live.get("status") != "OBSERVED_ACCEPTED"
                or evidence.get("assignment_verified_before_semantic_release") is not True
                or evidence.get("artifact_checksum_readback_verified") is not True
                or evidence.get("raw_stream_readback_verified") is not True
                or snapshot.get("tool_count") != 0 or snapshot.get("tools") != []
                or evidence.get("tool_activity_count") != 0
                or member_names != ["codex.exe", "conhost.exe"]
                or evidence["accounting_after_termination"].get("active_processes") != 0
                or evidence.get("termination_attempt_count") != 1
                or evidence["binding"]["token"]["task_id"] != task_id
                or snapshot.get("logical_operation_id") != live.get("logical_operation_id")
                or _sha(directory / "RAW_STDOUT.jsonl") != evidence["stdout_sha256"]
                or _sha(directory / "RAW_STDERR.bin") != evidence["stderr_sha256"]
                or _sha(directory / "LAST_MESSAGE.json") != evidence["last_message_sha256"]
                or rows != [(live["logical_operation_id"], "OBSERVED_ACCEPTED", 1, 0)]):
            raise RuntimeError(f"OPERATION_{number}_INVARIANT")
        logical_ids.append(live["logical_operation_id"])
        call_ids.append(evidence["binding"]["token"]["call_id"])
        operations.append({"task_id": task_id, "call_id": call_ids[-1],
            "logical_operation_id": logical_ids[-1], "tool_count": 0,
            "members": member_names, "active_after_termination": 0,
            "ledger_state": "OBSERVED_ACCEPTED"})
    if len(set(logical_ids)) != 2 or len(set(call_ids)) != 2:
        raise RuntimeError("CROSS_OPERATION_IDENTITY")
    record = json.loads((trial / "REGISTRY.json").read_text())[ALIAS]
    registry = {ALIAS: {"queue": str(trial / record["queue"]),
                        "run_id": record["run_id"],
                        "owned_root": str(trial / record["owned_root"])}}
    from shared_interfaces.status_tool import GenieStatusTools
    tools = GenieStatusTools(registry)
    run = tools.call("get_run_status", {"run_name": ALIAS})
    tasks = [tools.call("get_task_result", {"run_name": ALIAS, "task_id": value})
             for value in TASK_IDS]
    if (run.get("status") != "PASS"
            or run.get("queue_history", {}).get("reserved_model_calls") != 2
            or any(task.get("status") != "CONFIRMED"
                   or task.get("content_role") != "UNTRUSTED_ACCEPTED_TASK_DATA"
                   for task in tasks)):
        raise RuntimeError("FRESH_READBACK_INVARIANT")
    result = {"status": "PASS", "classification": "PHASE_2_COMPLETE_NONCLAIM",
              "operations": operations, "progress_actions": actions,
              "worker_model_calls": 2, "reviewer_model_calls": 0,
              "retry_count": 0, "fresh_destination_statuses":
              [task["status"] for task in tasks],
              "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER",
              "json_stream_is_sole_authority": False}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-directory", type=Path, default=HERE)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    evidence = args.evidence_directory.resolve()
    report = args.report.resolve() if args.report is not None else None
    if report is not None:
        if report == evidence or evidence in report.parents:
            raise ValueError("REPORT_INSIDE_EVIDENCE")
        if report.exists() or args.report.is_symlink():
            raise ValueError("REPORT_COLLISION")
    result = inspect_sealed(evidence)
    if report is not None:
        # Trusted local host: exclusive creation prevents overwriting an old
        # report. This is not hostile-path or atomic-publication assurance.
        with report.open("x", encoding="utf-8") as destination:
            destination.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PHASE_2_SEALED_EVIDENCE_VERIFIED_NONCLAIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

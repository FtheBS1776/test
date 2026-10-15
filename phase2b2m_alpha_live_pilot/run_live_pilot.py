"""Run the single alpha model turn and bind it to fresh destination readback."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
ALIAS = "phase2b2-alpha-live-synthetic-20261015"
TASK_ID = "genie-phase2b2-alpha-live-task-20261015-8c51d7"
CODEX = Path(r"C:\Users\aaron\Documents\Codex\phase2b2-alpha-audit-20261015\win32-x64\package\vendor\x86_64-pc-windows-msvc\bin\codex.exe")
CODEX_VERSION = "codex-cli package 0.163.0-alpha.11-win32-x64"
CODEX_HOME = Path(r"C:\Users\aaron\.codex")


def _registry():
    raw = json.loads((TRIAL / "REGISTRY.json").read_text(encoding="utf-8"))
    record = raw[ALIAS]
    return {ALIAS: {"queue": str(TRIAL / record["queue"]),
                    "run_id": record["run_id"],
                    "owned_root": str(TRIAL / record["owned_root"])}}


def _write_once(name, value):
    path = TRIAL / name
    if path.exists():
        raise ValueError("EVIDENCE_ALREADY_EXISTS")
    path.write_text(json.dumps(value, indent=2, sort_keys=True,
                               ensure_ascii=True) + "\n", encoding="utf-8")


def main():
    from phase2b2m_alpha_live_pilot.alpha_exec_worker import (
        AGENT, EXPECTED_RESULT, run_once,
    )
    from shared_interfaces.run_control import GenieRunController
    from shared_interfaces.run_events import GenieRunEvents
    from shared_interfaces.status_tool import GenieStatusTools

    registry = _registry()
    controller = GenieRunController(registry)
    events = GenieRunEvents(registry)
    status = GenieStatusTools(registry)
    dispatch = controller.call("advance_run", {"run_name": ALIAS})
    _write_once("DISPATCH.json", dispatch)
    if dispatch.get("action") != "INVOKE_WORKER":
        raise ValueError("DISPATCH_NOT_INVOKE_WORKER")

    scratch = Path(tempfile.mkdtemp(prefix="genie-phase2b2-alpha-child-"))
    live = run_once(
        token=dispatch["token"], ledger_path=TRIAL / "operation.sqlite",
        executable=CODEX, version=CODEX_VERSION, codex_home=CODEX_HOME,
        working_directory=scratch, timeout_seconds=240)
    _write_once("LIVE_WORKER.json", live)
    if live.get("status") != "OBSERVED_ACCEPTED":
        _write_once("STOP.json", {
            "frontier": "PHASE_2B2_ALPHA_LIVE_UNKNOWN_NONCLAIM",
            "preserve": True, "allow_new_invocation": False,
            "retry_count": 0, "phase2c_entered": False})
        print(json.dumps(live, sort_keys=True))
        return 2

    observe = events.call("apply_run_event", {
        "run_name": ALIAS, "operation": "observe", "supplied": dispatch["token"],
        "payload": {"outcome": "OBSERVED_ACCEPTED", "agent": AGENT,
                    "evidence": {"logical_operation_id": live[
                        "logical_operation_id"], "worker_evidence_sha256":
                        hashlib.sha256(json.dumps(live["evidence"], sort_keys=True,
                        separators=(",", ":")).encode()).hexdigest(),
                        "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER"}}})
    _write_once("OBSERVE.json", observe)
    if observe != {"status": "APPLIED", "operation": "observe",
                   "result": "RECORDED"}:
        raise ValueError("OBSERVE_UNCERTAIN")
    submit = events.call("apply_run_event", {
        "run_name": ALIAS, "operation": "submit", "supplied": dispatch["token"],
        "payload": {"agent": AGENT, "text": live["result_text"]}})
    _write_once("SUBMIT.json", submit)
    if submit != {"status": "APPLIED", "operation": "submit",
                  "result": "SUBMITTED"}:
        raise ValueError("SUBMIT_UNCERTAIN")

    request = controller.call("advance_run", {"run_name": ALIAS})
    _write_once("REVIEW_REQUEST.json", request)
    if (request.get("action") != "REVIEW_CANDIDATE"
            or request.get("token") != dispatch["token"]
            or json.loads(request.get("candidate", "null")) != EXPECTED_RESULT):
        raise ValueError("REVIEW_BINDING")
    review = events.call("apply_run_event", {
        "run_name": ALIAS, "operation": "review", "supplied": dispatch["token"],
        "payload": {"candidate_hash": request["candidate_sha256"],
                    "decision": "ACCEPT",
                    "reason": "bounded-deterministic-schema-match-common-cause"}})
    _write_once("REVIEW.json", review)
    if review != {"status": "APPLIED", "operation": "review", "result": "ACCEPT"}:
        raise ValueError("REVIEW_UNCERTAIN")
    delivery = controller.call("advance_run", {"run_name": ALIAS})
    _write_once("DELIVERY.json", delivery)
    if delivery.get("action") != "TASK_COMPLETE" or delivery.get("task_id") != TASK_ID:
        raise ValueError("DELIVERY_UNCERTAIN")
    fresh = status.call("get_task_result", {"run_name": ALIAS,
                                             "task_id": TASK_ID})
    _write_once("FRESH_DESTINATION_READBACK.json", fresh)
    if (fresh.get("status") != "CONFIRMED"
            or fresh.get("result_text") != live["result_text"]
            or fresh.get("content_role") != "UNTRUSTED_ACCEPTED_TASK_DATA"):
        raise ValueError("FRESH_DESTINATION_NOT_CONFIRMED")
    _write_once("STOP.json", {
        "frontier": "PHASE_2B2_ALPHA_LIVE_COMPLETE_NONCLAIM",
        "live_worker_calls": 1, "reviewer_model_calls": 0,
        "retry_count": 0, "phase2c_entered": False,
        "accepted_only_after_fresh_destination_readback": True,
        "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER"})
    print("PHASE_2B2_ALPHA_LIVE_COMPLETE_NONCLAIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

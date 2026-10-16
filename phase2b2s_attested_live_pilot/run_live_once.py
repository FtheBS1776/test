"""Execute one attested live turn and require fresh destination readback."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
PREFLIGHT = HERE.parent / "phase2b2r_exact_codex_preflight" / "trial"
ALIAS = "phase2b2-attested-live-20261016"
TASK_ID = "genie-phase2b2-attested-task-20261016-c4e713"


def registry():
    record = json.loads((TRIAL / "REGISTRY.json").read_text())[ALIAS]
    return {ALIAS: {"queue": str(TRIAL / record["queue"]),
                    "run_id": record["run_id"],
                    "owned_root": str(TRIAL / record["owned_root"])}}


def write_once(name, value):
    path = TRIAL / name
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        import os
        os.fsync(target.fileno())
    if path.read_bytes() != raw:
        raise RuntimeError("EVIDENCE_READBACK_MISMATCH")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    args = parser.parse_args(argv)
    preflight = json.loads((PREFLIGHT / "PREFLIGHT_RESULT.json").read_text())
    if (preflight.get("status") != "OBSERVED_ACCEPTED"
            or preflight.get("evidence", {}).get("model_turns") != 0
            or preflight.get("evidence", {}).get(
                "classification") != "NO_MODEL_PREFLIGHT_ACCEPTED_NONCLAIM"):
        raise ValueError("PREFLIGHT_NOT_ACCEPTED")
    from phase2b2s_attested_live_pilot.attested_worker import (
        AGENT, EXPECTED_RESULT, run_once,
    )
    from shared_interfaces.run_control import GenieRunController
    from shared_interfaces.run_events import GenieRunEvents
    from shared_interfaces.status_tool import GenieStatusTools
    selected = registry()
    controller, events, status = (GenieRunController(selected),
                                  GenieRunEvents(selected),
                                  GenieStatusTools(selected))
    dispatch = controller.call("advance_run", {"run_name": ALIAS})
    write_once("DISPATCH.json", dispatch)
    if dispatch.get("action") != "INVOKE_WORKER":
        raise ValueError("DISPATCH_NOT_INVOKE_WORKER")
    scratch = Path(tempfile.mkdtemp(prefix="genie-phase2b2-attested-live-"))
    live = run_once(
        token=dispatch["token"], artifact_directory=args.artifact_directory,
        codex_home=args.codex_home, working_directory=scratch,
        ledger_path=TRIAL / "operation.sqlite", evidence_directory=TRIAL,
        timeout_seconds=240)
    write_once("LIVE_WORKER.json", live)
    if live.get("status") != "OBSERVED_ACCEPTED":
        write_once("STOP.json", {
            "frontier": "PHASE_2B2_ATTESTED_LIVE_UNKNOWN_NONCLAIM",
            "preserve": True, "allow_new_invocation": False,
            "retry_count": 0, "phase2c_entered": False,
            "scratch": str(scratch)})
        return 2
    observe = events.call("apply_run_event", {
        "run_name": ALIAS, "operation": "observe", "supplied": dispatch["token"],
        "payload": {"outcome": "OBSERVED_ACCEPTED", "agent": AGENT,
                    "evidence": {"logical_operation_id": live[
                        "logical_operation_id"], "worker_evidence_sha256":
                        hashlib.sha256(json.dumps(live["evidence"], sort_keys=True,
                        separators=(",", ":")).encode()).hexdigest(),
                        "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER"}}})
    write_once("OBSERVE.json", observe)
    if observe != {"status": "APPLIED", "operation": "observe",
                   "result": "RECORDED"}:
        raise ValueError("OBSERVE_UNCERTAIN")
    submit = events.call("apply_run_event", {
        "run_name": ALIAS, "operation": "submit", "supplied": dispatch["token"],
        "payload": {"agent": AGENT, "text": live["result_text"]}})
    write_once("SUBMIT.json", submit)
    if submit != {"status": "APPLIED", "operation": "submit",
                  "result": "SUBMITTED"}:
        raise ValueError("SUBMIT_UNCERTAIN")
    request = controller.call("advance_run", {"run_name": ALIAS})
    write_once("REVIEW_REQUEST.json", request)
    if (request.get("action") != "REVIEW_CANDIDATE"
            or request.get("token") != dispatch["token"]
            or json.loads(request.get("candidate", "null")) != EXPECTED_RESULT):
        raise ValueError("REVIEW_BINDING")
    review = events.call("apply_run_event", {
        "run_name": ALIAS, "operation": "review", "supplied": dispatch["token"],
        "payload": {"candidate_hash": request["candidate_sha256"],
                    "decision": "ACCEPT",
                    "reason": "bounded-attested-schema-match-common-cause"}})
    write_once("REVIEW.json", review)
    if review != {"status": "APPLIED", "operation": "review",
                  "result": "ACCEPT"}:
        raise ValueError("REVIEW_UNCERTAIN")
    delivery = controller.call("advance_run", {"run_name": ALIAS})
    write_once("DELIVERY.json", delivery)
    if (delivery.get("action") != "TASK_COMPLETE"
            or delivery.get("task_id") != TASK_ID):
        raise ValueError("DELIVERY_UNCERTAIN")
    fresh = status.call("get_task_result", {"run_name": ALIAS,
                                             "task_id": TASK_ID})
    write_once("FRESH_DESTINATION_READBACK.json", fresh)
    if (fresh.get("status") != "CONFIRMED"
            or fresh.get("result_text") != live["result_text"]
            or fresh.get("content_role") != "UNTRUSTED_ACCEPTED_TASK_DATA"):
        raise ValueError("FRESH_DESTINATION_NOT_CONFIRMED")
    write_once("STOP.json", {
        "frontier": "PHASE_2B2_ATTESTED_LIVE_COMPLETE_NONCLAIM",
        "live_worker_calls": 1, "reviewer_model_calls": 0,
        "retry_count": 0, "phase2c_entered": False,
        "accepted_only_after_fresh_destination_readback": True,
        "independence": "COMMON_CAUSE_SAME_HOST_SAME_PROVIDER",
        "scratch": str(scratch)})
    print("PHASE_2B2_ATTESTED_LIVE_COMPLETE_NONCLAIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

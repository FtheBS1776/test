"""Deterministic Phase 2C checks. This file never launches Codex."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    from phase2b2r_exact_codex_preflight.exact_codex_preflight import verify_artifact
    executable, digest = verify_artifact(args.artifact_directory)
    # Exercise the full two-task driver with fake hooks in disposable stores.
    from shared_interfaces.session_driver import drive_run
    from shared_interfaces.status_tool import GenieStatusTools, _load_core
    with tempfile.TemporaryDirectory(prefix="genie-phase2c-no-model-") as temporary:
        root = Path(temporary)
        queue, owned = root / "queue.sqlite", root / "work"
        owned.mkdir()
        runner = _load_core().load_runner()
        run_id = "phase2c-no-model-preflight"
        runner.q.initialize(queue, {"run_id": run_id, "max_tasks": 2,
            "max_model_calls": 2, "effect_scope": "owned-local-report-inbox"})
        for number in (1, 2):
            runner.q.enqueue(queue, {"task_id": f"preflight-{number}",
                "goal": "no model driver exercise", "input_sha256": str(number) * 64,
                "max_attempts": 1})
        registry = {"preflight": {"queue": str(queue), "run_id": run_id,
                                   "owned_root": str(owned)}}
        worker_calls = []
        reviewer_calls = []
        def worker(action):
            worker_calls.append(action["token"]["call_id"])
            return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED",
                    "agent": "NO_MODEL_FIXTURE", "evidence": {"model_turns": 0},
                    "text": '{"authority_request":false,"marker":"LOCAL_ATTESTED_WORKER_OK_20261016","visible_tool_or_mcp_names":[]}'}
        def reviewer(action):
            reviewer_calls.append(action["token"]["call_id"])
            return {"token": action["token"],
                    "candidate_hash": action["candidate_sha256"],
                    "decision": "ACCEPT", "reason": "NO_MODEL_EXACT_FIXTURE"}
        result = drive_run(registry, "preflight", worker, reviewer, max_actions=8)
        status = GenieStatusTools(registry).call("get_run_status", {"run_name": "preflight"})
        if (result.get("action") != "STOP"
                or result.get("reason") != "ALL_TASKS_COMPLETE"
                or result.get("counts") != {"advances": 7, "worker_hooks": 2,
                                             "reviewer_hooks": 2}
                or len(set(worker_calls)) != 2 or worker_calls != reviewer_calls
                or status.get("status") != "PASS"
                or [task["fresh_sink"]["status"] for task in status["tasks"]]
                   != ["CONFIRMED", "CONFIRMED"]):
            raise RuntimeError("NO_MODEL_DRIVER_PREFLIGHT_FAILED")
    result = {"status": "OBSERVED_ACCEPTED", "classification":
              "PHASE2C_NO_MODEL_PREFLIGHT_ACCEPTED_NONCLAIM", "model_turns": 0,
              "worker_fixture_calls": 2, "reviewer_fixture_calls": 2,
              "codex_executable": str(executable), "codex_executable_sha256": digest,
              "driver_sha256": hashlib.sha256((HERE.parent / "shared_interfaces" /
                                                "session_driver.py").read_bytes()).hexdigest()}
    target = HERE / "NO_MODEL_PREFLIGHT.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PHASE2C_NO_MODEL_PREFLIGHT_ACCEPTED_NONCLAIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

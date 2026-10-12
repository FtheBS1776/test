"""Provision the one fresh Phase 2A run; never reset or repair partial state."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TRIAL = Path(__file__).resolve().parent / "trial"
QUEUE = TRIAL / "queue.sqlite"
OWNED = TRIAL / "work"
INPUT = TRIAL / "INPUT.md"


def _load(name):
    value = json.loads((TRIAL / name).read_text(encoding="utf-8", errors="strict"))
    if type(value) is not dict:
        raise ValueError("CONFIG_OBJECT")
    return value


def main():
    policy = _load("POLICY.json")
    plan = _load("PLAN.json")
    registry = _load("REGISTRY.json")
    alias = "phase2a-synthetic-20261012"
    input_sha256 = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    if (set(registry) != {alias}
            or registry[alias] != {
                "queue": "queue.sqlite",
                "run_id": policy.get("run_id"),
                "owned_root": "work",
            }
            or set(policy) != {
                "run_id", "max_tasks", "max_model_calls", "effect_scope"}
            or type(policy.get("run_id")) is not str
            or not policy["run_id"].startswith(
                "genie-phase2a-controller-run-20261012-")
            or policy.get("max_tasks") != 1
            or policy.get("max_model_calls") != 1
            or policy.get("effect_scope") != "owned-local-report-inbox"
            or set(plan) != {
                "task_id", "goal", "input_sha256", "max_attempts"}
            or type(plan.get("task_id")) is not str
            or not plan["task_id"].startswith(
                "genie-phase2a-controller-task-20261012-")
            or plan.get("task_id") == policy.get("run_id")
            or type(plan.get("goal")) is not str or not plan["goal"]
            or plan.get("input_sha256") != input_sha256
            or plan.get("max_attempts") != 1
            or QUEUE.exists() or OWNED.exists()):
        raise ValueError("FRESH_SYNTHETIC_PRECONDITION")
    from shared_interfaces.status_tool import _load_core
    runner = _load_core().load_runner()
    OWNED.mkdir()
    runner.q.initialize(QUEUE, policy)
    if runner.q.enqueue(QUEUE, plan) != "ENQUEUED":
        raise ValueError("SYNTHETIC_ENQUEUE")
    print("PHASE2A_SYNTHETIC_PROVISIONED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

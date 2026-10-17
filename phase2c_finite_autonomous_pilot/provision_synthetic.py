"""Provision the only fresh Phase 2C two-task synthetic run."""
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
QUEUE = TRIAL / "queue.sqlite"
OWNED = TRIAL / "work"
ALIAS = "phase2c-finite-live-20261016"
TASKS = (
    ("genie-phase2c-finite-task-1-20261016", "INPUT_1.md"),
    ("genie-phase2c-finite-task-2-20261016", "INPUT_2.md"),
)


def _load(name):
    value = json.loads((TRIAL / name).read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("CONFIG_OBJECT")
    return value


def plans():
    return [{
        "task_id": task_id,
        "goal": "produce bounded attested no-authority worker datum",
        "input_sha256": hashlib.sha256((TRIAL / source).read_bytes()).hexdigest(),
        "max_attempts": 1,
    } for task_id, source in TASKS]


def main():
    policy, registry = _load("POLICY.json"), _load("REGISTRY.json")
    forbidden = [QUEUE, OWNED, TRIAL / "PROGRESS.jsonl", TRIAL / "TERMINAL.json"]
    if (policy != {"run_id": "genie-phase2c-finite-run-20261016",
                   "max_tasks": 2, "max_model_calls": 2,
                   "effect_scope": "owned-local-report-inbox"}
            or set(registry) != {ALIAS}
            or registry[ALIAS] != {"queue": "queue.sqlite",
                                   "run_id": policy["run_id"],
                                   "owned_root": "work"}
            or any(path.exists() for path in forbidden)
            or any((TRIAL / f"operation-{n}").exists() for n in (1, 2))):
        raise ValueError("FRESH_SYNTHETIC_PRECONDITION")
    from shared_interfaces.status_tool import _load_core
    runner = _load_core().load_runner()
    OWNED.mkdir()
    runner.q.initialize(QUEUE, policy)
    for plan in plans():
        if runner.q.enqueue(QUEUE, plan) != "ENQUEUED":
            raise ValueError("SYNTHETIC_ENQUEUE")
    print("PHASE2C_SYNTHETIC_PROVISIONED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

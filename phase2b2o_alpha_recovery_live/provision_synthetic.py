"""Provision the only fresh alpha recovery live task."""
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
LEDGER = TRIAL / "operation.sqlite"
ALIAS = "phase2b2-alpha-recovery-live-20261015"


def load(name):
    value = json.loads((TRIAL / name).read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("CONFIG_OBJECT")
    return value


def main():
    policy, plan, registry = load("POLICY.json"), load("PLAN.json"), load("REGISTRY.json")
    if (set(registry) != {ALIAS}
            or registry[ALIAS] != {"queue": "queue.sqlite",
                                   "run_id": policy.get("run_id"),
                                   "owned_root": "work"}
            or policy.get("max_tasks") != 1 or policy.get("max_model_calls") != 1
            or policy.get("effect_scope") != "owned-local-report-inbox"
            or plan.get("max_attempts") != 1
            or plan.get("input_sha256") != hashlib.sha256(INPUT.read_bytes()).hexdigest()
            or QUEUE.exists() or OWNED.exists() or LEDGER.exists()):
        raise ValueError("FRESH_SYNTHETIC_PRECONDITION")
    from shared_interfaces.status_tool import _load_core
    runner = _load_core().load_runner()
    OWNED.mkdir()
    runner.q.initialize(QUEUE, policy)
    if runner.q.enqueue(QUEUE, plan) != "ENQUEUED":
        raise ValueError("SYNTHETIC_ENQUEUE")
    print("PHASE2B2_ALPHA_RECOVERY_LIVE_PROVISIONED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

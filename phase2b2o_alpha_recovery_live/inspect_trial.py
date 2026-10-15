"""Read-only inspection of the sealed recovery live trial."""
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TRIAL = Path(__file__).resolve().parent / "trial"
ALIAS = "phase2b2-alpha-recovery-live-20261015"
TASK = "genie-phase2b2-alpha-recovery-task-20261015-74b93e"


def main():
    from shared_interfaces.status_tool import GenieStatusTools
    record = json.loads((TRIAL / "REGISTRY.json").read_text())[ALIAS]
    registry = {ALIAS: {"queue": str(TRIAL / record["queue"]),
                        "run_id": record["run_id"],
                        "owned_root": str(TRIAL / record["owned_root"])}}
    tools = GenieStatusTools(registry)
    connection = sqlite3.connect(
        f"file:{(TRIAL / 'operation.sqlite').as_posix()}?mode=ro", uri=True)
    try:
        operation = connection.execute(
            "SELECT logical_id,state,preserve,allow_new_invocation "
            "FROM operation").fetchall()
    finally:
        connection.close()
    print(json.dumps({"operation_ledger": operation,
                      "run": tools.call("get_run_status", {"run_name": ALIAS}),
                      "task": tools.call("get_task_result", {
                          "run_name": ALIAS, "task_id": TASK})},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

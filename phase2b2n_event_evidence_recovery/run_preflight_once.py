"""Execute one fresh no-model event-evidence recovery preflight."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
RESULT = TRIAL / "PREFLIGHT_RESULT.json"
STOP = TRIAL / "STOP.json"
RAW = TRIAL / "RAW_EVENTS.jsonl"
RUNTIME = Path(r"C:\Users\aaron\Documents\Codex\phase2b2-event-evidence-runtime-20261015")
PYTHON = Path(r"C:\Users\aaron\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
FIXTURE = HERE / "event_fixture.py"


def write_once(path, value):
    if path.exists():
        raise ValueError("EVIDENCE_ALREADY_EXISTS")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def main():
    if TRIAL.exists() or RUNTIME.exists():
        raise ValueError("PREFLIGHT_NOT_FRESH")
    TRIAL.mkdir()
    RUNTIME.mkdir()
    operation_id = hashlib.sha256(
        b"phase2b2-event-evidence-recovery-preflight-20261015-v1").hexdigest()
    from phase2b2n_event_evidence_recovery.recovery_preflight import run_once
    result = run_once(
        python_executable=PYTHON, fixture_path=FIXTURE, work_root=RUNTIME,
        evidence_path=RAW, operation_id=operation_id)
    write_once(RESULT, result)
    write_once(STOP, {
        "frontier": ("PHASE_2B2_EVENT_EVIDENCE_RECOVERY_PREFLIGHT_VERIFIED_NONCLAIM"
                     if result.get("status") == "VERIFIED"
                     else "PHASE_2B2_EVENT_EVIDENCE_RECOVERY_PREFLIGHT_UNKNOWN_NONCLAIM"),
        "status": result.get("status"), "preserve": True,
        "allow_new_invocation": False, "retry_count": 0,
        "model_turn_count": 0, "live_turn_authorized": False,
        "phase2c_entered": False})
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

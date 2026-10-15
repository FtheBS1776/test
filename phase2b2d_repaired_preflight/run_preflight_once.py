"""Run and record the sole authorized repaired no-model recovery preflight."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TRIAL = Path(__file__).resolve().parent / "trial"
LEDGER = TRIAL / "preflight_operation.db"
RESULT = TRIAL / "PREFLIGHT_RESULT.json"
STOP = TRIAL / "STOP.json"
CODEX = Path(r"C:\Users\aaron\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe")
VERSION = "codex-cli 0.162.1"
CODEX_HOME = Path(r"C:\Users\aaron\.codex")
OPERATION_CONTEXT = (
    "phase2b2-repaired-recovery-preflight-20261014-authorized-once-v1")


def _write_once(path, value):
    if path.exists():
        raise ValueError("PREFLIGHT_EVIDENCE_ALREADY_EXISTS")
    path.write_text(json.dumps(value, indent=2, sort_keys=True,
                               ensure_ascii=True) + "\n", encoding="utf-8")


def main():
    if LEDGER.exists() or RESULT.exists() or STOP.exists():
        raise ValueError("PREFLIGHT_NOT_FRESH")
    TRIAL.mkdir(exist_ok=True)
    from phase2b2c_preflight.recovery_preflight import run_once
    result = run_once(
        executable=CODEX, version=VERSION, codex_home=CODEX_HOME,
        ledger_path=LEDGER, timeout_seconds=90,
        operation_context=OPERATION_CONTEXT)
    _write_once(RESULT, result)
    _write_once(STOP, {
        "frontier": ("PHASE_2B2_REPAIRED_RECOVERY_PREFLIGHT_VERIFIED_NONCLAIM"
                     if result.get("status") == "VERIFIED"
                     else "PHASE_2B2_REPAIRED_RECOVERY_PREFLIGHT_UNKNOWN_NONCLAIM"),
        "status": result.get("status"), "preserve": True,
        "allow_new_invocation": False, "retry_count": 0,
        "semantic_request_count": 0, "model_turn_count": 0,
        "phase2b2_live_retry_entered": False, "phase2c_entered": False})
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

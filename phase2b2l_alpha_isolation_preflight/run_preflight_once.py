"""Run one fresh alpha app-server isolation preflight without authentication."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"
LEDGER = TRIAL / "preflight_operation.db"
RESULT = TRIAL / "PREFLIGHT_RESULT.json"
STOP = TRIAL / "STOP.json"
CODEX = Path(r"C:\Users\aaron\Documents\Codex\phase2b2-alpha-audit-20261015\win32-x64\package\vendor\x86_64-pc-windows-msvc\bin\codex.exe")
CODEX_HOME = Path(r"C:\Users\aaron\Documents\Codex\phase2b2-alpha-isolation-runtime-20261015")
VERSION = "codex-cli package 0.163.0-alpha.11-win32-x64"
OPERATION_CONTEXT = "phase2b2-alpha-isolation-preflight-20261015-v1"


def write_once(path, value):
    if path.exists():
        raise ValueError("EVIDENCE_ALREADY_EXISTS")
    path.write_text(json.dumps(value, indent=2, sort_keys=True,
                               ensure_ascii=True) + "\n", encoding="utf-8")


def main():
    if TRIAL.exists() or CODEX_HOME.exists():
        raise ValueError("PREFLIGHT_NOT_FRESH")
    TRIAL.mkdir()
    CODEX_HOME.mkdir()
    from phase2b2l_alpha_isolation_preflight.alpha_isolation_preflight import run_once
    result = run_once(
        executable=CODEX, version=VERSION, codex_home=CODEX_HOME,
        ledger_path=LEDGER, timeout_seconds=90,
        operation_context=OPERATION_CONTEXT)
    write_once(RESULT, result)
    write_once(STOP, {
        "frontier": ("PHASE_2B2_ALPHA_ISOLATION_PREFLIGHT_VERIFIED_NONCLAIM"
                     if result.get("status") == "VERIFIED"
                     else "PHASE_2B2_ALPHA_ISOLATION_PREFLIGHT_UNKNOWN_NONCLAIM"),
        "status": result.get("status"), "preserve": True,
        "allow_new_invocation": False, "retry_count": 0,
        "semantic_request_count": 0, "model_turn_count": 0,
        "authenticated": False, "phase2c_entered": False,
    })
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the single Phase 2B2R no-model preflight and persist its result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from phase2b2r_exact_codex_preflight.exact_codex_preflight import run_once


HERE = Path(__file__).resolve().parent
TRIAL = HERE / "trial"


def _write_json_once(path, value):
    path = Path(path)
    raw = (json.dumps(value, indent=2, sort_keys=True,
                      ensure_ascii=True) + "\n").encode("utf-8")
    with open(path, "xb") as target:
        target.write(raw)
        target.flush()
        import os
        os.fsync(target.fileno())
    if path.read_bytes() != raw:
        raise RuntimeError("RESULT_READBACK_MISMATCH")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    args = parser.parse_args(argv)
    if TRIAL.exists():
        raise ValueError("TRIAL_ALREADY_EXISTS")
    TRIAL.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="genie-phase2b2r-no-model-"))
    result = run_once(
        artifact_directory=args.artifact_directory,
        codex_home=args.codex_home,
        working_directory=scratch,
        ledger_path=TRIAL / "operation.sqlite",
        evidence_directory=TRIAL,
    )
    _write_json_once(TRIAL / "PREFLIGHT_RESULT.json", result)
    if result.get("status") == "OBSERVED_ACCEPTED" and not any(
            scratch.iterdir()):
        scratch.rmdir()
    else:
        _write_json_once(TRIAL / "PRESERVED_SCRATCH.json", {
            "path": str(scratch), "reason": result.get("status")})
    print(json.dumps({"status": result.get("status"),
                      "logical_operation_id": result.get(
                          "logical_operation_id")}, sort_keys=True))
    return 0 if result.get("status") == "OBSERVED_ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic no-model process-tree fixture for Phase 2B2B."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time


PROTOCOL = "genie-no-model-process-tree-fixture-v1"
EXPECTED_GATE = b"RELEASE_AFTER_JOB_ASSIGNMENT\n"


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")


def _parent():
    gate = sys.stdin.buffer.readline(len(EXPECTED_GATE) + 1)
    if gate != EXPECTED_GATE or sys.stdin.buffer.read(1):
        return 21
    argv = [
        sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
        "--role", "descendant",
    ]
    environment = {"GENIE_EXECUTION_CLASS": "NO_MODEL_CALL_CONTAINMENT_FIXTURE"}
    for key in ("SystemRoot", "WINDIR"):
        if key in os.environ:
            environment[key] = os.environ[key]
    child = subprocess.Popen(
        argv, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, cwd=Path.cwd(), env=environment,
        close_fds=True,
        creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
    report = {
        "protocol": PROTOCOL,
        "model_invoked": False,
        "parent_pid": os.getpid(),
        "descendant_pid": child.pid,
        "proposal": "NO_MODEL_CALL",
    }
    sys.stdout.buffer.write(_canonical(report) + b"\n")
    sys.stdout.buffer.flush()
    time.sleep(60)
    return 22


def _descendant():
    time.sleep(60)
    return 23


def main():
    if sys.argv == [str(Path(__file__).resolve()), "--role", "parent"]:
        return _parent()
    if sys.argv == [str(Path(__file__).resolve()), "--role", "descendant"]:
        return _descendant()
    return 20


if __name__ == "__main__":
    raise SystemExit(main())

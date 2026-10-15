"""Deterministic no-model JSONL event/process-tree fixture."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time


GATE = b"RELEASE_AFTER_JOB_ASSIGNMENT\n"
RESULT = {
    "authority_request": False,
    "marker": "NO_MODEL_EVENT_FIXTURE_20261015",
    "visible_tool_or_mcp_names": [],
}


def emit(value):
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def parent():
    if sys.stdin.buffer.readline(len(GATE) + 1) != GATE:
        return 21
    child = subprocess.Popen(
        [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
         "--role", "descendant"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, env={"EVENT_FIXTURE": "NO_MODEL"},
        cwd=Path.cwd(), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    emit({"type": "thread.started", "thread_id": "fixture-thread"})
    emit({"type": "turn.started"})
    emit({"type": "item.completed", "item": {"type": "reasoning",
                                                 "text": "fixture"}})
    emit({"type": "item.completed", "item": {"type": "plan",
                                                 "text": "fixture-unknown"}})
    emit({"type": "item.completed", "item": {"type": "agent_message",
                                                 "text": json.dumps(RESULT,
                                                                     sort_keys=True)}})
    emit({"type": "turn.completed", "usage": {"fixture": True},
          "model_invoked": False, "descendant_pid": child.pid})
    time.sleep(60)
    return 22


def descendant():
    time.sleep(60)
    return 23


def main():
    expected = str(Path(__file__).resolve())
    if sys.argv == [expected, "--role", "parent"]:
        return parent()
    if sys.argv == [expected, "--role", "descendant"]:
        return descendant()
    return 20


if __name__ == "__main__":
    raise SystemExit(main())

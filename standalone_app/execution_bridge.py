"""Provider-neutral standalone bridge over the accepted finite Genie driver.

The bridge injects no network/provider behavior. Worker/reviewer callables are
supplied by a trusted local host and the accepted session driver remains the
sole finite orchestration/callback implementation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import types

from desktop_plugin import live_state_windows as live

SESSION_DRIVER_SHA256 = "872903f1eaec93fce406662382fcadc896d28e8ce894cf60ae083d3e02dc5ab8"


class BridgeError(ValueError):
    pass


def _load_driver():
    try:
        source = Path(__file__).resolve().parents[1] / "shared_interfaces" / "session_driver.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != SESSION_DRIVER_SHA256:
            raise ValueError("driver source mismatch")
        module = types.ModuleType("_standalone_pinned_session_driver")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise BridgeError("BRIDGE_SOURCE_BINDING") from None


def drive(run_name, worker, reviewer, max_actions=64, notify=None, costs=None, materials=None):
    """Enter the accepted finite driver once and preserve its terminal result."""
    driver = _load_driver()
    try:
        runs = live.load_live_runs()
    except Exception:
        raise BridgeError("BRIDGE_LIVE_STATE_UNAVAILABLE") from None
    # Material selection is trusted local configuration. Hashes bind bytes,
    # not truth or permission to adopt any claim contained in those bytes.
    if type(materials) is not dict or any(type(k) is not str or type(v) is not str for k, v in materials.items()):
        raise BridgeError("BRIDGE_MATERIALS_REQUIRED")
    saved = dict(materials)
    try:
        events = driver._load_events()
        control = events._load_control()
        host = control.GenieRunController(runs)
        record = host._runs[run_name]
        core = control._load_facade()._load_core()
        with core.readonly(record[0]) as db:
            core.schema(db, {"entries": ["seq", "task_id", "plan", "state", "reason", "completion"]})
            plans = {task_id: json.loads(plan) for task_id, plan in db.execute("SELECT task_id,plan FROM entries")}
        if set(plans) != set(saved):
            raise ValueError("material coverage")
        bound = {}
        for task_id, text in saved.items():
            raw = text.encode("utf-8", errors="strict")
            if len(raw) > 1048576:
                raise ValueError("material bound")
            sha = hashlib.sha256(raw).hexdigest()
            if sha != plans[task_id]["input_sha256"]:
                raise ValueError("material binding")
            bound[task_id] = {"text": text, "input_sha256": sha, "content_role": "UNTRUSTED_TASK_INPUT"}
    except Exception:
        raise BridgeError("BRIDGE_MATERIAL_BINDING") from None

    def attached(hook):
        def call(action):
            material = bound[action["token"]["task_id"]]
            if material["input_sha256"] != action["token"]["input_sha256"]:
                raise BridgeError("BRIDGE_MATERIAL_BINDING")
            return hook({**action, "task_materials": dict(material)})
        return call
    try:
        result = driver.drive_run(
            runs, run_name, attached(worker), attached(reviewer),
            max_actions=max_actions, notify=notify, costs=costs)
    except Exception:
        # Unexpected bridge/driver-call failure is non-authorizing. The accepted
        # driver normally internalizes hook exceptions as UNKNOWN; this guard is
        # only for a failure outside its returned terminal contract.
        raise BridgeError("BRIDGE_OUTCOME_UNKNOWN") from None
    if type(result) is not dict:
        raise BridgeError("BRIDGE_OUTCOME_UNKNOWN")
    return result

"""Provider-neutral standalone bridge over the accepted finite Genie driver.

The bridge injects no network/provider behavior. Worker/reviewer callables are
supplied by a trusted local host and the accepted session driver remains the
sole finite orchestration/callback implementation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import types

import live_state_windows as live

SESSION_DRIVER_SHA256 = "89b0fd1ef48d5460dada5cc59b25072a10ec9b5c7049af25eabbb2d4464bf9d9"


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


def drive(run_name, worker, reviewer, max_actions=64, notify=None):
    """Enter the accepted finite driver once and preserve its terminal result."""
    driver = _load_driver()
    try:
        runs = live.load_live_runs()
    except Exception:
        raise BridgeError("BRIDGE_LIVE_STATE_UNAVAILABLE") from None
    try:
        result = driver.drive_run(
            runs, run_name, worker, reviewer,
            max_actions=max_actions, notify=notify)
    except Exception:
        # Unexpected bridge/driver-call failure is non-authorizing. The accepted
        # driver normally internalizes hook exceptions as UNKNOWN; this guard is
        # only for a failure outside its returned terminal contract.
        raise BridgeError("BRIDGE_OUTCOME_UNKNOWN") from None
    if type(result) is not dict:
        raise BridgeError("BRIDGE_OUTCOME_UNKNOWN")
    return result

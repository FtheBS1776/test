"""Controller-only MCP projection for one bounded Genie progression step.

This module is transport-neutral.  It pins and reuses the accepted
``GenieRunController`` rather than introducing a generic mutation API.  It
cannot dispatch a worker, apply an event, review content, loop, retry, refund,
reset a budget, or select a store path from model input.
"""
import hashlib
import json
from pathlib import Path
import types

RUN_CONTROL_SHA256 = "ecc71b088e5a7e3c0bde33b53a7e850dd769daee5b301f2f116edf956599f2d4"
NAME = "advance_run"
TITLE = "Advance one Genie run step"
ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": False,
}
ACTIONS = {
    "INVOKE_WORKER", "REVIEW_CANDIDATE", "TASK_COMPLETE", "RECONCILE_WORKER",
    "RECONCILE_HOST", "RECONCILE_SETUP", "RECONCILE_DESTINATION", "UNKNOWN",
    "HOLD", "STOP",
}


def _load_controller_module():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source unavailable")
        source = directory / "run_control.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != RUN_CONTROL_SHA256:
            raise ValueError("source mismatch")
        module = types.ModuleType("_mcp_pinned_run_control")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise ValueError("RUN_CONTROL_SOURCE_BINDING") from None


def _snapshot(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    raw.encode("utf-8", errors="strict")
    return json.loads(raw)


def _reject(reason):
    return {"structuredContent": {"status": "REJECT", "reason": reason}}


def _unknown():
    return {"structuredContent": {
        "action": "UNKNOWN",
        "reason": "MCP_CONTROLLER_OUTCOME_UNKNOWN",
        "preserve": True,
        "allow_new_invocation": False,
    }}


def _valid_result(value):
    if type(value) is not dict:
        return False
    if value.get("status") == "REJECT":
        return (set(value) == {"status", "reason"}
                and type(value["reason"]) is str and bool(value["reason"]))
    action = value.get("action")
    if type(action) is not str or action not in ACTIONS:
        return False
    if ("allow_new_invocation" in value
            and value["allow_new_invocation"] is not False):
        return False
    if action == "UNKNOWN":
        # Repair the projection boundary around an older permissive validator:
        # every uncertain write result must explicitly preserve state and deny
        # a new invocation.  A weaker shape becomes canonical UNKNOWN.
        return (value.get("preserve") is True
                and value.get("allow_new_invocation") is False)
    return True


class GenieMcpControllerConsumer:
    """Project exactly one controller operation into MCP tool semantics."""

    def __init__(self, runs):
        try:
            controller = _load_controller_module()
            self._controller = controller.GenieRunController(runs)
        except Exception:
            raise ValueError("RUN_CONTROL_SOURCE_BINDING_OR_REGISTRY") from None

    def tools(self):
        """Return one detached, explicitly mutating descriptor."""
        try:
            source = self._controller.tools()
            if (type(source) is not list or len(source) != 1
                    or type(source[0]) is not dict):
                raise ValueError("unexpected tool set")
            item = source[0]
            if (set(item) != {"name", "description", "inputSchema", "annotations"}
                    or item["name"] != NAME
                    or type(item["description"]) is not str
                    or not item["description"]
                    or item["inputSchema"] != {
                        "type": "object",
                        "properties": {"run_name": {"type": "string"}},
                        "required": ["run_name"],
                        "additionalProperties": False,
                    }
                    or item["annotations"] != ANNOTATIONS):
                raise ValueError("unexpected controller metadata")
            return _snapshot([{
                "name": NAME,
                "title": TITLE,
                "description": item["description"],
                "inputSchema": item["inputSchema"],
                "annotations": item["annotations"],
            }])
        except Exception:
            raise ValueError("INVALID_MCP_CONTROLLER_METADATA") from None

    def call(self, name, arguments):
        """Delegate once; never retry an exception or uncertain result."""
        if type(name) is not str or name != NAME or type(arguments) is not dict:
            return _reject("INVALID_TOOL_CALL")
        try:
            detached = _snapshot(arguments)
        except Exception:
            return _reject("INVALID_ARGUMENTS")
        try:
            # Exactly one call.  An exception can conceal committed state, so
            # this boundary returns UNKNOWN and never calls the controller again.
            result = _snapshot(self._controller.call(name, detached))
            return {"structuredContent": result} if _valid_result(result) else _unknown()
        except Exception:
            return _unknown()

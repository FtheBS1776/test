"""Controller-only MCP projection for one bound Genie event callback.

This transport-neutral projection pins and reuses ``GenieRunEvents``.  It does
not advance a run, invoke a worker or reviewer, choose a review decision,
retry a callback, or expose a store path.  The caller remains a trusted serial
controller; MCP metadata is not authorization.
"""
import hashlib
import json
from pathlib import Path
import types


RUN_EVENTS_SHA256 = "b150fef78663421b3ddf3f88267e33c5adeea5615d86275d5be35b4c88f28871"
INPUT_SCHEMA_SHA256 = "59fd685d201f46cfac160c371f25de5dc55a108c90ad3f28dcb1403331089634"
NAME = "apply_run_event"
TITLE = "Apply one bound Genie run event"
ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": False,
}
APPLIED_RESULTS = {
    "observe": {"RECORDED", "DUPLICATE"},
    "submit": {"SUBMITTED", "DUPLICATE"},
    "review": {"ACCEPT", "REPAIR", "DUPLICATE"},
}


def _load_events_module():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source unavailable")
        source = directory / "run_events.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != RUN_EVENTS_SHA256:
            raise ValueError("source mismatch")
        module = types.ModuleType("_mcp_pinned_run_events")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise ValueError("RUN_EVENTS_SOURCE_BINDING") from None


def _snapshot(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    raw.encode("utf-8", errors="strict")
    return json.loads(raw)


def _schema_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode(
                         "utf-8", errors="strict")
    return hashlib.sha256(raw).hexdigest()


def _reject(reason):
    return {"structuredContent": {"status": "REJECT", "reason": reason}}


def _unknown():
    return {"structuredContent": {
        "status": "UNKNOWN",
        "reason": "MCP_EVENTS_OUTCOME_UNKNOWN",
        "preserve": True,
        "allow_new_invocation": False,
    }}


def _valid_result(value, expected_operation=None, expected_decision=None):
    if type(value) is not dict:
        return False
    status = value.get("status")
    if status == "REJECT":
        return (set(value) == {"status", "reason"}
                and type(value["reason"]) is str and bool(value["reason"]))
    if status == "UNKNOWN":
        return (set(value) == {
                    "status", "reason", "preserve", "allow_new_invocation"}
                and type(value["reason"]) is str and bool(value["reason"])
                and value["preserve"] is True
                and value["allow_new_invocation"] is False)
    if (status != "APPLIED"
            or set(value) != {"status", "operation", "result"}):
        return False
    operation = value.get("operation")
    result = value.get("result")
    if (type(operation) is not str or operation not in APPLIED_RESULTS
            or operation != expected_operation
            or type(result) is not str or result not in APPLIED_RESULTS[operation]):
        return False
    return (operation != "review" or result == "DUPLICATE"
            or result == expected_decision)


class GenieMcpEventsConsumer:
    """Project exactly one existing event operation into MCP semantics."""

    def __init__(self, runs):
        try:
            events = _load_events_module()
            self._events = events.GenieRunEvents(runs)
        except Exception:
            raise ValueError("RUN_EVENTS_SOURCE_BINDING_OR_REGISTRY") from None

    def tools(self):
        """Return one detached, explicitly mutating descriptor."""
        try:
            source = self._events.tools()
            if (type(source) is not list or len(source) != 1
                    or type(source[0]) is not dict):
                raise ValueError("unexpected tool set")
            item = source[0]
            if (set(item) != {"name", "description", "inputSchema", "annotations"}
                    or item["name"] != NAME
                    or type(item["description"]) is not str
                    or not item["description"]
                    or type(item["inputSchema"]) is not dict
                    or _schema_hash(item["inputSchema"]) != INPUT_SCHEMA_SHA256
                    or item["annotations"] != ANNOTATIONS):
                raise ValueError("unexpected event metadata")
            return _snapshot([{
                "name": NAME,
                "title": TITLE,
                "description": item["description"],
                "inputSchema": item["inputSchema"],
                "annotations": item["annotations"],
            }])
        except Exception:
            raise ValueError("INVALID_MCP_EVENTS_METADATA") from None

    def call(self, name, arguments):
        """Delegate once; never retry an exception or uncertain result."""
        if type(name) is not str or name != NAME or type(arguments) is not dict:
            return _reject("INVALID_TOOL_CALL")
        try:
            detached = _snapshot(arguments)
        except Exception:
            return _reject("INVALID_ARGUMENTS")
        try:
            expected_operation = detached.get("operation")
            payload = detached.get("payload")
            expected_decision = (payload.get("decision")
                                 if type(payload) is dict else None)
            # Exactly one call.  Once the callback is entered, an exception can
            # conceal committed state, so uncertainty is preserved without retry.
            result = _snapshot(self._events.call(name, detached))
            return ({"structuredContent": result}
                    if _valid_result(
                        result, expected_operation, expected_decision) else _unknown())
        except Exception:
            return _unknown()

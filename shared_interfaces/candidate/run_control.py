"""Single-step progression for a trusted serial local Genie host.

This mutating surface is separate from the read-only catalog and CLI. It never
invokes workers, applies callbacks, approves candidates or retries a step.
Shared host configuration is not remote authorization or hostile confinement.
"""
import hashlib
import json
import math
from pathlib import Path
import types

FACADE_SHA256 = "37629d2ec2d8bdb88da66247c7093225e387b4d79220fb42b214cc01c8ef2619"
TOKEN_KEYS = {"run_id", "task_id", "input_sha256", "attempt", "slot_id", "call_id"}
REQUEST_KEYS = {"task_id", "input_sha256", "attempt", "goal", "feedback"}
ACTIONS = {
    "INVOKE_WORKER", "REVIEW_CANDIDATE", "TASK_COMPLETE", "RECONCILE_WORKER",
    "RECONCILE_HOST", "RECONCILE_SETUP", "RECONCILE_DESTINATION", "UNKNOWN",
    "HOLD", "STOP",
}


class _SourceError(ValueError):
    pass


def _reject(reason):
    return {"status": "REJECT", "reason": reason}


def _unknown():
    return {"action": "UNKNOWN", "reason": "STEP_OUTCOME_UNKNOWN",
            "preserve": True, "allow_new_invocation": False}


def _load_facade():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source location unavailable")
        source = directory / "status_tool.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != FACADE_SHA256:
            raise ValueError("source mismatch")
        module = types.ModuleType("_control_pinned_status_tool")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise _SourceError("FACADE_SOURCE_BINDING") from None


def _ident(value):
    return (type(value) is str and bool(value) and value == value.strip()
            and len(value) <= 200)


def _hash(value):
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _fields(value, keys):
    return (type(value) is dict and set(value) == keys
            and all(type(key) is str for key in value))


def _token(value, run_id):
    return (_fields(value, TOKEN_KEYS) and _ident(value["run_id"])
            and value["run_id"] == run_id and _ident(value["task_id"])
            and type(value["attempt"]) is int and 1 <= value["attempt"] <= 4
            and all(_hash(value[key]) for key in ("input_sha256", "slot_id", "call_id")))


def _request(value, token):
    return (_fields(value, REQUEST_KEYS) and _ident(value["task_id"])
            and _ident(value["goal"]) and _hash(value["input_sha256"])
            and type(value["attempt"]) is int and 1 <= value["attempt"] <= 4
            and all(value[key] == token[key] for key in ("task_id", "input_sha256", "attempt"))
            and (value["feedback"] is None or _ident(value["feedback"])))


def _json_tree(value, active):
    kind = type(value)
    if value is None or kind in (bool, int):
        return True
    if kind is str:
        value.encode("utf-8", errors="strict")
        return True
    if kind is float:
        return math.isfinite(value)
    if kind not in (dict, list) or id(value) in active:
        return False
    active.add(id(value))
    try:
        if kind is dict:
            return all(type(key) is str and _json_tree(key, active)
                       and _json_tree(item, active) for key, item in value.items())
        return all(_json_tree(item, active) for item in value)
    finally:
        active.remove(id(value))


def _valid_response(result, run_id):
    if (type(result) is not dict or type(result.get("action")) is not str
            or result["action"] not in ACTIONS or not _json_tree(result, set())):
        return False
    # Check that the preserved result remains representable as strict UTF8
    # JSON, without transforming its values or claiming store authenticity.
    json.dumps(result, allow_nan=False, ensure_ascii=False).encode("utf-8")
    action = result["action"]
    if action == "INVOKE_WORKER":
        return (_fields(result, {"action", "token", "request"})
                and _token(result["token"], run_id)
                and _request(result["request"], result["token"]))
    if action == "REVIEW_CANDIDATE":
        if (not _fields(result, {"action", "token", "candidate", "candidate_sha256"})
                or not _token(result["token"], run_id)
                or type(result["candidate"]) is not str
                or not result["candidate"].strip()
                or not _hash(result["candidate_sha256"])):
            return False
        raw = result["candidate"].encode("utf-8", errors="strict")
        return len(raw) <= 12000 and hashlib.sha256(raw).hexdigest() == result["candidate_sha256"]
    if "allow_new_invocation" in result and result["allow_new_invocation"] is not False:
        return False
    if "run_id" in result and result["run_id"] != run_id:
        return False
    if action == "RECONCILE_WORKER":
        return (_token(result.get("token"), run_id)
                and type(result.get("host")) is dict
                and result.get("allow_new_invocation") is False)
    if action == "STOP":
        return type(result.get("reason")) is str and bool(result["reason"])
    if action in ("TASK_COMPLETE", "RECONCILE_DESTINATION"):
        return _ident(result.get("task_id")) and type(result.get("result")) is dict
    return True


class GenieRunController:
    def __init__(self, runs):
        # Use the exact maintained constructor rather than introduce another
        # registry schema. Only detached immutable records are retained.
        try:
            facade = _load_facade()
            validated = facade.GenieStatusTools(runs)
            self._runs = dict(validated._runs)
        except _SourceError:
            raise ValueError("FACADE_SOURCE_BINDING") from None
        except Exception:
            raise ValueError("INVALID_RUN_REGISTRY") from None

    def tools(self):
        return [{
            "name": "advance_run",
            "description": (
                "Mutate an existing trusted local run by invoking its runner "
                "step once. May provision, reserve, deliver or persist STOP. "
                "Serial host only; not idempotent. Does not invoke a worker, "
                "review candidates, retry, reset budgets or grant remote authority. "
                "Post-call UNKNOWN requires reconciliation of original state."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"run_name": {"type": "string"}},
                "required": ["run_name"],
                "additionalProperties": False,
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        }]

    def call(self, tool_name, arguments):
        if type(tool_name) is not str or tool_name != "advance_run":
            return _reject("UNSUPPORTED_TOOL")
        if (not _fields(arguments, {"run_name"})
                or type(arguments["run_name"]) is not str):
            return _reject("INVALID_ARGUMENTS")
        alias = arguments["run_name"]
        if alias not in self._runs:
            return _reject("UNKNOWN_RUN")
        queue, run_id, root = self._runs[alias]
        try:
            facade = _load_facade()
            core = facade._load_core()
            runner = core.load_runner()
            # These prechecks cannot be confused with an entered mutating step.
            runner.context(queue, run_id)
        except _SourceError:
            return _reject("FACADE_SOURCE_BINDING")
        except Exception:
            return _reject("CORE_LOAD_OR_CONTEXT_FAILURE")
        try:
            # From this call onward, a failure can conceal committed state.
            # There is no rollback, safe-retry, refund or replacement assertion.
            result = runner.step(queue, run_id, root)
            return result if _valid_response(result, run_id) else _unknown()
        except Exception:
            return _unknown()

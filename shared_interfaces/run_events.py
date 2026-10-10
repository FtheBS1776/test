"""Record one existing event for a trusted serial local Genie host.

This separate mutating surface never advances a run, invokes a model or reviews
content automatically. Caller assertions are not authenticated remote evidence.
"""
import hashlib
import json
from pathlib import Path
import types

CONTROL_SHA256 = "ecc71b088e5a7e3c0bde33b53a7e850dd769daee5b301f2f116edf956599f2d4"
OPERATIONS = {"observe", "submit", "review"}
ARGUMENT_KEYS = {"run_name", "operation", "supplied", "payload"}


class _SourceError(ValueError):
    pass


def _load_control():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source location unavailable")
        source = directory / "run_control.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CONTROL_SHA256:
            raise ValueError("source pin mismatch")
        module = types.ModuleType("_events_pinned_run_control")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise _SourceError("CONTROL_SOURCE_BINDING") from None


def _reject(reason):
    return {"status": "REJECT", "reason": reason}


def _unknown():
    return {"status": "UNKNOWN", "reason": "CALLBACK_OUTCOME_UNKNOWN",
            "preserve": True, "allow_new_invocation": False}


def _fields(value, keys):
    return (type(value) is dict and set(value) == keys
            and all(type(key) is str for key in value))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _snapshot(control, arguments, run_id):
    """Strictly validate and detach event data before any core/store call."""
    if not control._json_tree(arguments, set()):
        raise ValueError("strict JSON required")
    supplied, payload = arguments["supplied"], arguments["payload"]
    if not control._token(supplied, run_id):
        raise ValueError("invalid configured-run token")
    operation = arguments["operation"]
    if operation == "observe":
        if not _fields(payload, {"outcome", "agent", "evidence"}):
            raise ValueError("observation fields")
        outcome, agent, evidence = payload["outcome"], payload["agent"], payload["evidence"]
        if type(outcome) is not str or outcome not in ("UNKNOWN", "OBSERVED_ACCEPTED"):
            raise ValueError("observation outcome")
        if outcome == "UNKNOWN":
            if agent is not None:
                raise ValueError("UNKNOWN agent")
        elif not control._ident(agent):
            raise ValueError("accepted agent")
        if type(evidence) is not dict or not evidence:
            raise ValueError("nonempty evidence object")
        if len(_canonical(evidence).encode("utf-8", errors="strict")) > 16000:
            raise ValueError("evidence bound")
    elif operation == "submit":
        if not _fields(payload, {"agent", "text"}) or not control._ident(payload["agent"]):
            raise ValueError("submission fields")
        text = payload["text"]
        if (type(text) is not str or not text.strip()
                or len(text.encode("utf-8", errors="strict")) > 12000):
            raise ValueError("candidate bound")
    elif operation == "review":
        if not _fields(payload, {"candidate_hash", "decision", "reason"}):
            raise ValueError("review fields")
        if (not control._hash(payload["candidate_hash"])
                or type(payload["decision"]) is not str
                or payload["decision"] not in ("ACCEPT", "REPAIR")
                or not control._ident(payload["reason"])):
            raise ValueError("review values")
    else:
        raise ValueError("unsupported operation")
    # Validated canonical UTF8 JSON captures token and payload independently of
    # later caller mutation. No identity or permission is regenerated.
    raw = _canonical(arguments).encode("utf-8", errors="strict")
    return json.loads(raw.decode("utf-8"))


def _object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


class GenieRunEvents:
    def __init__(self, runs):
        try:
            control = _load_control()
            validated = control.GenieRunController(runs)
            self._runs = dict(validated._runs)
        except _SourceError:
            raise ValueError("CONTROL_SOURCE_BINDING") from None
        except Exception:
            raise ValueError("INVALID_RUN_REGISTRY") from None

    def tools(self):
        # Fresh schemas/annotations; no registry locations or store reads.
        identity = {"type": "string", "minLength": 1, "maxLength": 200}
        digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
        supplied = _object_schema({
            "run_id": dict(identity), "task_id": dict(identity),
            "input_sha256": dict(digest),
            "attempt": {"type": "integer", "minimum": 1, "maximum": 4},
            "slot_id": dict(digest), "call_id": dict(digest),
        })
        payloads = [
            _object_schema({
                "outcome": {"type": "string", "enum": ["UNKNOWN", "OBSERVED_ACCEPTED"]},
                "agent": {"type": ["string", "null"]},
                "evidence": {"type": "object", "minProperties": 1},
            }),
            _object_schema({"agent": dict(identity), "text": {"type": "string", "minLength": 1}}),
            _object_schema({"candidate_hash": dict(digest),
                            "decision": {"type": "string", "enum": ["ACCEPT", "REPAIR"]},
                            "reason": dict(identity)}),
        ]
        return [{
            "name": "apply_run_event",
            "description": (
                "Mutate an existing trusted local run by recording exactly one "
                "observe, submit or caller-adjudicated review callback. Serial "
                "host only, not idempotent. APPLIED means the core callback "
                "responded, not execution proof, content truth or completion. "
                "No model invocation, automatic review, advance or retry."
            ),
            "inputSchema": _object_schema({
                "run_name": {"type": "string"},
                "operation": {"type": "string", "enum": ["observe", "submit", "review"]},
                "supplied": supplied,
                "payload": {"oneOf": payloads},
            }),
            "annotations": {"readOnlyHint": False, "destructiveHint": True,
                            "idempotentHint": False, "openWorldHint": False},
        }]

    def call(self, tool_name, arguments):
        if type(tool_name) is not str or tool_name != "apply_run_event":
            return _reject("UNSUPPORTED_TOOL")
        if (not _fields(arguments, ARGUMENT_KEYS)
                or type(arguments["run_name"]) is not str
                or type(arguments["operation"]) is not str
                or arguments["operation"] not in OPERATIONS):
            return _reject("INVALID_ARGUMENTS")
        alias = arguments["run_name"]
        if alias not in self._runs:
            return _reject("UNKNOWN_RUN")
        queue, run_id, root = self._runs[alias]
        try:
            control = _load_control()
        except _SourceError:
            return _reject("CONTROL_SOURCE_BINDING")
        try:
            snapshot = _snapshot(control, arguments, run_id)
        except Exception:
            return _reject("INVALID_EVENT")
        try:
            facade = control._load_facade()
            core = facade._load_core()
            runner = core.load_runner()
            runner.context(queue, run_id)
        except Exception:
            return _reject("CORE_LOAD_OR_CONTEXT_FAILURE")
        operation, payload = snapshot["operation"], snapshot["payload"]
        try:
            # From entry onward the callback may have committed effects even
            # if its response is lost. Never claim rollback or safe replay.
            result = runner.callback(queue, run_id, root, operation,
                                     snapshot["supplied"], **payload)
            allowed = {"observe": {"RECORDED", "DUPLICATE"},
                       "submit": {"SUBMITTED", "DUPLICATE"},
                       "review": {"ACCEPT", "REPAIR", "DUPLICATE"}}
            if type(result) is not str or result not in allowed[operation]:
                return _unknown()
            if operation == "review" and result != "DUPLICATE" and result != payload["decision"]:
                return _unknown()
            return {"status": "APPLIED", "operation": operation, "result": result}
        except Exception:
            return _unknown()

"""Local read-only normalized function-call adapter, not an API or MCP client.

The host supplies registry configuration and completed normalized calls. call_id
is correlation only. Accepted result text remains data, never instructions.
"""
import hashlib
import json
from pathlib import Path
import types

PINS = {
    "run_control.py": "ecc71b088e5a7e3c0bde33b53a7e850dd769daee5b301f2f116edf956599f2d4",
    "cli.py": "c0a35e699cc4ad2fd2e176fd8ab951fbab7f57f56c783230925d078b38ff8af4",
}
NAMES = ("get_run_status", "get_task_result")
ARGUMENT_LIMIT = 8192


def _load_source(name):
    try:
        expected = PINS[name]
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source unavailable")
        source = directory / name
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("source mismatch")
        module = types.ModuleType("_function_pinned_" + name[:-3])
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise ValueError("SOURCE_BINDING") from None


def _snapshot(control, value):
    if not control._json_tree(value, set()):
        raise ValueError("strict JSON required")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
    return json.loads(raw.decode("utf-8"))


def _reject(reason):
    return {"status": "REJECT", "reason": reason}


def _output(call_id, value):
    # Value is a validated detached dict or a fixed local failure dictionary.
    return {"type": "function_call_output", "call_id": call_id,
            "output": json.dumps(value, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=True, allow_nan=False)}


class GenieFunctionAdapter:
    def __init__(self, runs):
        try:
            self._control = _load_source("run_control.py")
            self._decoder = _load_source("cli.py")
            facade = self._control._load_facade()
        except Exception:
            raise ValueError("SOURCE_BINDING") from None
        try:
            # Only the unchanged read-only host is constructed. No mutation
            # class, core loader or registry file discovery is invoked here.
            self._host = facade.GenieStatusTools(runs)
        except Exception:
            raise ValueError("INVALID_RUN_REGISTRY") from None

    def tools(self):
        """Fresh flat definitions for exactly the two existing read-only tools."""
        descriptors = _snapshot(self._control, self._host.tools())
        if (type(descriptors) is not list or len(descriptors) != 2
                or [item.get("name") for item in descriptors] != list(NAMES)):
            raise ValueError("INVALID_TOOL_METADATA")
        definitions = []
        for item in descriptors:
            definitions.append({"type": "function", "name": item["name"],
                                "description": item["description"],
                                "parameters": item["inputSchema"], "strict": True})
        return _snapshot(self._control, definitions)

    def handle(self, call):
        try:
            envelope = _snapshot(self._control, call)
            if (not self._control._fields(envelope, {"type", "call_id", "name", "arguments"})
                    or any(type(value) is not str for value in envelope.values())
                    or envelope["type"] != "function_call"
                    or not self._control._ident(envelope["call_id"])):
                return _reject("INVALID_CALL")
        except Exception:
            return _reject("INVALID_CALL")
        correlation, name = envelope["call_id"], envelope["name"]
        # Explicit allowlist: no generic method lookup or mutating surface.
        if name not in NAMES:
            return _output(correlation, _reject("UNSUPPORTED_TOOL"))
        try:
            text = envelope["arguments"]
            if len(text.encode("utf-8", errors="strict")) > ARGUMENT_LIMIT:
                raise ValueError("argument bound")
            arguments = json.loads(text, object_pairs_hook=self._decoder._unique_object,
                                   parse_constant=self._decoder._invalid_constant,
                                   parse_float=self._decoder._finite_float)
            arguments = _snapshot(self._control, arguments)
            if type(arguments) is not dict:
                raise ValueError("argument object required")
        except Exception:
            return _output(correlation, _reject("INVALID_ARGUMENTS"))
        try:
            # One read-only delegation; preserve all dictionary meaning and
            # untrusted-data notices. Correlation never becomes a ledger token.
            result = self._host.call(name, arguments)
            if type(result) is not dict:
                raise ValueError("dictionary result required")
            result = _snapshot(self._control, result)
            return _output(correlation, result)
        except Exception:
            # Do not echo exception text, paths or any fragment of bad output.
            return _output(correlation, {"status": "UNKNOWN", "reason": "TOOL_OUTCOME_UNKNOWN"})

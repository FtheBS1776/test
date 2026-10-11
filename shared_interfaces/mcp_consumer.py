"""Dependency-free ChatGPT MCP read-only consumer projection for Genie.

This is not an MCP server, transport, authentication layer, backend, model
client, or authority mechanism. It projects the already accepted local
read-only function adapter into MCP tool descriptors and tool-result objects.
"""
import hashlib
import json
from pathlib import Path
import secrets
import types

ADAPTER_SHA256 = "9627bc0967e4b6115f405671be8a2c60498101e276d96062d55572537f2769d2"
NAMES = ("get_run_status", "get_task_result")
TITLES = {
    "get_run_status": "Get Genie run status",
    "get_task_result": "Get Genie task result",
}
ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


def _load_adapter():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source unavailable")
        source = directory / "function_adapter.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ADAPTER_SHA256:
            raise ValueError("source mismatch")
        module = types.ModuleType("_mcp_pinned_function_adapter")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise ValueError("ADAPTER_SOURCE_BINDING") from None


def _snapshot(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    raw.encode("utf-8", errors="strict")
    return json.loads(raw)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("nonfinite number")


def _decode_object(text):
    value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    if type(value) is not dict:
        raise ValueError("dictionary required")
    return _snapshot(value)


def _unknown():
    return {"structuredContent": {
        "status": "UNKNOWN", "reason": "MCP_CONSUMER_OUTCOME_UNKNOWN"
    }}


class GenieMcpReadonlyConsumer:
    """Project exact read-only Genie calls into MCP-compatible tool semantics."""

    def __init__(self, runs):
        try:
            adapter = _load_adapter()
            self._adapter = adapter.GenieFunctionAdapter(runs)
        except Exception:
            raise ValueError("ADAPTER_SOURCE_BINDING_OR_REGISTRY") from None

    def tools(self):
        """Return exactly two detached MCP tool descriptors; no transport setup."""
        try:
            source = self._adapter.tools()
            if (type(source) is not list or len(source) != 2
                    or [item.get("name") for item in source] != list(NAMES)):
                raise ValueError("unexpected tool set")
            projected = []
            for item in source:
                if (type(item) is not dict
                        or set(item) != {"type", "name", "description", "parameters", "strict"}
                        or item["type"] != "function" or item["strict"] is not True
                        or type(item["description"]) is not str
                        or type(item["parameters"]) is not dict):
                    raise ValueError("unexpected adapter metadata")
                name = item["name"]
                projected.append({
                    "name": name,
                    "title": TITLES[name],
                    "description": item["description"],
                    "inputSchema": item["parameters"],
                    "annotations": dict(ANNOTATIONS),
                })
            return _snapshot(projected)
        except Exception:
            raise ValueError("INVALID_MCP_TOOL_METADATA") from None

    def call(self, name, arguments):
        """Call one projected read-only tool and return an MCP tool-result object."""
        if type(name) is not str or name not in NAMES or type(arguments) is not dict:
            return {"structuredContent": {"status": "REJECT", "reason": "INVALID_TOOL_CALL"}}
        try:
            detached = _snapshot(arguments)
            encoded = json.dumps(detached, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False)
            encoded.encode("utf-8", errors="strict")
        except Exception:
            return {"structuredContent": {"status": "REJECT", "reason": "INVALID_ARGUMENTS"}}
        try:
            correlation = "mcp-" + secrets.token_hex(16)
            reply = self._adapter.handle({
                "type": "function_call",
                "call_id": correlation,
                "name": name,
                "arguments": encoded,
            })
            if (type(reply) is not dict
                    or set(reply) != {"type", "call_id", "output"}
                    or reply["type"] != "function_call_output"
                    or reply["call_id"] != correlation
                    or type(reply["output"]) is not str):
                return _unknown()
            result = _decode_object(reply["output"])
            if "result_text" in result:
                if (result.get("content_role") != "UNTRUSTED_ACCEPTED_TASK_DATA"
                        or type(result.get("content_notice")) is not str
                        or not result["content_notice"]):
                    return _unknown()
            return {"structuredContent": result}
        except Exception:
            return _unknown()

"""Pure consumer contract for a future ChatGPT/MCP plugin.

This module is not an MCP server or transport. It maps MCP-style tool metadata
and structured calls to the already accepted read-only GenieFunctionAdapter.
Core result dictionaries are preserved as data; wrapper failures alone become
MCP-level tool errors.
"""
import hashlib
import json
import math
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
    "openWorldHint": False,
}
ARGUMENT_LIMIT = 8192


def _load_adapter_module():
    try:
        source = Path(__file__).resolve().parents[1] / "shared_interfaces" / "function_adapter.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ADAPTER_SHA256:
            raise ValueError("adapter mismatch")
        module = types.ModuleType("_pinned_genie_function_adapter")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise ValueError("ADAPTER_BINDING") from None


def _json_tree(value, seen):
    kind = type(value)
    if value is None or kind is bool or kind is int:
        return True
    if kind is float:
        return math.isfinite(value)
    if kind is str:
        try:
            value.encode("utf-8", errors="strict")
            return True
        except UnicodeError:
            return False
    if kind is list:
        marker = id(value)
        if marker in seen:
            return False
        seen.add(marker)
        ok = all(_json_tree(item, seen) for item in value)
        seen.remove(marker)
        return ok
    if kind is dict:
        marker = id(value)
        if marker in seen:
            return False
        seen.add(marker)
        ok = True
        for key, item in value.items():
            if type(key) is not str or not _json_tree(key, seen) or not _json_tree(item, seen):
                ok = False
                break
        seen.remove(marker)
        return ok
    return False


def _snapshot(value):
    if not _json_tree(value, set()):
        raise ValueError("strict JSON required")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
    return json.loads(raw.decode("utf-8"))


def _strict_load(text):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate key")
            out[key] = value
        return out

    def constant(_):
        raise ValueError("nonfinite")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite")
        return number

    value = json.loads(text, object_pairs_hook=unique,
                       parse_constant=constant, parse_float=finite_float)
    return _snapshot(value)


def _tool_error():
    return {
        "content": [{"type": "text", "text": "Genie plugin wrapper could not safely complete this tool call."}],
        "isError": True,
    }


class GeniePluginConsumer:
    """Transport-free ChatGPT/MCP consumer boundary over the accepted adapter."""

    def __init__(self, runs):
        module = _load_adapter_module()
        self._adapter = module.GenieFunctionAdapter(runs)

    def tools(self):
        """Return detached MCP-compatible metadata for exactly two read-only tools."""
        raw = _snapshot(self._adapter.tools())
        if type(raw) is not list or len(raw) != 2 or any(type(item) is not dict for item in raw):
            raise ValueError("ADAPTER_METADATA")
        if [item.get("name") for item in raw] != list(NAMES):
            raise ValueError("ADAPTER_METADATA")
        tools = []
        for item in raw:
            if (set(item) != {"type", "name", "description", "parameters", "strict"}
                    or item["type"] != "function" or item["strict"] is not True
                    or type(item["description"]) is not str or not item["description"]
                    or type(item["parameters"]) is not dict):
                raise ValueError("ADAPTER_METADATA")
            name = item["name"]
            tools.append({
                "name": name,
                "title": TITLES[name],
                "description": item["description"],
                "inputSchema": item["parameters"],
                "annotations": dict(ANNOTATIONS),
            })
        return _snapshot(tools)

    def call_tool(self, name, arguments):
        """Map one structured consumer call to one adapter call and MCP-style result."""
        try:
            # MCP supplies structured arguments. Normalize once to the adapter's
            # accepted JSON-string boundary; no caller ID becomes Genie authority.
            args = _snapshot(arguments)
            args_text = json.dumps(args, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False, allow_nan=False)
            if len(args_text.encode("utf-8", errors="strict")) > ARGUMENT_LIMIT:
                raise ValueError("argument bound")
            if type(name) is not str:
                raise ValueError("name")
            name.encode("utf-8", errors="strict")
            correlation = "mcp-local-" + secrets.token_hex(16)
            reply = self._adapter.handle({
                "type": "function_call",
                "call_id": correlation,
                "name": name,
                "arguments": args_text,
            })
            if (type(reply) is not dict
                    or set(reply) != {"type", "call_id", "output"}
                    or reply.get("type") != "function_call_output"
                    or reply.get("call_id") != correlation
                    or type(reply.get("output")) is not str):
                raise ValueError("adapter envelope")
            result = _strict_load(reply["output"])
            if type(result) is not dict:
                raise ValueError("adapter result")
            # Genie semantic states remain ordinary structured data. In particular,
            # UNKNOWN/REJECT are not rewritten as transport success or failure.
            text = json.dumps(result, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=True, allow_nan=False)
            return _snapshot({
                "structuredContent": result,
                "content": [{"type": "text", "text": text}],
            })
        except Exception:
            return _tool_error()

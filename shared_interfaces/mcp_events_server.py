"""Local stdio MCP transport for Genie's isolated Phase 2B1 event surface.

The only exposed operation is the pinned event facade's non-idempotent
``apply_run_event``.  This process contains no progression tool, worker or
reviewer dispatcher, automatic review, session driver, loop, retry, network
listener, or read-only Genie tools.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import types


CONSUMER_SHA256 = "33bdac26577380ee473e75f0f810a1e50c4f6e2c7e33c095ed21436d8d03a8ba"
INPUT_SCHEMA_SHA256 = "59fd685d201f46cfac160c371f25de5dc55a108c90ad3f28dcb1403331089634"
SERVER_VERSION = "0.1.0-phase2b1-nonclaim"
TRANSPORT_DISTRIBUTIONS = {
    "mcp": "2.3.0",
    "mcp-types": "2.3.0",
    "annotated-types": "0.8.0",
    "anyio": "4.15.1",
    "attrs": "26.1.0",
    "cffi": "2.1.1",
    "click": "8.5.0",
    "cryptography": "50.0.2",
    "h11": "0.16.0",
    "httpcore2": "2.13.1",
    "httpx2": "2.13.1",
    "idna": "3.20",
    "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1",
    "opentelemetry-api": "1.45.1",
    "pycparser": "3.11",
    "pydantic": "2.14.1",
    "pydantic-core": "2.50.1",
    "PyJWT": "2.15.1",
    "python-multipart": "0.0.32",
    "referencing": "0.37.0",
    "rpds-py": "2026.9.1",
    "sse-starlette": "3.5.0",
    "starlette": "1.7.0",
    "truststore": "0.10.4",
    "typing-extensions": "4.16.0",
    "typing-inspection": "0.4.4",
    "uvicorn": "0.54.0",
}
WINDOWS_TRANSPORT_DISTRIBUTIONS = {"pywin32": "312"}
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


def required_transport_distributions():
    required = dict(TRANSPORT_DISTRIBUTIONS)
    if os.name == "nt":
        required.update(WINDOWS_TRANSPORT_DISTRIBUTIONS)
    return required


def _require_sdk():
    try:
        for distribution, expected in required_transport_distributions().items():
            if metadata.version(distribution) != expected:
                raise ValueError("version mismatch")
        from mcp.server import Server
        from mcp.types import (CallToolResult, ListToolsResult, TextContent,
                               Tool, ToolAnnotations)
        return types.SimpleNamespace(
            Server=Server, CallToolResult=CallToolResult,
            ListToolsResult=ListToolsResult, TextContent=TextContent,
            Tool=Tool, ToolAnnotations=ToolAnnotations)
    except Exception:
        raise ValueError("MCP_SDK_VERSION_BINDING") from None


def _load_consumer_module():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source unavailable")
        source = directory / "mcp_events.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CONSUMER_SHA256:
            raise ValueError("source mismatch")
        module = types.ModuleType("_pinned_genie_mcp_events")
        module.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise ValueError("MCP_EVENTS_SOURCE_BINDING") from None


def _unknown():
    return {
        "status": "UNKNOWN",
        "reason": "MCP_EVENTS_SERVER_OUTCOME_UNKNOWN",
        "preserve": True,
        "allow_new_invocation": False,
    }


def _schema_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode(
                         "utf-8", errors="strict")
    return hashlib.sha256(raw).hexdigest()


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


def build_server_from_consumer(consumer):
    sdk = _require_sdk()
    descriptors = consumer.tools()
    if (type(descriptors) is not list or len(descriptors) != 1
            or type(descriptors[0]) is not dict):
        raise ValueError("INVALID_MCP_EVENTS_METADATA")
    item = descriptors[0]
    if (set(item) != {"name", "title", "description", "inputSchema", "annotations"}
            or item["name"] != "apply_run_event"
            or item["title"] != "Apply one bound Genie run event"
            or type(item["description"]) is not str or not item["description"]
            or type(item["inputSchema"]) is not dict
            or _schema_hash(item["inputSchema"]) != INPUT_SCHEMA_SHA256
            or item["annotations"] != ANNOTATIONS):
        raise ValueError("INVALID_MCP_EVENTS_METADATA")
    tool = sdk.Tool(
        name=item["name"], title=item["title"],
        description=item["description"], input_schema=item["inputSchema"],
        annotations=sdk.ToolAnnotations(
            read_only_hint=False, destructive_hint=True,
            idempotent_hint=False, open_world_hint=False))

    async def list_tools(_ctx, _params):
        return sdk.ListToolsResult(tools=[tool])

    async def call_tool(_ctx, params):
        arguments = params.arguments if params.arguments is not None else {}
        try:
            expected_operation = (arguments.get("operation")
                                  if type(arguments) is dict else None)
            payload = arguments.get("payload") if type(arguments) is dict else None
            expected_decision = (payload.get("decision")
                                 if type(payload) is dict else None)
            # One delegate call only.  There is deliberately no retry branch.
            projected = consumer.call(params.name, arguments)
            if (type(projected) is not dict or set(projected) != {"structuredContent"}
                    or type(projected["structuredContent"]) is not dict):
                raise ValueError("projection shape")
            encoded = json.dumps(
                projected["structuredContent"], sort_keys=True,
                separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            detached = json.loads(encoded)
            if not _valid_result(
                    detached, expected_operation, expected_decision):
                raise ValueError("projection result")
        except Exception:
            detached = _unknown()
        label = detached.get("status", "UNKNOWN")
        safe_text = "Genie Phase 2B1 event result; status=" + str(label)
        if detached.get("status") == "APPLIED":
            safe_text += "; callback acknowledgement only"
        if detached.get("status") == "UNKNOWN":
            safe_text += "; preserve state; do not retry"
        return sdk.CallToolResult(
            content=[sdk.TextContent(type="text", text=safe_text)],
            structured_content=detached,
            is_error=False)

    return sdk.Server(
        "Genie Phase 2B1 Events", version=SERVER_VERSION,
        instructions=(
            "Controller-only local event surface. apply_run_event records one "
            "already-bound trusted-host observation, submission, or separately "
            "adjudicated review. APPLIED is not execution proof, content truth, "
            "or completion. This server cannot advance or dispatch models. "
            "UNKNOWN requires preservation and is not retry permission."),
        on_list_tools=list_tools, on_call_tool=call_tool)


def build_server(runs):
    consumer_module = _load_consumer_module()
    consumer = consumer_module.GenieMcpEventsConsumer(runs)
    return build_server_from_consumer(consumer)


def _parser():
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Local stdio-only Genie Phase 2B1 events; exactly one tool.")
    parser.add_argument("--registry", required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    from shared_interfaces import cli
    runs = cli._read_registry(args.registry)
    server = build_server(runs)
    import anyio
    from mcp.server.stdio import stdio_server

    async def arun():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream,
                server.create_initialization_options())

    anyio.run(arun)


if __name__ == "__main__":
    main()

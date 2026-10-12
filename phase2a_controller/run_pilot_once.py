"""Make the sole recorded Phase 2A MCP mutation call; never retry it."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from mcp import Client, StdioServerParameters


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Path(__file__).resolve().parent / "trial" / "REGISTRY.json"
ALIAS = "phase2a-synthetic-20261012"


async def _run():
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-B", "-m", "shared_interfaces.mcp_controller_server",
            "--registry", str(REGISTRY),
        ],
        cwd=str(ROOT),
    )
    async with Client(params) as client:
        listed = await client.list_tools()
        if len(listed.tools) != 1 or listed.tools[0].name != "advance_run":
            raise ValueError("PILOT_TOOL_SURFACE")
        annotations = listed.tools[0].annotations
        observed_annotations = {
            "readOnlyHint": annotations.read_only_hint,
            "destructiveHint": annotations.destructive_hint,
            "idempotentHint": annotations.idempotent_hint,
            "openWorldHint": annotations.open_world_hint,
        }
        expected_annotations = {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
        if observed_annotations != expected_annotations:
            raise ValueError("PILOT_TOOL_ANNOTATIONS")

        # This is intentionally the only call_tool site in the recorded pilot.
        # Any UNKNOWN or transport uncertainty terminates the script without retry.
        result = await client.call_tool("advance_run", {"run_name": ALIAS})
        return {
            "tool_names": [tool.name for tool in listed.tools],
            "annotations": observed_annotations,
            "is_error": result.is_error,
            "text": [item.text for item in result.content],
            "structured_content": result.structured_content,
            "call_count": 1,
            "retry_count": 0,
        }


def main():
    result = asyncio.run(_run())
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

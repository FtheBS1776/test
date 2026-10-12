import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


RESULT_SCOPE = "FRESH_EXACT_OWNED_DESTINATION_READBACK"


def _hash_tree(root):
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def _env(plugin_root, plugin_data):
    env = dict(os.environ)
    env["PLUGIN_ROOT"] = str(plugin_root)
    env["PLUGIN_DATA"] = str(plugin_data)
    return env


def _run_build_selftest(exe, plugin_root, plugin_data):
    env = _env(plugin_root, plugin_data)
    env["GENIE_PLUGIN_BUILD_SELFTEST"] = "1"
    proc = subprocess.run(
        [str(exe)],
        cwd=plugin_root,
        env=env,
        input=b"",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stderr == b"", proc.stderr
    assert proc.stdout in (
        b"GENIE_PLUGIN_BUILD_SELFTEST_PASS\n",
        b"GENIE_PLUGIN_BUILD_SELFTEST_PASS\r\n",
    ), proc.stdout


async def _exercise(exe, plugin_root, plugin_data):
    from mcp import Client, StdioServerParameters

    params = StdioServerParameters(
        command=str(exe),
        args=[],
        cwd=str(plugin_root),
        env=_env(plugin_root, plugin_data),
    )
    async with Client(params) as client:
        listed = await client.list_tools()
        names = [tool.name for tool in listed.tools]
        assert names == ["get_run_status", "get_task_result"], names

        status = await client.call_tool("get_run_status", {"run_name": "actual"})
        structured = status.structured_content
        assert type(structured) is dict and structured.get("status") == "PASS", structured
        tasks = structured.get("tasks")
        assert type(tasks) is list and tasks, tasks
        confirmed = [
            item for item in tasks
            if type(item) is dict
            and type(item.get("fresh_sink")) is dict
            and item["fresh_sink"].get("status") == "CONFIRMED"
        ]
        assert confirmed, structured
        task_id = confirmed[0]["task_id"]

        result = await client.call_tool(
            "get_task_result", {"run_name": "actual", "task_id": task_id})
        body = result.structured_content
        assert type(body) is dict and body.get("status") == "CONFIRMED", body
        assert body.get("content_role") == "UNTRUSTED_ACCEPTED_TASK_DATA", body
        assert type(body.get("result_text")) is str and body["result_text"], body
        assert body["result_text"] not in result.content[0].text
        assert "UNTRUSTED DATA" in result.content[0].text

        rejected = await client.call_tool(
            "get_task_result", {"run_name": "does-not-exist", "task_id": task_id})
        rejected_body = rejected.structured_content
        assert rejected_body == {"status": "REJECT", "reason": "UNKNOWN_RUN"}, rejected_body

        unavailable = await client.call_tool(
            "get_task_result", {"run_name": "synthetic-unknown", "task_id": task_id})
        unavailable_body = unavailable.structured_content
        assert unavailable_body == {
            "status": "UNKNOWN",
            "reason": "TASK_RESULT_UNAVAILABLE",
            "evidence_scope": RESULT_SCOPE,
        }, unavailable_body
        assert "result_text" not in unavailable_body
        assert "status=UNKNOWN" in unavailable.content[0].text
        return task_id


def _expect_partial_preserve(exe, plugin_root, data):
    proc = subprocess.run(
        [str(exe)],
        cwd=plugin_root,
        env=_env(plugin_root, data),
        input=b"",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout == b"", proc.stdout
    expected_lf = b"GENIE_PLUGIN_REJECT:PLUGIN_STATE_PARTIAL_PRESERVE\n"
    expected_crlf = b"GENIE_PLUGIN_REJECT:PLUGIN_STATE_PARTIAL_PRESERVE\r\n"
    assert proc.stderr in (expected_lf, expected_crlf), proc.stderr


def main():
    plugin_root = Path(os.environ["GENIE_PLUGIN_ROOT"]).resolve(strict=True)
    exe = plugin_root / "bin" / "genie-mcp.exe"
    assert exe.is_file(), exe

    manifest = _load_json(plugin_root / "plugin.json")
    assert manifest == {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "genie-readonly",
        "version": "0.1.1",
        "description": "Read bounded local Genie run diagnostics and confirmed accepted task results without granting new authority.",
    }
    mcp = _load_json(plugin_root / "mcp.json")
    assert mcp == {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            "genie-readonly": {
                "type": "stdio",
                "command": "./bin/genie-mcp.exe",
                "cwd": "${PLUGIN_ROOT}",
            }
        },
    }
    codex_manifest = _load_json(plugin_root / ".codex-plugin" / "plugin.json")
    assert codex_manifest["name"] == "genie-readonly"
    assert codex_manifest["version"] == "0.1.1"
    assert codex_manifest["mcpServers"] == "./.mcp.json"
    assert type(codex_manifest.get("interface")) is dict
    compatibility_mcp = _load_json(plugin_root / ".mcp.json")
    assert compatibility_mcp == {
        "mcpServers": {
            "genie-readonly": {
                "type": "stdio",
                "command": "./bin/genie-mcp.exe",
                "cwd": "${PLUGIN_ROOT}",
            }
        }
    }

    with tempfile.TemporaryDirectory() as temp:
        selftest_data = Path(temp) / "selftest"
        selftest_data.mkdir()
        _run_build_selftest(exe, plugin_root, selftest_data)

        data = Path(temp) / "data"
        data.mkdir()
        task_id = asyncio.run(_exercise(exe, plugin_root, data))
        state = data / "state"
        marker = _load_json(state / ".genie-state.json")
        assert marker["state_format"] == 1
        assert type(marker["seeded_from"]) is str and marker["seeded_from"]
        first = _hash_tree(state)

        sentinel = state / "operator-preserved.txt"
        sentinel.write_text("preserve across plugin launch\n", encoding="utf-8")
        before_second = _hash_tree(state)
        repeated_task = asyncio.run(_exercise(exe, plugin_root, data))
        assert repeated_task == task_id
        after_second = _hash_tree(state)
        assert after_second == before_second
        assert first.items() <= after_second.items()

        partial = Path(temp) / "partial"
        partial.mkdir()
        (partial / "state").mkdir()
        (partial / "state" / "unbound.txt").write_text(
            "do not overwrite\n", encoding="utf-8")
        _expect_partial_preserve(exe, plugin_root, partial)
        assert (partial / "state" / "unbound.txt").read_text(
            encoding="utf-8") == "do not overwrite\n"

        abandoned = Path(temp) / "abandoned"
        abandoned.mkdir()
        abandoned_init = abandoned / ".state.init-previous"
        abandoned_init.mkdir()
        abandoned_file = abandoned_init / "partial.txt"
        abandoned_file.write_text(
            "preserve interrupted init\n", encoding="utf-8")
        _expect_partial_preserve(exe, plugin_root, abandoned)
        assert not (abandoned / "state").exists()
        assert abandoned_file.read_text(
            encoding="utf-8") == "preserve interrupted init\n"

    print("DESKTOP_PLUGIN_FROZEN_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

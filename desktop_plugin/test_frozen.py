import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from live_state_windows import MARKER_NAME, MARKER_VALUE, candidate_live_root


def _hash_tree(root):
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def _env(plugin_root, plugin_data, selftest=False):
    env = dict(os.environ)
    env["PLUGIN_ROOT"] = str(plugin_root)
    env["PLUGIN_DATA"] = str(plugin_data)
    if selftest:
        env["GENIE_PLUGIN_BUILD_SELFTEST"] = "1"
    else:
        env.pop("GENIE_PLUGIN_BUILD_SELFTEST", None)
    return env


def _expect_reject(exe, plugin_root, plugin_data, reason):
    proc = subprocess.run(
        [str(exe)], cwd=plugin_root, env=_env(plugin_root, plugin_data),
        input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout == b"", proc.stdout
    expected = f"GENIE_PLUGIN_REJECT:{reason}".encode("ascii")
    assert proc.stderr.rstrip(b"\r\n") == expected, proc.stderr


def _run_build_selftest(exe, plugin_root, plugin_data):
    proc = subprocess.run(
        [str(exe)], cwd=plugin_root,
        env=_env(plugin_root, plugin_data, selftest=True),
        input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stderr == b"", proc.stderr
    assert proc.stdout.rstrip(b"\r\n") == b"GENIE_PLUGIN_BUILD_SELFTEST_PASS", proc.stdout


async def _exercise(exe, plugin_root, plugin_data):
    from mcp import Client, StdioServerParameters

    params = StdioServerParameters(
        command=str(exe), args=[], cwd=str(plugin_root),
        env=_env(plugin_root, plugin_data))
    async with Client(params) as client:
        listed = await client.list_tools()
        names = [tool.name for tool in listed.tools]
        assert names == ["get_run_status", "get_task_result"], names
        status = await client.call_tool("get_run_status", {"run_name": "actual"})
        structured = status.structured_content
        assert type(structured) is dict and structured.get("status") == "PASS", structured
        confirmed = [
            item for item in structured.get("tasks", [])
            if type(item) is dict and type(item.get("fresh_sink")) is dict
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
        return task_id


def _write_marker(root, value=MARKER_VALUE):
    (root / MARKER_NAME).write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8", errors="strict")


def _copy_fixture(root):
    shutil.copytree(Path("host_return/trial"), root)
    _write_marker(root)


def _remove_root(root):
    if root.exists():
        shutil.rmtree(root)
    parent = root.parent
    if parent.exists():
        try:
            parent.rmdir()
        except OSError:
            pass


def main():
    plugin_root = Path(os.environ["GENIE_PLUGIN_ROOT"]).resolve(strict=True)
    exe = plugin_root / "bin" / "genie-mcp.exe"
    assert exe.is_file(), exe

    manifest = _load_json(plugin_root / "plugin.json")
    assert manifest == {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "genie-readonly",
        "version": "0.2.0",
        "description": "Read bounded local Genie run diagnostics and confirmed accepted task results from existing Genie-owned local state without granting new authority.",
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

    live = candidate_live_root()
    assert not live.exists(), f"refuse to touch pre-existing live root: {live}"
    assert not live.parent.exists(), f"refuse to touch pre-existing app root: {live.parent}"

    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        plugin_data = scratch / "plugin-data"
        plugin_data.mkdir()
        sentinel = plugin_data / "host-owned-sentinel.txt"
        sentinel.write_text("plugin data must remain outside Genie authority\n", encoding="utf-8")
        plugin_data_before = _hash_tree(plugin_data)

        # Missing live state must fail rather than seeding PLUGIN_DATA.
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_UNAVAILABLE")
        assert _hash_tree(plugin_data) == plugin_data_before

        live.parent.mkdir(parents=False)

        # A malformed marker is explicit invalid state, never setup permission.
        live.mkdir()
        _write_marker(live, {**MARKER_VALUE, "extra": "forbidden"})
        (live / "REGISTRY.json").write_text("{}\n", encoding="utf-8")
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_INVALID")
        shutil.rmtree(live)

        # Registry path traversal is rejected before a Genie store read.
        live.mkdir()
        _write_marker(live)
        malicious = {
            "actual": {
                "queue": "../outside.sqlite",
                "run_id": "genie-work-host-return-20261010",
                "owned_root": "work",
            }
        }
        (live / "REGISTRY.json").write_text(
            json.dumps(malicious) + "\n", encoding="utf-8")
        (live / "work").mkdir()
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_PATH")
        shutil.rmtree(live)

        # A Windows junction direct child must not escape the fixed state root.
        source = Path("host_return/trial")
        shutil.copytree(source, live)
        _write_marker(live)
        shutil.rmtree(live / "work")
        outside = scratch / "outside-work"
        shutil.copytree(source / "work", outside)
        junction = live / "work"
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        assert made.returncode == 0, (made.stdout, made.stderr)
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_PATH")
        os.rmdir(junction)
        shutil.rmtree(live)

        # Valid fixed-root state drives real frozen stdio calls without writes.
        _copy_fixture(live)
        live_before = _hash_tree(live)
        _run_build_selftest(exe, plugin_root, plugin_data)
        task_id = asyncio.run(_exercise(exe, plugin_root, plugin_data))
        middle = _hash_tree(live)
        assert middle == live_before
        repeated = asyncio.run(_exercise(exe, plugin_root, plugin_data))
        assert repeated == task_id
        assert _hash_tree(live) == live_before
        assert _hash_tree(plugin_data) == plugin_data_before

    _remove_root(live)
    print("DESKTOP_PLUGIN_LIVE_STATE_FROZEN_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

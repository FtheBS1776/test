import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from desktop_plugin.live_state_windows import MARKER_NAME, MARKER_VALUE, candidate_live_root
from standalone_app import owner, execution_bridge


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
        unknown = await client.call_tool("get_task_result", {
            "run_name": "actual", "task_id": "known-unavailable"})
        assert unknown.structured_content.get("status") == "UNKNOWN", unknown.structured_content
        assert "result_text" not in unknown.structured_content
        missing = await client.call_tool("get_task_result", {
            "run_name": "absent", "task_id": "known-unavailable"})
        assert missing.structured_content == {"status": "REJECT", "reason": "UNKNOWN_RUN"}
        missing_task = await client.call_tool("get_task_result", {
            "run_name": "actual", "task_id": "absent"})
        assert missing_task.structured_content == {"status": "REJECT", "reason": "UNKNOWN_TASK"}
        assert body["result_text"] == FIXTURE_RESULT
        return task_id


FIXTURE_RESULT = "NO MODEL CALL: fresh standalone-to-plugin composition fixture."


def _write_marker(root, raw=None):
    (root / MARKER_NAME).write_text(
        raw if raw is not None else json.dumps(MARKER_VALUE), encoding="utf-8")


def _create_and_drive_fixture():
    """One fresh owned run, deterministic hooks, one genuinely unserved task."""
    materials = {"completed-fixture": "NO MODEL CALL: primary input",
                 "known-unavailable": "NO MODEL CALL: unserved input"}
    costs = {role: {"max_micro_usd": 0, "quote_ref": "NO_MODEL_FIXTURE"}
             for role in ("author", "reviewer", "repair")}
    owner.create_first_run({
        "run_name": "actual",
        "policy": {"run_id": "live-package-fixture-20261018", "max_tasks": 2,
                   "max_model_calls": 1, "effect_scope": "owned-local-report-inbox",
                   "cost_policy": {"mode": "DISABLE_ALL", "limit_micro_usd": 0,
                                   "authorization_ref": None, "quotes": costs}},
        "plans": [{"task_id": task, "goal": "No-model source composition check",
                   "input_sha256": hashlib.sha256(text.encode()).hexdigest(), "max_attempts": 1}
                  for task, text in materials.items()]})
    seen = []

    def worker(action):
        assert action["task_materials"]["text"] == materials[action["token"]["task_id"]]
        seen.append(action)
        return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED",
                "agent": "no-model-package-fixture", "evidence": {"scope": "NO_MODEL_CALL"},
                "text": FIXTURE_RESULT}

    def reviewer(action):
        assert action["token"] == seen[0]["token"]
        return {"token": action["token"], "candidate_hash": action["candidate_sha256"],
                "decision": "ACCEPT", "reason": "DETERMINISTIC_FIXTURE_ONLY"}

    result = execution_bridge.drive("actual", worker, reviewer,
                                    costs=costs, materials=materials)
    assert (result["action"], result["reason"]) == ("STOP", "CALL_BUDGET_EXHAUSTED"), result
    assert result["counts"]["worker_hooks"] == result["counts"]["reviewer_hooks"] == 1
    assert len(seen) == 1
    status = owner.status("actual")
    assert status["queue_history"]["reserved_model_calls"] == 1
    assert status["queue_history"]["cost_admission"]["reserved_micro_usd"] == 0
    print("FRESH_OWNER_BRIDGE_DRIVER_STOP_FIXTURE_PASS_NO_MODEL")


def main():
    # The real binary has no root override. This harness is deliberately limited
    # to a disposable hosted Windows account, never a user's existing namespace.
    assert os.name == "nt" and os.environ.get("GITHUB_ACTIONS") == "true", "EPHEMERAL_WINDOWS_CI_ONLY"
    plugin_root = Path(os.environ["GENIE_PLUGIN_ROOT"]).resolve(strict=True)
    exe = plugin_root / "bin" / "genie-mcp.exe"
    assert exe.is_file(), exe
    viewer = Path("desktop_plugin/.venv/Scripts/pyi-archive_viewer.exe").resolve(strict=True)
    contents = subprocess.run([str(viewer), "-l", "-b", str(exe)], check=True,
                              capture_output=True, text=True, timeout=30).stdout
    normalized = contents.replace("\\", "/").lower()
    assert "seed_state" not in normalized and "build_seed" not in normalized
    assert ".sqlite" not in normalized, "BUNDLED_STORE_FORBIDDEN"
    print("FROZEN_ARCHIVE_NO_SEED_OR_SQLITE_PASS")
    manifest = _load_json(plugin_root / "plugin.json")
    assert manifest["name"] == "genie-readonly" and manifest["version"] == "0.2.0"
    compat = _load_json(plugin_root / ".codex-plugin" / "plugin.json")
    assert compat["name"] == manifest["name"] and compat["version"] == manifest["version"]
    assert compat["mcpServers"] == "./.mcp.json"
    portable = _load_json(plugin_root / "mcp.json")["mcpServers"]["genie-readonly"]
    legacy = _load_json(plugin_root / ".mcp.json")["mcpServers"]["genie-readonly"]
    assert portable == {"type": "stdio", "command": "./bin/genie-mcp.exe", "cwd": "${PLUGIN_ROOT}"}
    assert legacy == {"command": "./bin/genie-mcp.exe", "args": [], "cwd": "${PLUGIN_ROOT}"}

    live = candidate_live_root()
    assert not os.path.lexists(live.parent), "REFUSE_EXISTING_APP_NAMESPACE"
    with tempfile.TemporaryDirectory() as temporary:
        scratch = Path(temporary)
        plugin_data = scratch / "plugin-data"
        cached = plugin_data / "state"
        cached.mkdir(parents=True)
        (cached / ".genie-state.json").write_text('{"state_format":1,"seeded_from":"retired-cache"}')
        (cached / "REGISTRY.json").write_text("{}\n")
        plugin_data_before = _hash_tree(plugin_data)

        # A convincing former cache cannot authorize fallback when live state is absent.
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_UNAVAILABLE")
        assert _hash_tree(plugin_data) == plugin_data_before
        live.parent.mkdir()
        for marker in (json.dumps({**MARKER_VALUE, "extra": "invalid"}),
                       '{"format":"wrong","format":"GENIE_LOCAL_STATE_V1",'
                       '"registry":"REGISTRY.json","scope":"GENIE_OWNED_LOCAL_STATE"}'):
            live.mkdir()
            _write_marker(live, marker)
            (live / "REGISTRY.json").write_text("{}\n")
            before = _hash_tree(live)
            _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_INVALID")
            assert _hash_tree(live) == before
            shutil.rmtree(live)  # Explicit cleanup of this test's rejected disposable fixture.

        live.mkdir()
        _write_marker(live)
        (live / "REGISTRY.json").write_text(json.dumps({"actual": {
            "queue": "../outside.sqlite", "run_id": "path-test", "owned_root": "work"}}))
        (live / "work").mkdir()
        before = _hash_tree(live)
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_PATH")
        assert _hash_tree(live) == before
        shutil.rmtree(live)

        # A junction must reject before the deliberately invalid queue is opened.
        live.mkdir()
        _write_marker(live)
        (live / "queue.sqlite").write_bytes(b"not a queue")
        (live / "REGISTRY.json").write_text(json.dumps({"actual": {
            "queue": "queue.sqlite", "run_id": "junction-test", "owned_root": "work"}}))
        outside = scratch / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("preserve")
        junction = live / "work"
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        assert made.returncode == 0, (made.stdout, made.stderr)
        before = _hash_tree(live)
        _expect_reject(exe, plugin_root, plugin_data, "LIVE_STATE_PATH")
        assert _hash_tree(live) == before and (outside / "sentinel").read_text() == "preserve"
        os.rmdir(junction)
        shutil.rmtree(live)
        live.parent.rmdir()

        # The same namespace is now created by the actual standalone owner;
        # no historical store/seed is copied into it or into the executable.
        _create_and_drive_fixture()
        before = _hash_tree(live)
        _run_build_selftest(exe, plugin_root, plugin_data)
        task_id = asyncio.run(_exercise(exe, plugin_root, plugin_data))
        assert task_id == "completed-fixture"
        assert asyncio.run(_exercise(exe, plugin_root, plugin_data)) == task_id
        assert _hash_tree(live) == before
        assert _hash_tree(plugin_data) == plugin_data_before
        # Successful harness cleanup only. Failed state is left for CI inspection.
        shutil.rmtree(live)
        live.parent.rmdir()
    print("DESKTOP_PLUGIN_LIVE_STATE_FROZEN_PASS_NO_MODEL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import asyncio
import ast
import copy
import contextlib
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared_interfaces import mcp_controller as consumer_module
from shared_interfaces import mcp_controller_server as server_module


ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": False,
}
SCHEMA = {
    "type": "object",
    "properties": {"run_name": {"type": "string"}},
    "required": ["run_name"],
    "additionalProperties": False,
}
DESCRIPTOR = {
    "name": "advance_run",
    "title": "Advance one Genie run step",
    "description": "Advance exactly one bounded non-idempotent controller step.",
    "inputSchema": SCHEMA,
    "annotations": ANNOTATIONS,
}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(paths):
    rows = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        target = ROOT / path
        rows.append(f"{path.as_posix()}\t{target.stat().st_size}\t{_sha(target)}")
    return hashlib.sha256(("\n".join(rows) + "\n").encode()).hexdigest()


def _protected_paths():
    paths = set()
    for name in ("desktop_plugin", "plugin_mcp_consumer", "plugin_mcp_server"):
        paths.update(path.relative_to(ROOT) for path in (ROOT / name).rglob("*")
                     if path.is_file())
    paths.update(pathlib.Path(name) for name in (
        "shared_interfaces/cli.py",
        "shared_interfaces/status_tool.py",
        "shared_interfaces/function_adapter.py",
        "shared_interfaces/mcp_consumer.py",
        "shared_interfaces/mcp_server.py",
        "shared_interfaces/run_control.py",
        "active_runner/run_status.py",
        "active_runner/runner.py",
        "run_queue/run_policy.py",
        "host_adapter/journal.py",
        "worker_bridge/bridge.py",
        "worker_bridge/reused/report_sink.py",
        "worker_bridge/reused/stateful_subject.py",
        ".github/workflows/genie-desktop-plugin-nonclaim.yml",
        ".github/workflows/genie-mcp-server-nonclaim.yml",
    ))
    return paths


def _historical_sqlite_paths():
    return {
        path.relative_to(ROOT) for path in ROOT.rglob("*.sqlite")
        if path.relative_to(ROOT).parts[0] != "phase2a_controller"
    }


def _fixture(base, suffix="unit"):
    from shared_interfaces.status_tool import _load_core

    runner = _load_core().load_runner()
    queue = base / "queue.sqlite"
    owned = base / "owned root"
    owned.mkdir()
    run_id = "genie-phase2a-test-run-" + suffix
    task_id = "genie-phase2a-test-task-" + suffix
    policy = {
        "run_id": run_id,
        "max_tasks": 1,
        "max_model_calls": 1,
        "effect_scope": "owned-local-report-inbox",
    }
    plan = {
        "task_id": task_id,
        "goal": "Return one bound action without dispatching a model",
        "input_sha256": hashlib.sha256(("input-" + suffix).encode()).hexdigest(),
        "max_attempts": 1,
    }
    runner.q.initialize(queue, policy)
    runner.q.enqueue(queue, plan)
    registry = {
        "phase2a-synthetic": {
            "queue": str(queue),
            "run_id": run_id,
            "owned_root": str(owned),
        }
    }
    return types.SimpleNamespace(
        runner=runner, queue=queue, owned=owned, policy=policy, plan=plan,
        registry=registry)


class FakeConsumer:
    def __init__(self, result=None, descriptors=None):
        self.result = result if result is not None else {
            "action": "STOP", "reason": "fixed", "allow_new_invocation": False,
        }
        self.descriptors = descriptors if descriptors is not None else [DESCRIPTOR]
        self.calls = []

    def tools(self):
        return copy.deepcopy(self.descriptors)

    def call(self, name, arguments):
        self.calls.append((name, copy.deepcopy(arguments)))
        return {"structuredContent": copy.deepcopy(self.result)}


class Tests(unittest.TestCase):
    def test_recorded_pilot_state_matches_bound_action(self):
        trial = ROOT / "phase2a_controller" / "trial"
        policy = json.loads((trial / "POLICY.json").read_text(encoding="utf-8"))
        plan = json.loads((trial / "PLAN.json").read_text(encoding="utf-8"))
        result = json.loads((trial / "CALL_RESULT_REDACTED.json").read_text(
            encoding="utf-8"))
        pre = json.loads((trial / "PRE_CALL_STATE.json").read_text(encoding="utf-8"))
        post = json.loads((trial / "POST_CALL_STATE_REDACTED.json").read_text(
            encoding="utf-8"))
        self.assertEqual(_sha(trial / "INPUT.md"), plan["input_sha256"])
        self.assertNotEqual(policy["run_id"], plan["task_id"])
        self.assertEqual((policy["max_tasks"], policy["max_model_calls"],
                          plan["max_attempts"]), (1, 1, 1))
        self.assertEqual(pre["databases"]["queue.sqlite"]["reservations"], [])
        self.assertEqual(
            pre["databases"]["queue.sqlite"]["entries"][0]["state"], "READY")
        self.assertEqual(result["tool_names"], ["advance_run"])
        self.assertEqual(result["annotations"], ANNOTATIONS)
        self.assertEqual((result["call_count"], result["retry_count"]), (1, 0))
        self.assertFalse(result["is_error"])
        action = result["structured_content"]
        self.assertEqual(action["action"], "INVOKE_WORKER")
        self.assertEqual(set(action["request_field_names"]), {
            "attempt", "feedback", "goal", "input_sha256", "task_id"})
        self.assertEqual(set(action["token_field_names"]), {
            "attempt", "call_id", "input_sha256", "run_id", "slot_id",
            "task_id"})
        commitments = post["binding_commitments"]
        self.assertEqual(action["request_sha256"], commitments["request_sha256"])
        self.assertEqual(action["token_sha256"], commitments["token_sha256"])
        state = post["post_call_state"]
        self.assertEqual(state["queue_state"], "RUNNING")
        self.assertEqual(state["entry_state"], "ACTIVE")
        self.assertEqual(state["reservation_count"], 1)
        self.assertEqual(state["task_state"], "WAITING_WORKER")
        self.assertEqual(state["host_call_count"], 1)
        self.assertEqual(state["host_observation_count"], 0)
        self.assertEqual(state["report_count"], 0)
        self.assertEqual(state["application_count"], 0)
        self.assertEqual((state["agent"], state["candidate"],
                          state["candidate_hash"], state["review"]),
                         (None, None, None, None))

        # Raw stores remain charged and preserved on the pilot host but are
        # intentionally gitignored. Fresh checkouts verify the bounded JSON
        # snapshots; the originating host additionally verifies live stores.
        raw_result_path = trial / "CALL_RESULT.json"
        queue = trial / "queue.sqlite"
        if raw_result_path.exists():
            raw_result = json.loads(raw_result_path.read_text(encoding="utf-8"))
            raw_action = raw_result["structured_content"]
            canonical = lambda value: json.dumps(
                value, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True).encode()
            self.assertEqual(
                hashlib.sha256(canonical(raw_action["request"])).hexdigest(),
                commitments["request_sha256"])
            self.assertEqual(
                hashlib.sha256(canonical(raw_action["token"])).hexdigest(),
                commitments["token_sha256"])
            self.assertEqual(
                hashlib.sha256(raw_action["token"]["slot_id"].encode()).hexdigest(),
                commitments["slot_id_sha256"])
            self.assertEqual(
                hashlib.sha256(raw_action["token"]["call_id"].encode()).hexdigest(),
                commitments["call_id_sha256"])
            self.assertEqual(raw_action["token"]["run_id"], policy["run_id"])
            self.assertEqual(raw_action["token"]["task_id"], plan["task_id"])
            self.assertEqual(raw_action["request"]["task_id"], plan["task_id"])
            self.assertEqual(
                raw_action["token"]["input_sha256"], plan["input_sha256"])
            self.assertEqual(
                raw_action["request"]["input_sha256"], plan["input_sha256"])
            from shared_interfaces.status_tool import _load_core
            runner = _load_core().load_runner()
            expected_slot = runner.b.digest(runner.b.canon({
                "kind": "queue-call-v1", "request": raw_action["request"]}))
            expected_call = runner.b.digest(runner.b.canon({
                "kind": "host-invoke-v1", "request": raw_action["request"]}))
            self.assertEqual(raw_action["token"]["slot_id"], expected_slot)
            self.assertEqual(raw_action["token"]["call_id"], expected_call)

        if queue.exists() and raw_result_path.exists():
            with contextlib.closing(sqlite3.connect(
                    queue.resolve().as_uri() + "?mode=ro", uri=True)) as database:
                self.assertEqual(database.execute(
                    "select state from entries").fetchone()[0], "ACTIVE")
                self.assertEqual(database.execute(
                    "select count(*) from reservations").fetchone()[0], 1)
                reservation = json.loads(database.execute(
                    "select request from reservations").fetchone()[0])
                self.assertEqual(reservation, raw_action["request"])
            _, ledger, sink = runner.paths(
                trial / "work", policy["run_id"], plan["task_id"])
            with contextlib.closing(sqlite3.connect(
                    ledger.resolve().as_uri() + "?mode=ro", uri=True)) as database:
                self.assertEqual(database.execute(
                    "select state from task").fetchone()[0], "WAITING_WORKER")
                self.assertEqual(database.execute(
                    "select count(*) from host_calls").fetchone()[0], 1)
                self.assertEqual(database.execute(
                    "select count(*) from host_observations").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select agent,candidate,candidate_hash,review from attempts"
                ).fetchone(), (None, None, None, None))
            with contextlib.closing(sqlite3.connect(
                    sink.resolve().as_uri() + "?mode=ro", uri=True)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reports").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select count(*) from applications").fetchone()[0], 0)

        source = (ROOT / "phase2a_controller" / "run_pilot_once.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        call_tool_sites = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "call_tool"
        ]
        self.assertEqual(len(call_tool_sites), 1)
        self.assertNotIn("while ", source)

    def test_exact_single_controller_tool_and_annotations(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "metadata")
            consumer = consumer_module.GenieMcpControllerConsumer(fixture.registry)
            tools = consumer.tools()
            self.assertEqual([tool["name"] for tool in tools], ["advance_run"])
            self.assertEqual(tools[0]["inputSchema"], SCHEMA)
            self.assertEqual(tools[0]["annotations"], ANNOTATIONS)
            self.assertNotIn(str(fixture.queue), json.dumps(tools))
            tools[0]["name"] = "mutated"
            self.assertEqual(consumer.tools()[0]["name"], "advance_run")

    def test_controller_source_and_sdk_pins_fail_closed(self):
        with patch.object(consumer_module.Path, "read_bytes", return_value=b"corrupt"):
            with self.assertRaisesRegex(ValueError, "RUN_CONTROL_SOURCE_BINDING"):
                consumer_module._load_controller_module()
        with patch.object(server_module.Path, "read_bytes", return_value=b"corrupt"):
            with self.assertRaisesRegex(ValueError, "MCP_CONTROLLER_SOURCE_BINDING"):
                server_module._load_consumer_module()
        with patch.object(server_module.metadata, "version", return_value="0"):
            with self.assertRaisesRegex(ValueError, "MCP_SDK_VERSION_BINDING"):
                server_module.build_server_from_consumer(FakeConsumer())

    def test_bad_tool_type_alias_and_input_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "bad-input")
            consumer = consumer_module.GenieMcpControllerConsumer(fixture.registry)
            before_queue = _sha(fixture.queue)
            before_root = list(fixture.owned.iterdir())
            for name in ("apply_run_event", "get_run_status", "review", "", None):
                result = consumer.call(name, {"run_name": "phase2a-synthetic"})
                self.assertEqual(result["structuredContent"]["status"], "REJECT")
            for arguments in (
                None, [], True, {}, {"run_name": 1},
                {"run_name": "phase2a-synthetic", "queue": "attacker"},
                {"run_name": "phase2a-synthetic", "retry": True},
                {"run_name": "phase2a-synthetic", "reset": True},
            ):
                result = consumer.call("advance_run", arguments)
                self.assertEqual(result["structuredContent"]["status"], "REJECT")
            for alias in (
                "absent", "", " phase2a-synthetic", "PHASE2A-SYNTHETIC",
                "../phase2a-synthetic", "C:\\state\\queue.sqlite", "bad\x00alias",
            ):
                result = consumer.call("advance_run", {"run_name": alias})
                self.assertEqual(result["structuredContent"]["status"], "REJECT")
            self.assertEqual(_sha(fixture.queue), before_queue)
            self.assertEqual(list(fixture.owned.iterdir()), before_root)

    def test_invalid_name_never_delegates(self):
        calls = []

        class Spy:
            def call(self, name, arguments):
                calls.append((name, arguments))
                raise AssertionError("must not delegate")

        consumer = consumer_module.GenieMcpControllerConsumer.__new__(
            consumer_module.GenieMcpControllerConsumer)
        consumer._controller = Spy()
        result = consumer.call("apply_run_event", {"run_name": "x"})
        self.assertEqual(result["structuredContent"]["status"], "REJECT")
        self.assertEqual(calls, [])

    def test_unknown_is_canonical_and_never_retried(self):
        expected = {
            "action": "UNKNOWN",
            "reason": "MCP_CONTROLLER_OUTCOME_UNKNOWN",
            "preserve": True,
            "allow_new_invocation": False,
        }
        for returned in (
            {"action": "UNKNOWN"},
            {"action": "UNKNOWN", "preserve": False,
             "allow_new_invocation": False},
            {"action": "IMAGINARY"},
            None,
        ):
            calls = []

            class Spy:
                def call(self, name, arguments):
                    calls.append((name, arguments))
                    return returned

            consumer = consumer_module.GenieMcpControllerConsumer.__new__(
                consumer_module.GenieMcpControllerConsumer)
            consumer._controller = Spy()
            result = consumer.call("advance_run", {"run_name": "x"})
            self.assertEqual(result["structuredContent"], expected)
            self.assertEqual(len(calls), 1)

        calls = []

        class Raises:
            def call(self, name, arguments):
                calls.append((name, arguments))
                raise RuntimeError("secret C:\\private\\state")

        consumer = consumer_module.GenieMcpControllerConsumer.__new__(
            consumer_module.GenieMcpControllerConsumer)
        consumer._controller = Raises()
        result = consumer.call("advance_run", {"run_name": "x"})
        self.assertEqual(result["structuredContent"], expected)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("private", json.dumps(result))

    def test_commit_then_exception_preserves_charge_without_refund(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "post-commit")
            real = consumer_module.GenieMcpControllerConsumer(fixture.registry)
            wrapped = real._controller
            calls = []

            class CommitThenRaise:
                def call(self, name, arguments):
                    calls.append((name, arguments))
                    wrapped.call(name, arguments)
                    raise RuntimeError("lost reply")

            real._controller = CommitThenRaise()
            result = real.call("advance_run", {"run_name": "phase2a-synthetic"})
            self.assertEqual(result["structuredContent"]["action"], "UNKNOWN")
            self.assertTrue(result["structuredContent"]["preserve"])
            self.assertFalse(result["structuredContent"]["allow_new_invocation"])
            self.assertEqual(len(calls), 1)
            with contextlib.closing(sqlite3.connect(fixture.queue)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reservations").fetchone()[0], 1)
                self.assertEqual(database.execute(
                    "select state from entries").fetchone()[0], "ACTIVE")
            _, ledger, sink = fixture.runner.paths(
                fixture.owned, fixture.policy["run_id"], fixture.plan["task_id"])
            with contextlib.closing(sqlite3.connect(ledger)) as database:
                self.assertEqual(database.execute(
                    "select state from task").fetchone()[0], "WAITING_WORKER")
                self.assertEqual(database.execute(
                    "select count(*) from host_calls").fetchone()[0], 1)
                self.assertEqual(database.execute(
                    "select count(*) from host_observations").fetchone()[0], 0)
            with contextlib.closing(sqlite3.connect(sink)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reports").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select count(*) from applications").fetchone()[0], 0)

    def test_server_metadata_one_delegation_and_safe_text(self):
        from mcp import Client

        payload = {
            "action": "INVOKE_WORKER",
            "token": {"call_id": "PRIVATE_TOKEN"},
            "request": {"goal": "PRIVATE_GOAL"},
        }
        consumer = FakeConsumer(payload)
        server = server_module.build_server_from_consumer(consumer)

        async def run():
            async with Client(server) as client:
                listed = await client.list_tools()
                self.assertEqual([tool.name for tool in listed.tools], ["advance_run"])
                tool = listed.tools[0]
                self.assertFalse(tool.annotations.read_only_hint)
                self.assertTrue(tool.annotations.destructive_hint)
                self.assertFalse(tool.annotations.idempotent_hint)
                self.assertFalse(tool.annotations.open_world_hint)
                result = await client.call_tool(
                    "advance_run", {"run_name": "phase2a-synthetic"})
                self.assertEqual(result.structured_content, payload)
                self.assertFalse(result.is_error)
                self.assertIn("no worker dispatched", result.content[0].text)
                self.assertNotIn("PRIVATE_TOKEN", result.content[0].text)
                self.assertNotIn("PRIVATE_GOAL", result.content[0].text)

        asyncio.run(run())
        self.assertEqual(consumer.calls, [
            ("advance_run", {"run_name": "phase2a-synthetic"})])

    def test_server_rejects_metadata_mutants(self):
        for mutate in ("extra", "readonly", "idempotent", "nondestructive"):
            tools = copy.deepcopy([DESCRIPTOR])
            if mutate == "extra":
                tools.append(copy.deepcopy(DESCRIPTOR))
            elif mutate == "readonly":
                tools[0]["annotations"]["readOnlyHint"] = True
            elif mutate == "idempotent":
                tools[0]["annotations"]["idempotentHint"] = True
            else:
                tools[0]["annotations"]["destructiveHint"] = False
            with self.assertRaisesRegex(ValueError, "INVALID_MCP_CONTROLLER_METADATA"):
                server_module.build_server_from_consumer(FakeConsumer(descriptors=tools))

    def test_server_malformed_projection_is_unknown_without_retry(self):
        from mcp import Client

        class Bad(FakeConsumer):
            def call(self, name, arguments):
                self.calls.append((name, copy.deepcopy(arguments)))
                return {"wrong": {}}

        consumer = Bad()
        server = server_module.build_server_from_consumer(consumer)

        async def run():
            async with Client(server) as client:
                result = await client.call_tool(
                    "advance_run", {"run_name": "phase2a-synthetic"})
                self.assertEqual(result.structured_content, {
                    "action": "UNKNOWN",
                    "reason": "MCP_CONTROLLER_SERVER_OUTCOME_UNKNOWN",
                    "preserve": True,
                    "allow_new_invocation": False,
                })
                self.assertFalse(result.is_error)
                self.assertIn("do not retry", result.content[0].text)

        asyncio.run(run())
        self.assertEqual(len(consumer.calls), 1)

    def test_real_windows_stdio_one_step_no_dispatch_or_callback(self):
        from mcp import Client, StdioServerParameters

        with tempfile.TemporaryDirectory(prefix="genie phase2a ") as temp:
            base = pathlib.Path(temp)
            fixture = _fixture(base, "stdio")
            registry = base / "controller registry.json"
            registry.write_text(json.dumps({
                "phase2a-synthetic": {
                    "queue": str(fixture.queue),
                    "run_id": fixture.policy["run_id"],
                    "owned_root": str(fixture.owned),
                }
            }), encoding="utf-8")
            params = StdioServerParameters(
                command=sys.executable,
                args=["-B", "-m", "shared_interfaces.mcp_controller_server",
                      "--registry", str(registry)],
                cwd=str(ROOT),
            )

            async def run():
                async with Client(params) as client:
                    listed = await client.list_tools()
                    self.assertEqual([tool.name for tool in listed.tools],
                                     ["advance_run"])
                    return await client.call_tool(
                        "advance_run", {"run_name": "phase2a-synthetic"})

            result = asyncio.run(run())
            self.assertFalse(result.is_error)
            action = result.structured_content
            self.assertEqual(action["action"], "INVOKE_WORKER")
            self.assertEqual(set(action), {"action", "token", "request"})
            self.assertEqual(set(action["token"]), {
                "run_id", "task_id", "input_sha256", "attempt", "slot_id", "call_id"})
            self.assertEqual(set(action["request"]), {
                "task_id", "input_sha256", "attempt", "goal", "feedback"})
            self.assertEqual(action["token"]["run_id"], fixture.policy["run_id"])
            self.assertEqual(action["token"]["task_id"], fixture.plan["task_id"])
            self.assertEqual(action["token"]["input_sha256"], fixture.plan["input_sha256"])
            self.assertEqual(action["token"]["attempt"], 1)
            self.assertEqual(action["request"]["feedback"], None)
            slot = fixture.runner.b.digest(fixture.runner.b.canon({
                "kind": "queue-call-v1", "request": action["request"]}))
            call = fixture.runner.b.digest(fixture.runner.b.canon({
                "kind": "host-invoke-v1", "request": action["request"]}))
            self.assertEqual(action["token"]["slot_id"], slot)
            self.assertEqual(action["token"]["call_id"], call)

            with contextlib.closing(sqlite3.connect(fixture.queue)) as database:
                self.assertEqual(database.execute(
                    "select state from entries").fetchone()[0], "ACTIVE")
                self.assertEqual(database.execute(
                    "select count(*) from reservations").fetchone()[0], 1)
                saved = json.loads(database.execute(
                    "select request from reservations").fetchone()[0])
                self.assertEqual(saved, action["request"])
            _, ledger, sink = fixture.runner.paths(
                fixture.owned, fixture.policy["run_id"], fixture.plan["task_id"])
            with contextlib.closing(sqlite3.connect(ledger)) as database:
                self.assertEqual(database.execute(
                    "select state from task").fetchone()[0], "WAITING_WORKER")
                self.assertEqual(database.execute(
                    "select count(*) from host_calls").fetchone()[0], 1)
                self.assertEqual(database.execute(
                    "select count(*) from host_observations").fetchone()[0], 0)
                attempt = database.execute(
                    "select agent,candidate,candidate_hash,review from attempts").fetchone()
                self.assertEqual(attempt, (None, None, None, None))
            with contextlib.closing(sqlite3.connect(sink)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reports").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select count(*) from applications").fetchone()[0], 0)

    def test_stdio_only_rejects_http_options(self):
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "shared_interfaces.mcp_controller_server",
             "--registry", "unused.json", "--host", "127.0.0.1"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unrecognized arguments", completed.stderr)

    def test_static_boundary_has_no_phase2b_or_network_surface(self):
        consumer = (ROOT / "shared_interfaces" / "mcp_controller.py").read_text(
            encoding="utf-8")
        server = (ROOT / "shared_interfaces" / "mcp_controller_server.py").read_text(
            encoding="utf-8")
        executable = consumer + "\n" + server
        for forbidden in (
            "apply_run_event(", ".callback(", "serve_run(",
            "session_driver", "streamable_http_app(", "uvicorn.run(",
            "subprocess.Popen(", "socket.socket(",
        ):
            self.assertNotIn(forbidden, executable)

    def test_readonly_package_and_historical_state_unchanged(self):
        protected = _protected_paths()
        self.assertEqual(len(protected), 54)
        self.assertEqual(
            _aggregate(protected),
            "ba2cd2b1fb6b1ed6c84d59b7255c1435d91a9afb68fa76c16fc8bc10bef18170")
        sentinels = {
            "shared_interfaces/status_tool.py":
                "37629d2ec2d8bdb88da66247c7093225e387b4d79220fb42b214cc01c8ef2619",
            "shared_interfaces/function_adapter.py":
                "9627bc0967e4b6115f405671be8a2c60498101e276d96062d55572537f2769d2",
            "shared_interfaces/mcp_consumer.py":
                "21f3fc657abb16c9ba7c9189f266cbdfeaec1dbf0ae2ca6d051caee1565ddd5d",
            "shared_interfaces/mcp_server.py":
                "67e02e26bb7224268c5cd69c07e12e7d97795b59d29b2ea3fac62f9c3dd6f573",
            "shared_interfaces/cli.py":
                "c0a35e699cc4ad2fd2e176fd8ab951fbab7f57f56c783230925d078b38ff8af4",
            "shared_interfaces/run_control.py":
                "ecc71b088e5a7e3c0bde33b53a7e850dd769daee5b301f2f116edf956599f2d4",
            "desktop_plugin/entry.py":
                "4235191453f3ca5ee168f06b58f3366ae4178134246e3304125ba17767f878d5",
            "desktop_plugin/genie_mcp.spec":
                "82efea06f159537a7de235712d185709437488dc3069071d4ba1a647c5d626b3",
        }
        for name, expected in sentinels.items():
            self.assertEqual(_sha(ROOT / name), expected)
        historical = _historical_sqlite_paths()
        self.assertEqual(len(historical), 27)
        self.assertEqual(
            _aggregate(historical),
            "56a1f0dcea069ba31a0a09f573fd927eaee4e25900bb6f1554564ffabbe33837")


if __name__ == "__main__":
    unittest.main(verbosity=2)

import asyncio
import contextlib
import copy
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

from shared_interfaces import mcp_events as consumer_module
from shared_interfaces import mcp_events_server as server_module


ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": False,
}


def _object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _descriptor():
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
        _object_schema({"agent": dict(identity),
                        "text": {"type": "string", "minLength": 1}}),
        _object_schema({"candidate_hash": dict(digest),
                        "decision": {"type": "string", "enum": ["ACCEPT", "REPAIR"]},
                        "reason": dict(identity)}),
    ]
    return {
        "name": "apply_run_event",
        "title": "Apply one bound Genie run event",
        "description": "Record one bound event without dispatch or progression.",
        "inputSchema": _object_schema({
            "run_name": {"type": "string"},
            "operation": {"type": "string", "enum": ["observe", "submit", "review"]},
            "supplied": supplied,
            "payload": {"oneOf": payloads},
        }),
        "annotations": dict(ANNOTATIONS),
    }


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(paths):
    rows = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        target = ROOT / path
        rows.append(f"{path.as_posix()}\t{target.stat().st_size}\t{_sha(target)}")
    return hashlib.sha256(("\n".join(rows) + "\n").encode()).hexdigest()


def _historical_sqlite_paths():
    return {
        path.relative_to(ROOT) for path in ROOT.rglob("*.sqlite")
        if path.relative_to(ROOT).parts[0] not in {
            "phase2a_controller", "phase2b_events"}
    }


def _fixture(base, suffix="unit"):
    from shared_interfaces.status_tool import _load_core
    from shared_interfaces.run_control import GenieRunController

    runner = _load_core().load_runner()
    queue = base / "queue.sqlite"
    owned = base / "owned root"
    owned.mkdir()
    run_id = "genie-phase2b1-test-run-" + suffix
    task_id = "genie-phase2b1-test-task-" + suffix
    policy = {
        "run_id": run_id,
        "max_tasks": 1,
        "max_model_calls": 1,
        "effect_scope": "owned-local-report-inbox",
    }
    plan = {
        "task_id": task_id,
        "goal": "Deterministic NO_MODEL_CALL event-interface fixture",
        "input_sha256": hashlib.sha256(("phase2b1-input-" + suffix).encode()).hexdigest(),
        "max_attempts": 1,
    }
    runner.q.initialize(queue, policy)
    runner.q.enqueue(queue, plan)
    registry = {
        "phase2b1-synthetic": {
            "queue": str(queue),
            "run_id": run_id,
            "owned_root": str(owned),
        }
    }
    action = GenieRunController(registry).call(
        "advance_run", {"run_name": "phase2b1-synthetic"})
    if action.get("action") != "INVOKE_WORKER":
        raise ValueError("FIXTURE_DISPATCH")
    return types.SimpleNamespace(
        runner=runner, queue=queue, owned=owned, policy=policy, plan=plan,
        registry=registry, action=action, token=action["token"])


def _observe(fixture):
    return {
        "run_name": "phase2b1-synthetic",
        "operation": "observe",
        "supplied": copy.deepcopy(fixture.token),
        "payload": {
            "outcome": "OBSERVED_ACCEPTED",
            "agent": "phase2b1-fixture-worker-no-model",
            "evidence": {
                "fixture": "NO_MODEL_CALL",
                "model_invoked": False,
                "independent_proof": False,
            },
        },
    }


class FakeConsumer:
    def __init__(self, result=None, descriptors=None):
        self.result = result if result is not None else {
            "status": "APPLIED", "operation": "observe", "result": "RECORDED"}
        self.descriptors = descriptors if descriptors is not None else [_descriptor()]
        self.calls = []

    def tools(self):
        return copy.deepcopy(self.descriptors)

    def call(self, name, arguments):
        self.calls.append((name, copy.deepcopy(arguments)))
        return {"structuredContent": copy.deepcopy(self.result)}


class Tests(unittest.TestCase):
    def test_exact_single_event_tool_and_defensive_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "metadata")
            consumer = consumer_module.GenieMcpEventsConsumer(fixture.registry)
            tools = consumer.tools()
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0]["name"], "apply_run_event")
            self.assertEqual(tools[0]["title"], "Apply one bound Genie run event")
            self.assertEqual(tools[0]["annotations"], ANNOTATIONS)
            self.assertFalse(tools[0]["inputSchema"]["additionalProperties"])
            self.assertEqual(tools[0]["inputSchema"]["required"], [
                "run_name", "operation", "supplied", "payload"])
            tools[0]["name"] = "advance_run"
            self.assertEqual(consumer.tools()[0]["name"], "apply_run_event")

    def test_bad_tool_arguments_alias_and_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "bad-input")
            consumer = consumer_module.GenieMcpEventsConsumer(fixture.registry)
            self.assertEqual(consumer.call("advance_run", {})["structuredContent"], {
                "status": "REJECT", "reason": "INVALID_TOOL_CALL"})
            self.assertEqual(consumer.call("apply_run_event", [])["structuredContent"], {
                "status": "REJECT", "reason": "INVALID_TOOL_CALL"})
            args = _observe(fixture)
            args["run_name"] = "absent"
            self.assertEqual(consumer.call(
                "apply_run_event", args)["structuredContent"]["status"], "REJECT")
            cyclic = _observe(fixture)
            cyclic["payload"]["evidence"]["cycle"] = cyclic
            self.assertEqual(consumer.call(
                "apply_run_event", cyclic)["structuredContent"], {
                    "status": "REJECT", "reason": "INVALID_ARGUMENTS"})

    def test_one_detached_delegation_only(self):
        consumer = object.__new__(consumer_module.GenieMcpEventsConsumer)
        calls = []

        class Events:
            def call(self, name, arguments):
                calls.append((name, copy.deepcopy(arguments)))
                arguments["payload"]["evidence"]["fixture"] = "changed"
                return {"status": "APPLIED", "operation": "observe", "result": "RECORDED"}

        consumer._events = Events()
        supplied = {
            "operation": "observe",
            "payload": {"evidence": {"fixture": "original"}},
        }
        result = consumer.call("apply_run_event", supplied)
        self.assertEqual(result["structuredContent"]["status"], "APPLIED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["payload"]["evidence"]["fixture"], "original")
        self.assertEqual(supplied["payload"]["evidence"]["fixture"], "original")

    def test_projection_normalizes_malformed_or_weakened_unknown(self):
        invalid = [
            None,
            {},
            {"status": "UNKNOWN"},
            {"status": "UNKNOWN", "reason": "weak", "preserve": False,
             "allow_new_invocation": False},
            {"status": "APPLIED", "operation": "observe", "result": "ACCEPT"},
            {"status": "APPLIED", "operation": "advance", "result": "RECORDED"},
        ]
        for payload in invalid:
            consumer = object.__new__(consumer_module.GenieMcpEventsConsumer)

            class Events:
                def call(self, _name, _arguments):
                    return copy.deepcopy(payload)

            consumer._events = Events()
            result = consumer.call("apply_run_event", {})["structuredContent"]
            self.assertEqual(result, {
                "status": "UNKNOWN",
                "reason": "MCP_EVENTS_OUTCOME_UNKNOWN",
                "preserve": True,
                "allow_new_invocation": False,
            })

    def test_result_matches_requested_operation_and_review_decision(self):
        cases = [
            (
                {"operation": "observe", "payload": {}},
                {"status": "APPLIED", "operation": "submit",
                 "result": "SUBMITTED"},
            ),
            (
                {"operation": "review", "payload": {"decision": "REPAIR"}},
                {"status": "APPLIED", "operation": "review",
                 "result": "ACCEPT"},
            ),
        ]
        for arguments, payload in cases:
            consumer = object.__new__(consumer_module.GenieMcpEventsConsumer)

            class Events:
                def call(self, _name, _arguments):
                    return copy.deepcopy(payload)

            consumer._events = Events()
            result = consumer.call(
                "apply_run_event", arguments)["structuredContent"]
            self.assertEqual(result, {
                "status": "UNKNOWN",
                "reason": "MCP_EVENTS_OUTCOME_UNKNOWN",
                "preserve": True,
                "allow_new_invocation": False,
            })

    def test_delegate_mutation_cannot_rebind_expected_result(self):
        cases = [
            (
                {"operation": "observe", "payload": {}},
                lambda arguments: arguments.update(operation="submit"),
                {"status": "APPLIED", "operation": "submit",
                 "result": "SUBMITTED"},
            ),
            (
                {"operation": "review", "payload": {"decision": "REPAIR"}},
                lambda arguments: arguments["payload"].update(decision="ACCEPT"),
                {"status": "APPLIED", "operation": "review",
                 "result": "ACCEPT"},
            ),
        ]
        for arguments, mutate, payload in cases:
            consumer = object.__new__(consumer_module.GenieMcpEventsConsumer)

            class Events:
                def call(self, _name, delegated):
                    mutate(delegated)
                    return copy.deepcopy(payload)

            consumer._events = Events()
            result = consumer.call(
                "apply_run_event", arguments)["structuredContent"]
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertTrue(result["preserve"])
            self.assertFalse(result["allow_new_invocation"])

    def test_commit_then_exception_preserves_observation_without_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "post-commit")
            consumer = consumer_module.GenieMcpEventsConsumer(fixture.registry)
            wrapped = consumer._events
            calls = []

            class CommitThenRaise:
                def call(self, name, arguments):
                    calls.append((name, copy.deepcopy(arguments)))
                    wrapped.call(name, arguments)
                    raise RuntimeError("lost callback response")

            consumer._events = CommitThenRaise()
            result = consumer.call(
                "apply_run_event", _observe(fixture))["structuredContent"]
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertTrue(result["preserve"])
            self.assertFalse(result["allow_new_invocation"])
            self.assertEqual(len(calls), 1)
            _, ledger, sink = fixture.runner.paths(
                fixture.owned, fixture.policy["run_id"], fixture.plan["task_id"])
            with contextlib.closing(sqlite3.connect(ledger)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from host_observations").fetchone()[0], 1)
                self.assertEqual(database.execute(
                    "select state from task").fetchone()[0], "WAITING_WORKER")
                self.assertEqual(database.execute(
                    "select count(*) from host_calls").fetchone()[0], 1)
                attempt = database.execute(
                    "select agent,candidate,candidate_hash,review from attempts").fetchone()
                self.assertEqual(attempt, (
                    "phase2b1-fixture-worker-no-model", None, None, None))
            with contextlib.closing(sqlite3.connect(sink)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reports").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select count(*) from applications").fetchone()[0], 0)
            with contextlib.closing(sqlite3.connect(fixture.queue)) as database:
                self.assertEqual(database.execute(
                    "select state from entries").fetchone()[0], "ACTIVE")
                self.assertEqual(database.execute(
                    "select count(*) from reservations").fetchone()[0], 1)

    def test_crossed_token_is_unknown_without_effect(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = _fixture(pathlib.Path(temp), "crossed-token")
            consumer = consumer_module.GenieMcpEventsConsumer(fixture.registry)
            arguments = _observe(fixture)
            arguments["supplied"]["call_id"] = "c" * 64
            result = consumer.call(
                "apply_run_event", arguments)["structuredContent"]
            self.assertEqual(result, {
                "status": "UNKNOWN",
                "reason": "CALLBACK_OUTCOME_UNKNOWN",
                "preserve": True,
                "allow_new_invocation": False,
            })
            _, ledger, sink = fixture.runner.paths(
                fixture.owned, fixture.policy["run_id"], fixture.plan["task_id"])
            with contextlib.closing(sqlite3.connect(ledger)) as database:
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

    def test_source_pin_failure_prevents_construction(self):
        with patch.object(consumer_module.Path, "read_bytes", return_value=b"bad"):
            with self.assertRaisesRegex(
                    ValueError, "RUN_EVENTS_SOURCE_BINDING_OR_REGISTRY"):
                consumer_module.GenieMcpEventsConsumer({})

    def test_server_consumer_source_pin_failure(self):
        with patch.object(server_module.Path, "read_bytes", return_value=b"bad"):
            with self.assertRaisesRegex(ValueError, "MCP_EVENTS_SOURCE_BINDING"):
                server_module._load_consumer_module()

    def test_sdk_closure_mismatch_fails_closed(self):
        with patch.object(server_module.metadata, "version", return_value="wrong"):
            with self.assertRaisesRegex(ValueError, "MCP_SDK_VERSION_BINDING"):
                server_module._require_sdk()

    def test_server_one_tool_one_delegation_and_safe_text(self):
        from mcp import Client

        consumer = FakeConsumer()
        server = server_module.build_server_from_consumer(consumer)

        async def run():
            async with Client(server) as client:
                listed = await client.list_tools()
                self.assertEqual([tool.name for tool in listed.tools],
                                 ["apply_run_event"])
                annotations = listed.tools[0].annotations
                self.assertFalse(annotations.read_only_hint)
                self.assertTrue(annotations.destructive_hint)
                self.assertFalse(annotations.idempotent_hint)
                self.assertFalse(annotations.open_world_hint)
                arguments = {
                    "run_name": "PRIVATE_ALIAS",
                    "operation": "observe",
                    "supplied": {"call_id": "PRIVATE_TOKEN"},
                    "payload": {"evidence": {"secret": "PRIVATE_EVIDENCE"}},
                }
                result = await client.call_tool("apply_run_event", arguments)
                self.assertEqual(result.structured_content, consumer.result)
                self.assertFalse(result.is_error)
                self.assertIn("callback acknowledgement only", result.content[0].text)
                for private in ("PRIVATE_ALIAS", "PRIVATE_TOKEN", "PRIVATE_EVIDENCE"):
                    self.assertNotIn(private, result.content[0].text)

        asyncio.run(run())
        self.assertEqual(len(consumer.calls), 1)

    def test_server_rejects_metadata_mutants(self):
        for mutate in (
                "extra", "readonly", "idempotent", "nondestructive", "name",
                "schema", "title", "description"):
            tools = [_descriptor()]
            if mutate == "extra":
                tools.append(_descriptor())
            elif mutate == "readonly":
                tools[0]["annotations"]["readOnlyHint"] = True
            elif mutate == "idempotent":
                tools[0]["annotations"]["idempotentHint"] = True
            elif mutate == "nondestructive":
                tools[0]["annotations"]["destructiveHint"] = False
            elif mutate == "name":
                tools[0]["name"] = "advance_run"
            elif mutate == "schema":
                tools[0]["inputSchema"]["properties"]["queue"] = {
                    "type": "string"}
            elif mutate == "title":
                tools[0]["title"] = ""
            else:
                tools[0]["description"] = ""
            with self.assertRaisesRegex(ValueError, "INVALID_MCP_EVENTS_METADATA"):
                server_module.build_server_from_consumer(
                    FakeConsumer(descriptors=tools))

    def test_server_malformed_projection_unknown_without_retry(self):
        from mcp import Client

        class Bad(FakeConsumer):
            def call(self, name, arguments):
                self.calls.append((name, copy.deepcopy(arguments)))
                return {"wrong": {}}

        consumer = Bad()
        server = server_module.build_server_from_consumer(consumer)

        async def run():
            async with Client(server) as client:
                result = await client.call_tool("apply_run_event", {})
                self.assertEqual(result.structured_content, {
                    "status": "UNKNOWN",
                    "reason": "MCP_EVENTS_SERVER_OUTCOME_UNKNOWN",
                    "preserve": True,
                    "allow_new_invocation": False,
                })
                self.assertFalse(result.is_error)
                self.assertIn("do not retry", result.content[0].text)

        asyncio.run(run())
        self.assertEqual(len(consumer.calls), 1)

    def test_server_weakened_unknown_is_canonical_without_leak_or_retry(self):
        from mcp import Client

        for payload in (
            {"status": "UNKNOWN", "reason": "PRIVATE_REASON",
             "preserve": False, "allow_new_invocation": False},
            {"status": "UNKNOWN", "reason": "PRIVATE_REASON",
             "preserve": True, "allow_new_invocation": True},
            {"status": {"PRIVATE_REASON": True}},
        ):
            consumer = FakeConsumer(payload)
            server = server_module.build_server_from_consumer(consumer)

            async def run():
                async with Client(server) as client:
                    return await client.call_tool("apply_run_event", {})

            result = asyncio.run(run())
            self.assertEqual(result.structured_content, {
                "status": "UNKNOWN",
                "reason": "MCP_EVENTS_SERVER_OUTCOME_UNKNOWN",
                "preserve": True,
                "allow_new_invocation": False,
            })
            self.assertFalse(result.is_error)
            self.assertNotIn("PRIVATE_REASON", result.content[0].text)
            self.assertEqual(len(consumer.calls), 1)

    def test_server_rejects_operation_or_review_decision_mismatch(self):
        from mcp import Client

        cases = [
            (
                {"operation": "observe", "payload": {}},
                {"status": "APPLIED", "operation": "submit",
                 "result": "SUBMITTED"},
            ),
            (
                {"operation": "review", "payload": {"decision": "REPAIR"}},
                {"status": "APPLIED", "operation": "review",
                 "result": "ACCEPT"},
            ),
        ]
        for arguments, payload in cases:
            consumer = FakeConsumer(payload)
            server = server_module.build_server_from_consumer(consumer)

            async def run():
                async with Client(server) as client:
                    return await client.call_tool(
                        "apply_run_event", arguments)

            result = asyncio.run(run())
            self.assertEqual(result.structured_content, {
                "status": "UNKNOWN",
                "reason": "MCP_EVENTS_SERVER_OUTCOME_UNKNOWN",
                "preserve": True,
                "allow_new_invocation": False,
            })
            self.assertEqual(len(consumer.calls), 1)

    def test_server_delegate_mutation_cannot_rebind_expected_result(self):
        from mcp import Client

        cases = [
            (
                {"operation": "observe", "payload": {}},
                lambda arguments: arguments.update(operation="submit"),
                {"status": "APPLIED", "operation": "submit",
                 "result": "SUBMITTED"},
            ),
            (
                {"operation": "review", "payload": {"decision": "REPAIR"}},
                lambda arguments: arguments["payload"].update(decision="ACCEPT"),
                {"status": "APPLIED", "operation": "review",
                 "result": "ACCEPT"},
            ),
        ]
        for arguments, mutate, payload in cases:
            class MutatingConsumer(FakeConsumer):
                def call(self, name, delegated):
                    self.calls.append((name, copy.deepcopy(delegated)))
                    mutate(delegated)
                    return {"structuredContent": copy.deepcopy(payload)}

            consumer = MutatingConsumer()
            server = server_module.build_server_from_consumer(consumer)

            async def run():
                async with Client(server) as client:
                    return await client.call_tool(
                        "apply_run_event", copy.deepcopy(arguments))

            result = asyncio.run(run())
            self.assertEqual(result.structured_content["status"], "UNKNOWN")
            self.assertTrue(result.structured_content["preserve"])
            self.assertFalse(result.structured_content["allow_new_invocation"])
            self.assertEqual(len(consumer.calls), 1)

    def test_real_windows_stdio_fixture_event_no_model_or_progression(self):
        from mcp import Client, StdioServerParameters

        with tempfile.TemporaryDirectory(prefix="genie phase2b1 ") as temp:
            base = pathlib.Path(temp)
            fixture = _fixture(base, "stdio")
            registry = base / "events registry.json"
            registry.write_text(json.dumps({
                "phase2b1-synthetic": {
                    "queue": str(fixture.queue),
                    "run_id": fixture.policy["run_id"],
                    "owned_root": str(fixture.owned),
                }
            }), encoding="utf-8")
            params = StdioServerParameters(
                command=sys.executable,
                args=["-B", "-m", "shared_interfaces.mcp_events_server",
                      "--registry", str(registry)],
                cwd=str(ROOT),
            )

            async def run():
                async with Client(params) as client:
                    listed = await client.list_tools()
                    self.assertEqual([tool.name for tool in listed.tools],
                                     ["apply_run_event"])
                    return await client.call_tool(
                        "apply_run_event", _observe(fixture))

            result = asyncio.run(run())
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content, {
                "status": "APPLIED", "operation": "observe", "result": "RECORDED"})
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
                    "select count(*) from host_observations").fetchone()[0], 1)
                attempt = database.execute(
                    "select agent,candidate,candidate_hash,review from attempts").fetchone()
                self.assertEqual(attempt, (
                    "phase2b1-fixture-worker-no-model", None, None, None))
            with contextlib.closing(sqlite3.connect(sink)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reports").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select count(*) from applications").fetchone()[0], 0)

    def test_real_windows_stdio_full_synthetic_sequence_stops_before_advance(self):
        from mcp import Client, StdioServerParameters

        with tempfile.TemporaryDirectory(prefix="genie phase2b1 full ") as temp:
            base = pathlib.Path(temp)
            fixture = _fixture(base, "stdio-full")
            registry = base / "events registry.json"
            registry.write_text(json.dumps({
                "phase2b1-synthetic": {
                    "queue": str(fixture.queue),
                    "run_id": fixture.policy["run_id"],
                    "owned_root": str(fixture.owned),
                }
            }), encoding="utf-8")
            params = StdioServerParameters(
                command=sys.executable,
                args=["-B", "-m", "shared_interfaces.mcp_events_server",
                      "--registry", str(registry)],
                cwd=str(ROOT),
            )
            candidate = "PHASE2B1 DETERMINISTIC SYNTHETIC FIXTURE; NO MODEL CALL"
            event_args = [
                _observe(fixture),
                {
                    "run_name": "phase2b1-synthetic",
                    "operation": "submit",
                    "supplied": copy.deepcopy(fixture.token),
                    "payload": {
                        "agent": "phase2b1-fixture-worker-no-model",
                        "text": candidate,
                    },
                },
                {
                    "run_name": "phase2b1-synthetic",
                    "operation": "review",
                    "supplied": copy.deepcopy(fixture.token),
                    "payload": {
                        "candidate_hash": hashlib.sha256(
                            candidate.encode("utf-8")).hexdigest(),
                        "decision": "ACCEPT",
                        "reason": "SYNTHETIC_FIXTURE_ONLY",
                    },
                },
            ]

            async def run():
                async with Client(params) as client:
                    results = []
                    for arguments in event_args:
                        results.append(await client.call_tool(
                            "apply_run_event", arguments))
                    return results

            results = asyncio.run(run())
            self.assertEqual(
                [result.structured_content for result in results], [
                    {"status": "APPLIED", "operation": "observe",
                     "result": "RECORDED"},
                    {"status": "APPLIED", "operation": "submit",
                     "result": "SUBMITTED"},
                    {"status": "APPLIED", "operation": "review",
                     "result": "ACCEPT"},
                ])
            self.assertTrue(all(result.is_error is False for result in results))
            with contextlib.closing(sqlite3.connect(fixture.queue)) as database:
                self.assertEqual(database.execute(
                    "select state from entries").fetchone()[0], "ACTIVE")
                self.assertEqual(database.execute(
                    "select count(*) from reservations").fetchone()[0], 1)
            _, ledger, sink = fixture.runner.paths(
                fixture.owned, fixture.policy["run_id"], fixture.plan["task_id"])
            with contextlib.closing(sqlite3.connect(ledger)) as database:
                self.assertEqual(database.execute(
                    "select state from task").fetchone()[0], "ACCEPTED")
                self.assertEqual(database.execute(
                    "select count(*) from host_calls").fetchone()[0], 1)
                self.assertEqual(database.execute(
                    "select count(*) from host_observations").fetchone()[0], 1)
                attempt = database.execute(
                    "select agent,candidate,candidate_hash,review from attempts").fetchone()
                self.assertEqual(attempt[:3], (
                    "phase2b1-fixture-worker-no-model", candidate,
                    hashlib.sha256(candidate.encode("utf-8")).hexdigest()))
                review = json.loads(attempt[3])
                self.assertEqual(review["decision"], "ACCEPT")
                self.assertEqual(review["reason"], "SYNTHETIC_FIXTURE_ONLY")
                self.assertEqual(review["reviewer"], "trusted-host-controller")
            with contextlib.closing(sqlite3.connect(sink)) as database:
                self.assertEqual(database.execute(
                    "select count(*) from reports").fetchone()[0], 0)
                self.assertEqual(database.execute(
                    "select count(*) from applications").fetchone()[0], 0)

    def test_stdio_only_rejects_http_options(self):
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "shared_interfaces.mcp_events_server",
             "--registry", "unused.json", "--host", "127.0.0.1"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unrecognized arguments", completed.stderr)

    def test_static_surface_has_no_dispatch_progression_driver_or_network(self):
        consumer = (ROOT / "shared_interfaces" / "mcp_events.py").read_text(
            encoding="utf-8")
        server = (ROOT / "shared_interfaces" / "mcp_events_server.py").read_text(
            encoding="utf-8")
        executable = consumer + "\n" + server
        for forbidden in (
            ".step(", "advance_run(", "serve_run(", "drive_run(",
            "session_driver", "subprocess.", "streamable_http_app(",
            "uvicorn.run(", "socket.socket(", "openai", "codex exec",
        ):
            self.assertNotIn(forbidden, executable)

    def test_phase2a_readonly_and_historical_integrity(self):
        manifest = json.loads((
            ROOT / "phase2a_controller" / "SOURCE_MANIFEST.json").read_text(
                encoding="utf-8"))
        self.assertEqual(len(manifest["files"]), 25)
        for name, expected in manifest["files"].items():
            target = ROOT / name
            self.assertEqual(target.stat().st_size, expected["bytes"], name)
            self.assertEqual(_sha(target), expected["sha256"], name)
        historical = _historical_sqlite_paths()
        self.assertEqual(len(historical), 27)
        self.assertEqual(
            _aggregate(historical),
            "56a1f0dcea069ba31a0a09f573fd927eaee4e25900bb6f1554564ffabbe33837")


if __name__ == "__main__":
    unittest.main(verbosity=2)

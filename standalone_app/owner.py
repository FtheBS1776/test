"""Minimal trusted-local standalone owner over the existing Genie core.

This module creates only the first NEW canonical run, reads status, and advances
one existing controller step. It never invokes a model/provider and accepts no
filesystem pathname from its caller.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import types

import live_state_windows as live
import provisioner_windows as provision

MCP_CONSUMER_SHA256 = "21f3fc657abb16c9ba7c9189f266cbdfeaec1dbf0ae2ca6d051caee1565ddd5d"
QUEUE_NAME = "queue.sqlite"
OWNED_ROOT_NAME = "work"
REGISTRY_NAME = "REGISTRY.json"


class OwnerError(ValueError):
    pass


def _load_control_chain():
    """Enter the already pinned shared-core chain without importing MCP runtime."""
    try:
        shared = Path(__file__).resolve().parents[1] / "shared_interfaces"
        source = shared / "mcp_consumer.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != MCP_CONSUMER_SHA256:
            raise ValueError("consumer source mismatch")
        consumer = types.ModuleType("_standalone_pinned_mcp_consumer")
        consumer.__file__ = str(source)
        exec(compile(raw, str(source), "exec"), consumer.__dict__)
        adapter = consumer._load_adapter()
        control = adapter._load_source("run_control.py")
        facade = control._load_facade()
        core = facade._load_core()
        runner = core.load_runner()
        return control, facade, runner
    except Exception:
        raise OwnerError("OWNER_SOURCE_BINDING") from None


def _snapshot(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode(
                             "utf-8", errors="strict")
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise OwnerError("OWNER_INPUT_INVALID") from None


def _precheck_spec(spec, runner):
    """Reject deterministic input errors before acquiring the staging witness.

    Queue initialize/enqueue remain authoritative. Policy checks here mirror the
    existing queue's pure structural constraints only so a typo does not strand
    the fixed one-shot staging namespace before core validation can run.
    """
    value = _snapshot(spec)
    if type(value) is not dict or set(value) != {"run_name", "policy", "plans"}:
        raise OwnerError("OWNER_INPUT_INVALID")
    run_name, policy, plans = value["run_name"], value["policy"], value["plans"]
    try:
        runner.b.ident(run_name)
        if (type(policy) is not dict
                or set(policy) != {"run_id", "max_tasks", "max_model_calls", "effect_scope"}):
            raise ValueError("policy shape")
        runner.b.ident(policy["run_id"])
        if any(type(policy[key]) is not int or not 1 <= policy[key] <= 8
               for key in ("max_tasks", "max_model_calls")):
            raise ValueError("policy bounds")
        if policy["effect_scope"] != "owned-local-report-inbox":
            raise ValueError("effect scope")
        if type(plans) is not list or not plans or len(plans) > policy["max_tasks"]:
            raise ValueError("plan count")
        seen = set()
        for plan in plans:
            runner.q.valid_plan(plan)
            task_id = plan["task_id"]
            if task_id in seen:
                raise ValueError("duplicate task")
            seen.add(task_id)
    except Exception:
        raise OwnerError("OWNER_INPUT_INVALID") from None
    return value


def _write_registry(workspace, run_name, run_id):
    path = workspace / REGISTRY_NAME
    body = {
        run_name: {
            "queue": QUEUE_NAME,
            "run_id": run_id,
            "owned_root": OWNED_ROOT_NAME,
        }
    }
    raw = (json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
        finally:
            os.close(fd)
    except Exception:
        raise OwnerError("OWNER_CREATE_PRESERVE") from None


def _live_runs():
    try:
        return live.load_live_runs()
    except Exception:
        raise OwnerError("OWNER_LIVE_STATE_UNAVAILABLE") from None


def create_first_run(spec):
    """Create one initial canonical run and publish it exactly once."""
    control, facade, runner = _load_control_chain()
    detached = _precheck_spec(spec, runner)
    run_name = detached["run_name"]
    policy = detached["policy"]
    plans = detached["plans"]

    try:
        session = provision.begin()
    except provision.ProvisionError as exc:
        raise OwnerError(str(exc)) from None

    workspace = session.workspace
    queue = workspace / QUEUE_NAME
    owned = workspace / OWNED_ROOT_NAME
    try:
        owned.mkdir(exist_ok=False)
        runner.q.initialize(queue, policy)
        for plan in plans:
            result = runner.q.enqueue(queue, plan)
            if result != "ENQUEUED":
                raise ValueError("unexpected enqueue result")
        _write_registry(workspace, run_name, policy["run_id"])
        state, reason = runner.context(queue, policy["run_id"])
        if state != "RUNNING" or reason is not None:
            raise ValueError("unexpected initialized run state")
        historical = runner.q.status(queue)
        if (historical.get("run_id") != policy["run_id"]
                or historical.get("state") != "RUNNING"
                or len(historical.get("entries", [])) != len(plans)
                or historical.get("reserved_model_calls") != 0):
            raise ValueError("unexpected initialized queue")
    except OwnerError:
        raise
    except Exception:
        # The acquired fixed staging witness is deliberately preserved. A later
        # begin() must fail rather than silently retry/replace partial creation.
        raise OwnerError("OWNER_CREATE_PRESERVE") from None

    try:
        publication = session.publish()
    except provision.ProvisionError as exc:
        raise OwnerError(str(exc)) from None

    # Publication has committed. Any mismatch now is preserved and must not be
    # interpreted as permission to recreate or replace the canonical root.
    try:
        runs = _live_runs()
        record = runs.get(run_name)
        if type(record) is not dict or record.get("run_id") != policy["run_id"]:
            raise ValueError("live binding mismatch")
        host = facade.GenieStatusTools(runs)
        status = host.call("get_run_status", {"run_name": run_name})
        if type(status) is not dict or status.get("status") != "PASS":
            raise ValueError("status unavailable")
    except Exception:
        raise OwnerError("OWNER_PUBLISHED_UNVERIFIED_PRESERVE") from None

    return {
        "status": "CREATED",
        "run_name": run_name,
        "run_id": policy["run_id"],
        "task_count": len(plans),
        "publication": publication,
        "initial_status": status,
        "model_invoked": False,
    }


def status(run_name):
    control, facade, _runner = _load_control_chain()
    try:
        run_name = _snapshot(run_name)
        if type(run_name) is not str:
            raise ValueError("alias")
        runs = _live_runs()
        result = facade.GenieStatusTools(runs).call(
            "get_run_status", {"run_name": run_name})
        if type(result) is not dict:
            raise ValueError("result")
        return result
    except OwnerError:
        raise
    except Exception:
        raise OwnerError("OWNER_STATUS_UNKNOWN") from None


def advance(run_name):
    control, _facade, _runner = _load_control_chain()
    try:
        run_name = _snapshot(run_name)
        if type(run_name) is not str:
            raise ValueError("alias")
        runs = _live_runs()
        result = control.GenieRunController(runs).call(
            "advance_run", {"run_name": run_name})
        if type(result) is not dict:
            raise ValueError("result")
        # Return the existing controller action unchanged. In particular, an
        # INVOKE_WORKER action is NOT executed by this owner unit.
        return result
    except OwnerError:
        raise
    except Exception:
        raise OwnerError("OWNER_ADVANCE_UNKNOWN") from None

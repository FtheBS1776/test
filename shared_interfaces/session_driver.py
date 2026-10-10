"""Finite trusted serial-host driver; uncertain effects stop without retry."""
import hashlib
import io
import json
from pathlib import Path
import sys
import types
EVENTS_SHA256 = "913b4d89bc5bbec0c37141f7914fd111a342d2fced80d25e404d2d25d704f760"
LINE_LIMIT = 160000
def _load_events():
    directory = next((p for p in Path(__file__).resolve().parents
                      if p.name == "shared_interfaces"), None)
    if directory is None:
        raise ValueError("EVENTS_SOURCE_BINDING")
    source = directory / "run_events.py"
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EVENTS_SHA256:
        raise ValueError("EVENTS_SOURCE_BINDING")
    module = types.ModuleType("_driver_pinned_run_events")
    module.__file__ = str(source)
    exec(compile(raw, str(source), "exec"), module.__dict__)
    return module
def _copy(control, value):
    if not control._json_tree(value, set()):
        raise ValueError("STRICT_JSON")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return json.loads(raw.decode("utf-8"))
def _unknown(counts):
    return {"action": "UNKNOWN", "reason": "DRIVER_OUTCOME_UNKNOWN",
            "preserve": True, "allow_new_invocation": False, "counts": dict(counts)}
def _terminal(action, counts):
    return {**action, "counts": dict(counts)}
def _running(core, runner, record):
    queue, run_id, _ = record
    with core.readonly(queue) as db:
        core.schema(db, {"run": ["id", "policy", "state", "stop_reason"]})
        policy, state, reason = runner.q.control(db)
        if policy["run_id"] != run_id:
            raise ValueError("RUN_CONTEXT_BINDING")
        if state != "RUNNING":
            return {"action": "STOP", "reason": reason or "RUN_NOT_RUNNING",
                    "preserve": True, "allow_new_invocation": False}
    return None
def _event_args(alias, operation, token, payload):
    return {"run_name": alias, "operation": operation,
            "supplied": token, "payload": payload}
def _applied(result, operation, allowed):
    return (type(result) is dict and result.get("status") == "APPLIED"
            and result.get("operation") == operation
            and type(result.get("result")) is str and result["result"] in allowed)
def drive_run(runs, run_name, worker, reviewer, max_actions=64, notify=None):
    counts = {"advances": 0, "worker_hooks": 0, "reviewer_hooks": 0}
    if (type(max_actions) is not int or not 1 <= max_actions <= 128
            or type(run_name) is not str or not callable(worker) or not callable(reviewer)
            or (notify is not None and not callable(notify))):
        return _terminal({"action": "REJECT", "reason": "INVALID_DRIVER_INPUT"}, counts)
    try:
        events = _load_events()
        event_host = events.GenieRunEvents(runs)
        if run_name not in event_host._runs:
            return _terminal({"action": "REJECT", "reason": "UNKNOWN_RUN"}, counts)
        control = events._load_control()
        control_host = control.GenieRunController(runs)
        record = event_host._runs[run_name]
        if control_host._runs[run_name] != record:
            raise ValueError("REGISTRY_BINDING")
        facade = control._load_facade()
        core = facade._load_core()
        runner = core.load_runner()
    except Exception:
        return _terminal({"action": "REJECT", "reason": "DRIVER_SETUP_FAILURE"}, counts)
    eligible = {}
    try:
        while counts["advances"] < max_actions:
            counts["advances"] += 1
            action = _copy(control, control_host.call("advance_run", {"run_name": run_name}))
            if notify is not None:
                notify(_copy(control, {"kind": "progress", "action": action, "counts": counts}))
            kind = action.get("action")
            if kind == "INVOKE_WORKER":
                if not control._valid_response(action, record[1]):
                    return _unknown(counts)
                original = _copy(control, action)
                token = original["token"]
                stopped = _running(core, runner, record)
                if stopped:
                    return _terminal(stopped, counts)
                counts["worker_hooks"] += 1
                reply = _copy(control, worker(_copy(control, original)))
                if (not control._fields(reply, {"token", "outcome", "agent", "evidence", "text"})
                        or not control._token(reply["token"], record[1]) or reply["token"] != token):
                    return _unknown(counts)
                observe = _event_args(run_name, "observe", token,
                                     {k: reply[k] for k in ("outcome", "agent", "evidence")})
                observe = events._snapshot(control, observe, record[1])
                submit = None
                if reply["outcome"] == "OBSERVED_ACCEPTED":
                    submit = events._snapshot(control, _event_args(run_name, "submit", token,
                                               {"agent": reply["agent"], "text": reply["text"]}), record[1])
                elif reply["outcome"] != "UNKNOWN" or reply["text"] is not None:
                    return _unknown(counts)
                result = event_host.call("apply_run_event", observe)
                if not _applied(result, "observe", {"RECORDED", "DUPLICATE"}):
                    return _unknown(counts)
                if submit is None:
                    return _unknown(counts)
                result = event_host.call("apply_run_event", submit)
                if not _applied(result, "submit", {"SUBMITTED", "DUPLICATE"}):
                    return _unknown(counts)
                if result["result"] != "SUBMITTED":
                    return _terminal({"action": "RECONCILE_REVIEW", "reason": "SUBMISSION_NOT_NEW",
                                      "preserve": True, "allow_new_invocation": False}, counts)
                key = events._canonical(token)
                eligible[key] = (submit["payload"]["text"], hashlib.sha256(
                    submit["payload"]["text"].encode("utf-8")).hexdigest())
            elif kind == "REVIEW_CANDIDATE":
                if not control._valid_response(action, record[1]):
                    return _unknown(counts)
                original = _copy(control, action)
                token = original["token"]
                key = events._canonical(token)
                saved = eligible.pop(key, None)
                if saved is None:
                    return _terminal({"action": "RECONCILE_REVIEW", "reason": "NO_SESSION_SUBMISSION",
                                      "preserve": True, "allow_new_invocation": False}, counts)
                if saved != (original["candidate"], original["candidate_sha256"]):
                    return _unknown(counts)
                stopped = _running(core, runner, record)
                if stopped:
                    return _terminal(stopped, counts)
                counts["reviewer_hooks"] += 1
                reply = _copy(control, reviewer(_copy(control, original)))
                if (not control._fields(reply, {"token", "candidate_hash", "decision", "reason"})
                        or not control._token(reply["token"], record[1]) or reply["token"] != token
                        or type(reply["candidate_hash"]) is not str
                        or reply["candidate_hash"] != original["candidate_sha256"]):
                    return _unknown(counts)
                review = events._snapshot(control, _event_args(run_name, "review", token,
                                          {k: reply[k] for k in ("candidate_hash", "decision", "reason")}), record[1])
                result = event_host.call("apply_run_event", review)
                if not _applied(result, "review", {reply["decision"], "DUPLICATE"}):
                    return _unknown(counts)
            elif kind == "TASK_COMPLETE":
                if (type(action.get("result")) is not dict
                        or action["result"].get("fresh_destination") != "CONFIRMED"
                        or action["result"].get("status") not in ("COMPLETE", "DUPLICATE")):
                    return _unknown(counts)
                status = core.report(*record)
                selected = [t for t in status["tasks"] if t["task_id"] == action.get("task_id")]
                if (status.get("status") != "PASS" or len(selected) != 1
                        or selected[0]["fresh_sink"].get("status") != "CONFIRMED"):
                    return _unknown(counts)
            elif (kind in {"STOP", "HOLD", "UNKNOWN"}
                  or (type(kind) is str and kind.startswith("RECONCILE"))):
                return _terminal(action, counts)
            elif action.get("status") == "REJECT" or kind == "REJECT":
                return _terminal({**action, "action": "REJECT"}, counts)
            else:
                return _unknown(counts)
        return _terminal({"action": "HOLD", "reason": "DRIVER_ACTION_LIMIT",
                          "preserve": True, "allow_new_invocation": False}, counts)
    except Exception:
        return _unknown(counts)
def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result
def _invalid_constant(value):
    raise ValueError("NONSTANDARD_JSON_CONSTANT")
def serve_run(runs, run_name, input_stream=None, output_stream=None, max_actions=64):
    reader = input_stream if input_stream is not None else sys.stdin.buffer
    writer = output_stream if output_stream is not None else sys.stdout.buffer
    failed = False
    try:
        control = _load_events()._load_control()
    except Exception:
        return _terminal({"action": "REJECT", "reason": "DRIVER_SETUP_FAILURE"},
                         {"advances": 0, "worker_hooks": 0, "reviewer_hooks": 0})
    def emit(message):
        nonlocal failed
        if failed:
            raise ValueError("TRANSPORT_FAILED")
        try:
            message = _copy(control, message)
            raw = (json.dumps(message, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
            if len(raw) > LINE_LIMIT:
                raise ValueError("OUTPUT_BOUND")
            body = raw.decode("utf-8") if isinstance(writer, io.TextIOBase) else raw
            if writer.write(body) != len(body):
                raise ValueError("SHORT_WRITE")
            writer.flush()
        except Exception:
            failed = True
            raise
    def exchange(action, request_kind, response_kind):
        nonlocal failed
        try:
            emit({"kind": request_kind, "action": action})
            line = reader.readline(LINE_LIMIT + 1)
            raw = line.encode("utf-8", errors="strict") if type(line) is str else line
            if type(raw) is not bytes or not raw or len(raw) > LINE_LIMIT or not raw.endswith(b"\n"):
                raise ValueError("INPUT_BOUND_OR_EOF")
            value = json.loads(raw.decode("utf-8", errors="strict"),
                               object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            value = _copy(control, value)
            if not control._fields(value, {"kind", "reply"}) or value["kind"] != response_kind:
                raise ValueError("PROTOCOL_KIND")
            return value["reply"]
        except Exception:
            raise
    result = drive_run(runs, run_name,
                       lambda a: exchange(a, "worker_request", "worker_return"),
                       lambda a: exchange(a, "review_request", "review_decision"),
                       max_actions=max_actions, notify=emit)
    if not failed:
        try:
            emit({"kind": "terminal", "result": result})
        except Exception:
            result = _unknown(result["counts"])
    return result

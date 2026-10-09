"""Render existing observation envelopes; rendering makes no execution claim.

This helper copies historical bindings without checking current ledger state.
The unchanged runner callback remains the final validator of observations.
"""
import argparse
import json
import math
import os
import stat
import sys

TOKEN_KEYS = {"run_id", "task_id", "input_sha256", "attempt", "slot_id", "call_id"}
REQUEST_KEYS = {"task_id", "input_sha256", "attempt", "goal", "feedback"}
FILE_LIMIT = 65536
EVIDENCE_LIMIT = 16000


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _string(value):
    if type(value) is not str:
        raise ValueError("string required")
    # Strict UTF8 excludes every lone surrogate, including strings in keys.
    value.encode("utf-8", errors="strict")


def _tree(value, active):
    kind = type(value)
    if value is None or kind in (bool, int):
        return
    if kind is str:
        _string(value)
        return
    if kind is float:
        if not math.isfinite(value):
            raise ValueError("nonfinite JSON number")
        return
    if kind not in (list, dict):
        raise ValueError("strict JSON types required")
    identity = id(value)
    if identity in active:
        raise ValueError("cyclic JSON value")
    active.add(identity)
    try:
        if kind is dict:
            for key, item in value.items():
                _string(key)
                _tree(item, active)
        else:
            for item in value:
                _tree(item, active)
    finally:
        active.remove(identity)


def _fields(value, keys):
    if type(value) is not dict or set(value) != keys:
        raise ValueError("unexpected object fields")
    if any(type(key) is not str for key in value):
        raise ValueError("exact string keys required")


def _ident(value):
    _string(value)
    if not value or value != value.strip() or len(value) > 200:
        raise ValueError("invalid identifier")


def _hash(value):
    if (type(value) is not str or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise ValueError("invalid lowercase digest")


def _attempt(value):
    if type(value) is not int or not 1 <= value <= 4:
        raise ValueError("invalid attempt")


def build_observation(dispatch, evidence, outcome, agent=None):
    """Return a detached existing observe payload, or raise ValueError.

    UNKNOWN remains UNKNOWN. A successful render neither authenticates caller
    evidence nor accepts a callback, proves execution, or authorizes relaunch.
    """
    try:
        _fields(dispatch, {"action", "request", "token"})
        if type(dispatch["action"]) is not str or dispatch["action"] != "INVOKE_WORKER":
            raise ValueError("original invocation dispatch required")
        request, token = dispatch["request"], dispatch["token"]
        _fields(request, REQUEST_KEYS)
        _fields(token, TOKEN_KEYS)
        for value in (request["task_id"], request["goal"], token["task_id"], token["run_id"]):
            _ident(value)
        for value in (request["input_sha256"], token["input_sha256"], token["slot_id"], token["call_id"]):
            _hash(value)
        _attempt(request["attempt"])
        _attempt(token["attempt"])
        for key in ("task_id", "input_sha256", "attempt"):
            if request[key] != token[key]:
                raise ValueError("request-token binding mismatch")
        if request["feedback"] is not None:
            _ident(request["feedback"])
        if type(outcome) is not str or outcome not in ("UNKNOWN", "OBSERVED_ACCEPTED"):
            raise ValueError("unsupported outcome")
        if outcome == "UNKNOWN":
            if agent is not None:
                raise ValueError("UNKNOWN requires null agent")
        else:
            _ident(agent)
        if type(evidence) is not dict or not evidence:
            raise ValueError("nonempty evidence object required")
        _tree(evidence, set())
        evidence_text = _canonical(evidence)
        if len(evidence_text.encode("utf-8", errors="strict")) > EVIDENCE_LIMIT:
            raise ValueError("evidence canonical byte bound")
        payload = {"supplied": token, "outcome": outcome, "agent": agent, "evidence": evidence}
        # JSON roundtrip detaches all mutable containers without changing the
        # supplied token or rederiving either historical identity digest.
        return json.loads(_canonical(payload))
    except (ValueError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError("invalid observation inputs") from error


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("nonstandard JSON constant")


def _nonblocking_opener(path, flags):
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))


def _read_json(path):
    with open(path, "rb", opener=_nonblocking_opener) as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("regular input file required")
        raw = source.read(FILE_LIMIT + 1)
    if len(raw) > FILE_LIMIT:
        raise ValueError("input file byte bound")
    text = raw.decode("utf-8", errors="strict")
    value = json.loads(text, object_pairs_hook=_unique_object,
                       parse_constant=_invalid_constant)
    _tree(value, set())
    return value


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


class _Once(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if getattr(namespace, self.dest) is not None:
            raise ValueError("repeated flag")
        setattr(namespace, self.dest, value)


def main(argv=None):
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument("--dispatch", required=True, action=_Once)
        parser.add_argument("--evidence", required=True, action=_Once)
        parser.add_argument("--outcome", required=True, action=_Once,
                            choices=("UNKNOWN", "OBSERVED_ACCEPTED"))
        parser.add_argument("--agent", action=_Once)
        args = parser.parse_args(argv)
        dispatch = _read_json(args.dispatch)
        evidence = _read_json(args.evidence)
        payload = build_observation(dispatch, evidence, args.outcome, args.agent)
        serialized = _canonical(payload) + "\n"
        sys.stdout.write(serialized)
        return 0
    except (OSError, ValueError, TypeError, RecursionError, OverflowError):
        sys.stderr.write('{"status":"REJECT","scope":"PAYLOAD_RENDER_ONLY"}\n')
        return 2


if __name__ == "__main__":
    sys.exit(main())

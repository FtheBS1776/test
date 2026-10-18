"""Minimal local CLI for the NONCLAIM standalone Genie owner."""
from __future__ import annotations

import argparse
import json
import math
import sys

from standalone_app import owner

INPUT_LIMIT = 65536


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("OWNER_CLI_ARGUMENTS")


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


def _constant(_value):
    raise ValueError("nonstandard constant")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite")
    return result


def _stdin_object():
    raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
    if len(raw) > INPUT_LIMIT:
        raise ValueError("input bound")
    value = json.loads(raw.decode("utf-8", errors="strict"),
                       object_pairs_hook=_pairs,
                       parse_constant=_constant,
                       parse_float=_float)
    if type(value) is not dict:
        raise ValueError("object required")
    return value


def _emit(value):
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=True, allow_nan=False) + "\n")


def _parser():
    parser = _Parser(prog="genie-owner", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create", allow_abbrev=False,
                        help="Create the first NEW canonical run from stdin JSON.")
    for name in ("status", "advance", "stop"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("run_name")
    return parser


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        if args.command == "create":
            result = owner.create_first_run(_stdin_object())
        elif args.command == "status":
            result = owner.status(args.run_name)
        elif args.command == "stop":
            result = owner.stop(args.run_name)
        else:
            result = owner.advance(args.run_name)
        _emit(result)
        if result.get("status") in ("UNKNOWN", "MISMATCH") or result.get("action") == "UNKNOWN":
            return 3
        if result.get("status") == "REJECT" or result.get("action") == "REJECT":
            return 2
        return 0
    except owner.OwnerError as exc:
        reason = str(exc)
        _emit({"status": "UNKNOWN" if ("UNKNOWN" in reason or "UNVERIFIED" in reason) else "REJECT",
               "reason": reason})
        return 3 if ("UNKNOWN" in reason or "UNVERIFIED" in reason) else 2
    except Exception:
        _emit({"status": "REJECT", "reason": "OWNER_CLI_INPUT"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

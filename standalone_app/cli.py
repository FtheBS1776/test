"""Minimal local CLI for the NONCLAIM standalone Genie owner."""
from __future__ import annotations

import argparse
import json
import sys

from standalone_app import owner
from shared_interfaces import cli as registry_cli

INPUT_LIMIT = 65536


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("OWNER_CLI_ARGUMENTS")


def _stdin_object():
    raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
    if len(raw) > INPUT_LIMIT:
        raise ValueError("input bound")
    value = json.loads(raw.decode("utf-8", errors="strict"),
                       object_pairs_hook=registry_cli._unique_object,
                       parse_constant=registry_cli._invalid_constant,
                       parse_float=registry_cli._finite_float)
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
    entered = False
    try:
        args = _parser().parse_args(argv)
        spec = _stdin_object() if args.command == "create" else None
        entered = True
        if args.command == "create":
            result = owner.create_first_run(spec)
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
        if entered:
            _emit({"status": "UNKNOWN", "reason": "OWNER_CLI_OUTCOME_UNKNOWN",
                   "preserve": True, "allow_new_invocation": False})
            return 3
        _emit({"status": "REJECT", "reason": "OWNER_CLI_INPUT"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

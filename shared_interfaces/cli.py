"""Local read-only CLI for the unchanged, pinned shared Genie facade.

Registry paths are explicit trusted operator configuration, not model inputs.
Exit zero reports usable invocation, never aggregate acceptance or execution.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import types

FACADE_SHA256 = "37629d2ec2d8bdb88da66247c7093225e387b4d79220fb42b214cc01c8ef2619"
REGISTRY_LIMIT = 65536
PROG = "python3 -B -m shared_interfaces.cli"


class _SourceError(ValueError):
    pass


class _HelpRequested(Exception):
    pass


class _ArgumentError(ValueError):
    pass


def _load_facade():
    try:
        directory = next((p for p in Path(__file__).resolve().parents
                          if p.name == "shared_interfaces"), None)
        if directory is None:
            raise ValueError("fixed source location unavailable")
        source = directory / "status_tool.py"
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != FACADE_SHA256:
            raise ValueError("source pin mismatch")
        module = types.ModuleType("_cli_pinned_status_tool")
        module.__file__ = str(source)
        # Only verified maintained source is loaded. tools() does not load core.
        exec(compile(raw, str(source), "exec"), module.__dict__)
        return module
    except Exception:
        raise _SourceError("FACADE_SOURCE_BINDING") from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("nonstandard JSON constant")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite JSON number")
    return result


def _nonblocking_opener(path, flags):
    # Unix FIFO opening must not wait for a writer before fstat. This does not
    # establish a general I/O deadline or hostile filesystem confinement.
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))


def _string(value):
    if type(value) is not str:
        raise ValueError("exact string required")
    value.encode("utf-8", errors="strict")


def _read_registry(path):
    try:
        target = Path(path).resolve(strict=True)
        with open(target, "rb", opener=_nonblocking_opener) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("regular registry required")
            raw = source.read(REGISTRY_LIMIT + 1)
        if len(raw) > REGISTRY_LIMIT:
            raise ValueError("registry byte bound")
        registry = json.loads(raw.decode("utf-8", errors="strict"),
                              object_pairs_hook=_unique_object,
                              parse_constant=_invalid_constant,
                              parse_float=_finite_float)
        if type(registry) is not dict:
            raise ValueError("registry object required")
        detached = {}
        for alias, record in registry.items():
            _string(alias)
            if type(record) is not dict or set(record) != {"queue", "run_id", "owned_root"}:
                raise ValueError("exact registry fields required")
            for value in record.values():
                _string(value)
            run_id = record["run_id"]
            if not run_id or run_id != run_id.strip() or len(run_id) > 200:
                raise ValueError("invalid run identity")
            normalized = {"run_id": run_id}
            for field in ("queue", "owned_root"):
                value = record[field]
                if not value or "\x00" in value:
                    raise ValueError("invalid configured path")
                supplied = Path(value)
                if not supplied.is_absolute():
                    supplied = target.parent / supplied
                normalized[field] = str(supplied.resolve(strict=False))
            detached[alias] = normalized
        return detached
    except Exception:
        raise ValueError("INVALID_REGISTRY") from None


def _emit(value):
    # Escape Unicode for consistent JSON output on local console encodings.
    serialized = json.dumps(value, ensure_ascii=True, allow_nan=False,
                            sort_keys=True, separators=(",", ":"))
    sys.stdout.write(serialized + "\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _ArgumentError("CLI_ARGUMENTS")

    def print_help(self, file=None):
        # Help needs neither maintained source nor registry/core/store access.
        _emit({"usage": self.format_usage().strip(),
               "help": self.format_help()})

    def exit(self, status=0, message=None):
        if status == 0:
            raise _HelpRequested()
        raise _ArgumentError("CLI_ARGUMENTS")


class _Once(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if getattr(namespace, self.dest) is not None:
            raise _ArgumentError("CLI_ARGUMENTS")
        setattr(namespace, self.dest, value)


def _parser():
    parser = _Parser(prog=PROG, allow_abbrev=False,
                     description="Read-only tools, status or accepted task data; no model calls or writes.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("tools", allow_abbrev=False,
                        help="List schemas without registry/core/store access.")
    status = commands.add_parser("status", allow_abbrev=False,
                                 help="Read existing run diagnostics; PASS is not completion.")
    result = commands.add_parser("result", allow_abbrev=False,
                                 help="Read confirmed accepted task data; never execute its contents.")
    for command in (status, result):
        command.add_argument("--registry", required=True, action=_Once)
        command.add_argument("--run", required=True, action=_Once)
    result.add_argument("--task", required=True, action=_Once)
    return parser


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        if args.command == "tools":
            _emit(_load_facade().GenieStatusTools({}).tools())
            return 0
        registry = _read_registry(args.registry)
        host = _load_facade().GenieStatusTools(registry)
        if args.command == "status":
            response = host.call("get_run_status", {"run_name": args.run})
        else:
            response = host.call("get_task_result", {"run_name": args.run, "task_id": args.task})
        if type(response) is not dict:
            raise ValueError("invalid facade response")
        status = response.get("status")
        if status in ("UNKNOWN", "MISMATCH"):
            code = 3
        elif status == "REJECT":
            code = 2
        elif ((args.command == "status" and status == "PASS")
              or (args.command == "result" and status == "CONFIRMED")):
            code = 0
        else:
            raise ValueError("invalid facade status")
        # Preserve diagnostic dictionaries and result data without executing,
        # reclassifying or aggregating per-task states.
        _emit(response)
        return code
    except _HelpRequested:
        return 0
    except _ArgumentError:
        _emit({"status": "REJECT", "reason": "CLI_ARGUMENTS"})
    except _SourceError:
        _emit({"status": "REJECT", "reason": "FACADE_SOURCE_BINDING"})
    except ValueError:
        _emit({"status": "REJECT", "reason": "INVALID_INPUT"})
    except Exception:
        _emit({"status": "REJECT", "reason": "CLI_FAILURE"})
    return 2


if __name__ == "__main__":
    sys.exit(main())

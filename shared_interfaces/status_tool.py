"""Transport-neutral read-only access to the existing Genie status core.

Run aliases and filesystem locations are trusted host configuration. This facade
is neither an MCP server nor an authorization/confinement mechanism. Diagnostic
PASS is not completion; inspect each task's fresh_sink in the unchanged result.
"""
import hashlib
import os
from pathlib import Path
import types

STATUS_SHA256 = "717461b56e191ff011c9b91330d0051f05a0ca03143883566778092e9af2b18e"
RECORD_KEYS = {"queue", "run_id", "owned_root"}


def _reject(reason):
    return {"status": "REJECT", "reason": reason}


class _SourceMismatch(ValueError):
    pass


def _load_core():
    # Candidate and maintained file share this fixed repository ancestor.
    directory = next((p for p in Path(__file__).resolve().parents
                      if p.name == "shared_interfaces"), None)
    if directory is None:
        raise _SourceMismatch("STATUS_SOURCE_BINDING")
    source = directory.parent / "active_runner" / "run_status.py"
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != STATUS_SHA256:
        raise _SourceMismatch("STATUS_SOURCE_BINDING")
    module = types.ModuleType("_shared_pinned_run_status")
    module.__file__ = str(source)
    # Execute only the exact verified owned source bytes. Its existing runner
    # pin and dependency loading remain unchanged; no input selects a module.
    exec(compile(raw, str(source), "exec"), module.__dict__)
    return module


class GenieStatusTools:
    def __init__(self, runs):
        """Detach trusted host alias records without opening any stores."""
        try:
            if type(runs) is not dict:
                raise ValueError("invalid mapping")
            detached = {}
            for name, record in runs.items():
                if type(name) is not str:
                    raise ValueError("invalid alias")
                if (type(record) is not dict or set(record) != RECORD_KEYS
                        or any(type(k) is not str for k in record)):
                    raise ValueError("invalid record")
                if type(record["run_id"]) is not str:
                    raise ValueError("invalid run identity")
                # Path-like values are accepted only from trusted constructor
                # configuration and converted to detached immutable strings.
                queue = os.fspath(record["queue"])
                root = os.fspath(record["owned_root"])
                if type(queue) is not str or type(root) is not str:
                    raise ValueError("invalid path representation")
                if not queue or not root or "\x00" in queue or "\x00" in root:
                    raise ValueError("invalid configured path")
                detached[name] = (queue, record["run_id"], root)
            self._runs = detached
        except Exception:
            raise ValueError("INVALID_RUN_REGISTRY") from None

    def tools(self):
        """Return fresh metadata containing no configured filesystem paths."""
        return [{
            "name": "get_run_status",
            "description": (
                "Read existing Genie run diagnostics for a trusted host alias. "
                "PASS means diagnostics completed; queue completion is history. "
                "Inspect each task's fresh_sink for current local readback. "
                "This tool does not dispatch, approve, deliver or write."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {"run_name": {"type": "string"}},
                "required": ["run_name"],
                "additionalProperties": False,
            },
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        }]

    def call(self, tool_name, arguments):
        """Delegate a valid alias call; sanitize failures without payload text."""
        if type(tool_name) is not str or tool_name != "get_run_status":
            return _reject("UNSUPPORTED_TOOL")
        if (type(arguments) is not dict or set(arguments) != {"run_name"}
                or any(type(k) is not str for k in arguments)
                or type(arguments["run_name"]) is not str):
            return _reject("INVALID_ARGUMENTS")
        alias = arguments["run_name"]
        if alias not in self._runs:
            return _reject("UNKNOWN_RUN")
        queue, run_id, root = self._runs[alias]
        try:
            core = _load_core()
            # Return core report semantics intact: per-task UNKNOWN/MISMATCH/
            # CONFIRMED, historical budget/stop, background false and scope.
            return core.report(queue, run_id, root)
        except _SourceMismatch:
            return _reject("STATUS_SOURCE_BINDING")
        except Exception:
            # Raw exception text may contain paths or stored content. Never
            # convert a core failure to success or disclose its exception chain.
            return _reject("CORE_FAILURE")

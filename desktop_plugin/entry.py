"""Windows Desktop-plugin entry point for Genie's accepted read-only MCP surface.

The plugin binds only to an existing fixed Genie-owned LocalAppData state root.
It never seeds, copies, repairs, migrates, or synchronizes authoritative state.
"""
from __future__ import annotations

import os
import sys

from live_state_windows import LiveStateError, load_live_runs

SELFTEST_ENV = "GENIE_PLUGIN_BUILD_SELFTEST"


class _BootstrapReject(ValueError):
    pass


def _load_runs():
    try:
        return load_live_runs()
    except LiveStateError as exc:
        raise _BootstrapReject(str(exc)) from None
    except Exception:
        raise _BootstrapReject("LIVE_STATE_INVALID") from None


def _build_selftest(runs):
    """CI-only fixed-stage probe; never prints paths, exception text, or data."""
    try:
        from shared_interfaces import status_tool
    except Exception:
        raise _BootstrapReject("SELFTEST_IMPORT") from None
    try:
        host = status_tool.GenieStatusTools(runs)
    except Exception:
        raise _BootstrapReject("SELFTEST_REGISTRY") from None
    try:
        core = status_tool._load_core()
    except Exception:
        raise _BootstrapReject("SELFTEST_CORE_LOAD") from None
    try:
        runner = core.load_runner()
        if runner is None:
            raise ValueError("runner unavailable")
    except Exception:
        raise _BootstrapReject("SELFTEST_RUNNER_LOAD") from None
    try:
        status = host.call("get_run_status", {"run_name": "actual"})
        if type(status) is not dict or status.get("status") != "PASS":
            raise ValueError("status unavailable")
    except Exception:
        raise _BootstrapReject("SELFTEST_CORE_REPORT") from None
    sys.stdout.write("GENIE_PLUGIN_BUILD_SELFTEST_PASS\n")


def _run_transport(runs):
    try:
        import anyio
        from mcp.server.stdio import stdio_server
        from shared_interfaces import mcp_server
        server = mcp_server.build_server(runs)
    except ValueError:
        raise _BootstrapReject("TRANSPORT_BINDING") from None
    except Exception:
        raise _BootstrapReject("TRANSPORT_IMPORT") from None

    async def arun():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options())

    try:
        anyio.run(arun)
    except Exception:
        raise _BootstrapReject("TRANSPORT_RUNTIME") from None


def main():
    try:
        runs = _load_runs()
        if os.environ.get(SELFTEST_ENV) == "1":
            _build_selftest(runs)
            return 0
        _run_transport(runs)
        return 0
    except _BootstrapReject as exc:
        # Fixed reason codes only: do not leak paths, result text, or internals.
        sys.stderr.write("GENIE_PLUGIN_REJECT:" + str(exc) + "\n")
        return 2
    except Exception:
        sys.stderr.write("GENIE_PLUGIN_FAILURE\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

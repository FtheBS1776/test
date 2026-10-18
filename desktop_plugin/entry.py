"""Windows Desktop-plugin entry point for the accepted read-only Genie MCP surface.

The host owns process lifetime and supplies PLUGIN_ROOT / PLUGIN_DATA. Package
code is replaceable; PLUGIN_DATA is persistent and is never overwritten during
an update. First-run seed provisioning is integrity-checked and fail-closed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

STATE_FORMAT = 1
SEED_DIR = "seed_state"
SEED_MANIFEST = "SEED_MANIFEST.json"
STATE_MARKER = ".genie-state.json"
SELFTEST_ENV = "GENIE_PLUGIN_BUILD_SELFTEST"


class _BootstrapReject(ValueError):
    pass


def _bundle_root():
    root = getattr(sys, "_MEIPASS", None)
    return Path(root) if root else Path(__file__).resolve().parent


def _strict_data_root():
    raw = os.environ.get("PLUGIN_DATA")
    if type(raw) is not str or not raw or "\x00" in raw:
        raise _BootstrapReject("PLUGIN_DATA_REQUIRED")
    try:
        root = Path(raw).resolve(strict=True)
    except Exception:
        raise _BootstrapReject("PLUGIN_DATA_REQUIRED") from None
    if not root.is_dir():
        raise _BootstrapReject("PLUGIN_DATA_REQUIRED")
    return root


def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _read_seed_manifest(seed):
    path = seed / SEED_MANIFEST
    try:
        raw = path.read_bytes()
        if len(raw) > 1024 * 1024:
            raise ValueError("manifest bound")
        value = json.loads(raw.decode("utf-8", errors="strict"))
        if (type(value) is not dict or set(value) != {"seed_id", "files"}
                or type(value["seed_id"]) is not str or not value["seed_id"]
                or type(value["files"]) is not list):
            raise ValueError("manifest shape")
        expected = {}
        for item in value["files"]:
            if (type(item) is not dict or set(item) != {"path", "sha256", "size"}
                    or type(item["path"]) is not str or not item["path"]
                    or item["path"].startswith(("/", "\\")) or ".." in Path(item["path"]).parts
                    or type(item["sha256"]) is not str or len(item["sha256"]) != 64
                    or type(item["size"]) is not int or item["size"] < 0
                    or item["path"] in expected):
                raise ValueError("manifest item")
            expected[item["path"]] = (item["sha256"], item["size"])
        actual = {}
        for candidate in seed.rglob("*"):
            if candidate.is_file() and candidate.name != SEED_MANIFEST:
                rel = candidate.relative_to(seed).as_posix()
                actual[rel] = (_sha(candidate), candidate.stat().st_size)
        if actual != expected:
            raise ValueError("seed mismatch")
        return value["seed_id"], hashlib.sha256(raw).hexdigest()
    except Exception:
        raise _BootstrapReject("SEED_INTEGRITY") from None


def _existing_state(state):
    marker = state / STATE_MARKER
    registry = state / "REGISTRY.json"
    try:
        if not marker.is_file() or not registry.is_file():
            raise ValueError("partial")
        raw = marker.read_bytes()
        if len(raw) > 4096:
            raise ValueError("marker bound")
        value = json.loads(raw.decode("utf-8", errors="strict"))
        if (type(value) is not dict or set(value) != {"state_format", "seeded_from"}
                or value["state_format"] != STATE_FORMAT
                or type(value["seeded_from"]) is not str or not value["seeded_from"]):
            raise ValueError("marker shape")
        return registry
    except Exception:
        raise _BootstrapReject("PLUGIN_STATE_PARTIAL_PRESERVE") from None


def _provision_state():
    data = _strict_data_root()
    state = data / "state"
    abandoned = [
        path for path in data.iterdir()
        if path.name.startswith(".state.init-")
    ]
    if abandoned:
        # An earlier first-run provisioning may have entered the copy step.
        # Do not infer rollback, cleanup, safe retry, or permission to reseed.
        raise _BootstrapReject("PLUGIN_STATE_PARTIAL_PRESERVE")
    if state.exists():
        if not state.is_dir():
            raise _BootstrapReject("PLUGIN_STATE_PARTIAL_PRESERVE")
        return _existing_state(state)

    seed = _bundle_root() / SEED_DIR
    seed_id, _manifest_sha = _read_seed_manifest(seed)
    temporary = data / (".state.init-" + str(os.getpid()))
    try:
        shutil.copytree(seed, temporary, ignore=shutil.ignore_patterns(SEED_MANIFEST))
        marker = {"state_format": STATE_FORMAT, "seeded_from": seed_id}
        (temporary / STATE_MARKER).write_text(
            json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8", errors="strict")
        if state.exists():
            raise _BootstrapReject("PLUGIN_STATE_PARTIAL_PRESERVE")
        temporary.replace(state)
    except _BootstrapReject:
        raise
    except Exception:
        raise _BootstrapReject("PLUGIN_STATE_INIT_UNKNOWN") from None
    # A successful move consumed staging. Any remaining staging is uncertain
    # evidence: preserve it so the next launch refuses automatic reseeding.
    return _existing_state(state)


def _build_selftest(registry):
    """CI-only fixed-stage probe; never prints paths, exception text, or data."""
    try:
        from shared_interfaces import cli, status_tool
    except Exception:
        raise _BootstrapReject("SELFTEST_IMPORT") from None
    try:
        runs = cli._read_registry(registry)
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


def _run_transport(registry):
    try:
        from shared_interfaces import mcp_server
    except Exception:
        raise _BootstrapReject("TRANSPORT_IMPORT") from None
    try:
        mcp_server.main(["--registry", str(registry), "--transport", "stdio"])
    except ValueError:
        # Binding/version/source failures are deterministic package incompatibility.
        raise _BootstrapReject("TRANSPORT_BINDING") from None
    except Exception:
        raise _BootstrapReject("TRANSPORT_RUNTIME") from None


def main():
    try:
        registry = _provision_state()
        if os.environ.get(SELFTEST_ENV) == "1":
            _build_selftest(registry)
            return 0
        _run_transport(registry)
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

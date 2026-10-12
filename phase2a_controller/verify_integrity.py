"""Compute read-only Phase 2A integrity evidence without repairing state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(root, paths):
    paths = sorted(paths, key=lambda item: item.as_posix())
    rows = [
        f"{path.as_posix()}\t{(root / path).stat().st_size}\t{_sha256(root / path)}"
        for path in paths
    ]
    return {
        "file_count": len(paths),
        "byte_count": sum((root / path).stat().st_size for path in paths),
        "sha256": hashlib.sha256(("\n".join(rows) + "\n").encode()).hexdigest(),
    }


def _all_files(root):
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def _protected_paths():
    paths = set()
    for name in ("desktop_plugin", "plugin_mcp_consumer", "plugin_mcp_server"):
        paths.update(path.relative_to(ROOT) for path in (ROOT / name).rglob("*")
                     if path.is_file())
    paths.update(Path(name) for name in (
        "shared_interfaces/cli.py",
        "shared_interfaces/status_tool.py",
        "shared_interfaces/function_adapter.py",
        "shared_interfaces/mcp_consumer.py",
        "shared_interfaces/mcp_server.py",
        "shared_interfaces/run_control.py",
        "active_runner/run_status.py",
        "active_runner/runner.py",
        "run_queue/run_policy.py",
        "host_adapter/journal.py",
        "worker_bridge/bridge.py",
        "worker_bridge/reused/report_sink.py",
        "worker_bridge/reused/stateful_subject.py",
        ".github/workflows/genie-desktop-plugin-nonclaim.yml",
        ".github/workflows/genie-mcp-server-nonclaim.yml",
    ))
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--installed-package", type=Path, required=True)
    parser.add_argument("--installed-state", type=Path, required=True)
    args = parser.parse_args(argv)
    historical = {
        path.relative_to(ROOT) for path in ROOT.rglob("*.sqlite")
        if path.relative_to(ROOT).parts[0] != "phase2a_controller"
    }
    result = {
        "repository_protected": _aggregate(ROOT, _protected_paths()),
        "repository_historical_sqlite": _aggregate(ROOT, historical),
        "installed_readonly_package": _aggregate(
            args.installed_package, _all_files(args.installed_package)),
        "installed_readonly_state": _aggregate(
            args.installed_state, _all_files(args.installed_state)),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

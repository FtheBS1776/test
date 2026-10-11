# PyInstaller spec for the Windows local Desktop plugin runtime.
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

ROOT = Path(SPECPATH).resolve().parent
SEED = ROOT / "desktop_plugin" / "build_seed"

runtime_sources = [
    (ROOT / "shared_interfaces" / "mcp_consumer.py", "shared_interfaces"),
    (ROOT / "shared_interfaces" / "function_adapter.py", "shared_interfaces"),
    (ROOT / "shared_interfaces" / "run_control.py", "shared_interfaces"),
    (ROOT / "shared_interfaces" / "cli.py", "shared_interfaces"),
    (ROOT / "shared_interfaces" / "status_tool.py", "shared_interfaces"),
    (ROOT / "active_runner" / "run_status.py", "active_runner"),
    (ROOT / "active_runner" / "runner.py", "active_runner"),
    (ROOT / "run_queue" / "run_policy.py", "run_queue"),
    (ROOT / "host_adapter" / "journal.py", "host_adapter"),
    (ROOT / "worker_bridge" / "bridge.py", "worker_bridge"),
    (ROOT / "worker_bridge" / "reused" / "report_sink.py", "worker_bridge/reused"),
    (ROOT / "worker_bridge" / "reused" / "stateful_subject.py", "worker_bridge/reused"),
]

datas = [(str(source), destination) for source, destination in runtime_sources]
datas.append((str(SEED), "seed_state"))

# Runtime checks use importlib.metadata, so carry the exact reviewed metadata.
transport_distributions = [
    "mcp", "mcp-types", "annotated-types", "anyio", "attrs", "cffi", "click",
    "cryptography", "h11", "httpcore2", "httpx2", "idna", "jsonschema",
    "jsonschema-specifications", "opentelemetry-api", "pycparser", "pydantic",
    "pydantic-core", "PyJWT", "python-multipart", "referencing", "rpds-py",
    "sse-starlette", "starlette", "truststore", "typing-extensions",
    "typing-inspection", "uvicorn", "pywin32",
]
for distribution in transport_distributions:
    datas += copy_metadata(distribution)

# Do not collect all mcp.* modules: that imports the unused optional mcp.cli
# surface and would add CLI-only dependencies such as typer. The approved Genie
# core below is deliberately loaded from raw hash-pinned source data, so imports
# used only inside that dynamic path must be named explicitly for freezing.
hiddenimports = [
    "shared_interfaces.mcp_server",
    "shared_interfaces.cli",
    "mcp.server",
    "mcp.server.stdio",
    "mcp.types",
    "sqlite3",
]

a = Analysis(
    [str(ROOT / "desktop_plugin" / "entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["mcp.cli", "typer"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="genie-mcp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

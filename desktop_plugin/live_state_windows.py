"""Fixed-root Windows binding for Genie's trusted-owned local read-only state.

No model/tool input selects a pathname. This module does not create, copy,
repair, migrate, or synchronize Genie state and does not claim hostile-local
filesystem confinement or rollback/currentness proof.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import uuid

from shared_interfaces import cli

APP_DIR = "GenieReasoningEngine"
STATE_DIR = "state-v1"
MARKER_NAME = "GENIE_STATE.json"
REGISTRY_NAME = "REGISTRY.json"
MARKER_VALUE = {
    "format": "GENIE_LOCAL_STATE_V1",
    "registry": REGISTRY_NAME,
    "scope": "GENIE_OWNED_LOCAL_STATE",
}
MAX_JSON = 65536
DIRECT_CHILD = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}
FOLDERID_LOCAL_APP_DATA = uuid.UUID("f1b32785-6fba-4fcf-9d55-7b8e7f157091")
RPC_E_CHANGED_MODE = 0x80010106
COINIT_APARTMENTTHREADED = 0x2


class LiveStateError(ValueError):
    pass


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _u32(value):
    return ctypes.c_uint32(value).value


def _failed(hr):
    return bool(_u32(hr) & 0x80000000)


def _known_local_app_data():
    if os.name != "nt":
        raise LiveStateError("LIVE_STATE_PLATFORM")
    try:
        ole32 = ctypes.OleDLL("ole32")
        shell32 = ctypes.OleDLL("shell32")
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        ole32.CoInitializeEx.restype = ctypes.c_long
        ole32.CoUninitialize.argtypes = []
        ole32.CoUninitialize.restype = None
        ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole32.CoTaskMemFree.restype = None
        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        shell32.SHGetKnownFolderPath.restype = ctypes.c_long

        init_hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        init_code = _u32(init_hr)
        initialized_here = init_code in (0, 1)
        if _failed(init_hr) and init_code != RPC_E_CHANGED_MODE:
            raise ValueError("COM init")

        pointer = ctypes.c_void_p()
        try:
            guid = _GUID.from_buffer_copy(FOLDERID_LOCAL_APP_DATA.bytes_le)
            hr = shell32.SHGetKnownFolderPath(
                ctypes.byref(guid), 0, None, ctypes.byref(pointer))
            if _failed(hr) or not pointer.value:
                raise ValueError("known folder")
            text = ctypes.wstring_at(pointer.value)
            if not text or "\x00" in text:
                raise ValueError("known folder text")
            base = Path(text).resolve(strict=True)
            if not base.is_dir():
                raise ValueError("known folder type")
            return base
        finally:
            if pointer.value:
                ole32.CoTaskMemFree(pointer)
            if initialized_here:
                ole32.CoUninitialize()
    except LiveStateError:
        raise
    except Exception:
        raise LiveStateError("LIVE_STATE_PLATFORM") from None


def candidate_live_root():
    """Return the fixed lexical live root; do not create it."""
    return _known_local_app_data() / APP_DIR / STATE_DIR


def _strict_json(path, limit=MAX_JSON):
    try:
        if not path.is_file():
            raise ValueError("regular file required")
        raw = path.read_bytes()
        if len(raw) > limit:
            raise ValueError("json bound")

        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate key")
                value[key] = item
            return value

        def invalid_constant(_value):
            raise ValueError("nonstandard constant")

        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=unique,
            parse_constant=invalid_constant,
        )
        return value
    except Exception:
        raise LiveStateError("LIVE_STATE_INVALID") from None


def _root():
    base = _known_local_app_data()
    lexical = base / APP_DIR / STATE_DIR
    try:
        resolved = lexical.resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError("root type")
        resolved.relative_to(base)
        # Fixed two-component namespace must not be redirected outside LocalAppData.
        app = (base / APP_DIR).resolve(strict=True)
        app.relative_to(base)
        if resolved.parent != app or app.parent != base:
            raise ValueError("root confinement")
        return resolved
    except Exception:
        raise LiveStateError("LIVE_STATE_UNAVAILABLE") from None


def _direct_child(root, name, kind):
    if (type(name) is not str or not DIRECT_CHILD.fullmatch(name)
            or name in (".", "..") or name.endswith((".", " "))
            or "/" in name or "\\" in name or ":" in name or "\x00" in name):
        raise LiveStateError("LIVE_STATE_PATH")
    stem = name.split(".", 1)[0].upper()
    if stem in RESERVED:
        raise LiveStateError("LIVE_STATE_PATH")
    try:
        path = (root / name).resolve(strict=True)
        if path.parent != root:
            raise ValueError("escaped direct child")
        if kind == "file" and not path.is_file():
            raise ValueError("file required")
        if kind == "dir" and not path.is_dir():
            raise ValueError("directory required")
        return path
    except LiveStateError:
        raise
    except Exception:
        raise LiveStateError("LIVE_STATE_PATH") from None


def validate_state_root(root, marker_mode="required"):
    """Validate one already selected state root and return detached run records.

    `marker_mode="required"` is the normal live-state contract. The trusted
    local provisioner alone may use `marker_mode="absent"` while validating an
    unpublished staging tree before it creates the provisioner-owned marker.
    This function does not select a path and does not create/modify state.
    """
    if marker_mode not in ("required", "absent"):
        raise LiveStateError("LIVE_STATE_INVALID")
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("root type")
    except Exception:
        raise LiveStateError("LIVE_STATE_INVALID") from None

    marker_lexical = root / MARKER_NAME
    if marker_mode == "required":
        marker_path = _direct_child(root, MARKER_NAME, "file")
        marker = _strict_json(marker_path, 4096)
        if marker != MARKER_VALUE:
            raise LiveStateError("LIVE_STATE_INVALID")
    elif os.path.lexists(marker_lexical):
        # The marker is provisioner-owned; unpublished state may not preseed it.
        raise LiveStateError("LIVE_STATE_INVALID")

    registry_path = _direct_child(root, REGISTRY_NAME, "file")
    raw_registry = _strict_json(registry_path, MAX_JSON)
    if type(raw_registry) is not dict or not raw_registry:
        raise LiveStateError("LIVE_STATE_INVALID")

    try:
        parsed = cli._read_registry(registry_path)
    except Exception:
        raise LiveStateError("LIVE_STATE_INVALID") from None
    if set(parsed) != set(raw_registry):
        raise LiveStateError("LIVE_STATE_INVALID")

    for alias, record in raw_registry.items():
        if (type(alias) is not str or not alias or alias != alias.strip()
                or len(alias) > 200):
            raise LiveStateError("LIVE_STATE_INVALID")
        if (type(record) is not dict
                or set(record) != {"queue", "run_id", "owned_root"}
                or type(record.get("run_id")) is not str):
            raise LiveStateError("LIVE_STATE_INVALID")
        queue = _direct_child(root, record.get("queue"), "file")
        owned = _direct_child(root, record.get("owned_root"), "dir")
        normalized = parsed.get(alias)
        if (type(normalized) is not dict
                or normalized.get("queue") != str(queue)
                or normalized.get("owned_root") != str(owned)
                or normalized.get("run_id") != record["run_id"]):
            raise LiveStateError("LIVE_STATE_BINDING")
    return parsed


def load_live_runs():
    """Validate fixed state binding and return detached absolute run records."""
    return validate_state_root(_root(), marker_mode="required")

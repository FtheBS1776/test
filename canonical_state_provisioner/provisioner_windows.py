"""One-time Windows namespace provisioner for trusted local Genie state.

This is an in-process standalone-owner primitive. It accepts no source path,
model input, MCP request, or remote authorization. It never repairs, retries,
replaces, imports, synchronizes, or cleans up uncertain state automatically.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path

from desktop_plugin import live_state_windows as live

STAGING_DIR = ".state-v1.init"
MOVEFILE_WRITE_THROUGH = 0x00000008
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
PUBLICATION_SCOPE = "FIXED_NAMESPACE_VISIBLE_PUBLICATION_NOT_CRASH_DURABILITY"


class ProvisionError(ValueError):
    pass


def _kernel32():
    if os.name != "nt":
        raise ProvisionError("PROVISION_PLATFORM")
    try:
        dll = ctypes.WinDLL("kernel32", use_last_error=True)
        dll.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
        dll.GetFileAttributesW.restype = wintypes.DWORD
        dll.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
        dll.MoveFileExW.restype = wintypes.BOOL
        return dll
    except Exception:
        raise ProvisionError("PROVISION_PLATFORM") from None


def _attributes(path):
    try:
        value = _kernel32().GetFileAttributesW(str(path))
        if value == INVALID_FILE_ATTRIBUTES:
            raise ValueError("attributes unavailable")
        return int(value)
    except ProvisionError:
        raise
    except Exception:
        raise ProvisionError("PROVISION_NAMESPACE_INVALID") from None


def _plain_directory(path, parent):
    """Validate one existing exact direct-child ordinary directory."""
    try:
        lexical = Path(path)
        parent = Path(parent).resolve(strict=True)
        attrs = _attributes(lexical)
        if not (attrs & FILE_ATTRIBUTE_DIRECTORY) or (attrs & FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("directory attributes")
        resolved = lexical.resolve(strict=True)
        if not resolved.is_dir() or resolved.parent != parent:
            raise ValueError("directory confinement")
        return resolved
    except ProvisionError:
        raise
    except Exception:
        raise ProvisionError("PROVISION_NAMESPACE_INVALID") from None


def _fixed_paths(create_app):
    try:
        base = live._known_local_app_data()
    except Exception:
        raise ProvisionError("PROVISION_PLATFORM") from None
    app_lexical = base / live.APP_DIR
    if os.path.lexists(app_lexical):
        app = _plain_directory(app_lexical, base)
    elif create_app:
        try:
            app_lexical.mkdir(exist_ok=False)
        except FileExistsError:
            # Benign concurrent creation is acceptable only if the winner made
            # the exact ordinary fixed app directory. Staging still arbitrates.
            pass
        except Exception:
            raise ProvisionError("PROVISION_NAMESPACE_CREATE") from None
        app = _plain_directory(app_lexical, base)
    else:
        raise ProvisionError("PROVISION_NAMESPACE_INVALID")
    return base, app, app / live.STATE_DIR, app / STAGING_DIR


def _move_publish(staging, final):
    """Same-parent/same-volume move, no replace-existing flag."""
    try:
        return bool(_kernel32().MoveFileExW(
            str(staging), str(final), MOVEFILE_WRITE_THROUGH))
    except Exception:
        return False


def _write_marker_exclusive(staging):
    path = staging / live.MARKER_NAME
    raw = (json.dumps(live.MARKER_VALUE, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
        finally:
            os.close(fd)
    except Exception:
        raise ProvisionError("PROVISION_MARKER_WRITE_PRESERVE") from None


def _validate(root, marker_mode):
    try:
        return live.validate_state_root(root, marker_mode=marker_mode)
    except Exception:
        raise ProvisionError("PROVISION_STAGING_INVALID_PRESERVE") from None


def _portable_binding(runs):
    """Compare semantics that are supposed to survive staging->final rename."""
    try:
        return {
            alias: (
                Path(record["queue"]).name,
                record["run_id"],
                Path(record["owned_root"]).name,
            )
            for alias, record in runs.items()
        }
    except Exception:
        raise ProvisionError("PROVISION_STAGING_INVALID_PRESERVE") from None


class ProvisioningSession:
    """Single-use in-process staging capability owned by the trusted host."""
    __slots__ = ("_base", "_app", "_staging", "_final", "_state")

    def __init__(self, base, app, staging, final):
        self._base = base
        self._app = app
        self._staging = staging
        self._final = final
        self._state = "OPEN"

    @property
    def workspace(self):
        if self._state != "OPEN":
            raise ProvisionError("PROVISION_SESSION_CLOSED")
        # Detached Path object for the trusted local core. It is not a remote
        # token and publish() accepts no caller-supplied pathname.
        return Path(str(self._staging))

    def publish(self):
        if self._state != "OPEN":
            raise ProvisionError("PROVISION_SESSION_CLOSED")
        # From here onward every failure preserves staging/final evidence.
        self._state = "PRESERVE"
        try:
            base = Path(self._base).resolve(strict=True)
            app = _plain_directory(self._app, base)
            staging = _plain_directory(self._staging, app)
            if staging != self._staging:
                raise ProvisionError("PROVISION_NAMESPACE_INVALID")
            if os.path.lexists(self._final):
                raise ProvisionError("PROVISION_FINAL_EXISTS")

            # Validate all existing registry/store bindings before this unit
            # contributes its provisioner-owned publication marker.
            _validate(staging, marker_mode="absent")
            _write_marker_exclusive(staging)
            prepared = _validate(staging, marker_mode="required")
            prepared_binding = _portable_binding(prepared)

            # Re-check the destination immediately before the one publish call.
            # No REPLACE_EXISTING flag is ever passed to MoveFileExW.
            if os.path.lexists(self._final):
                raise ProvisionError("PROVISION_FINAL_EXISTS")
            if not _move_publish(staging, self._final):
                self._state = "UNKNOWN"
                raise ProvisionError("PUBLISH_UNKNOWN_PRESERVE")

            # The namespace move has reported success. From this point forward,
            # ANY verification failure is a committed-but-unverified outcome;
            # never downgrade it to an ordinary precommit namespace error.
            self._state = "MOVED"
            try:
                final = _plain_directory(self._final, app)
                observed = live.validate_state_root(final, marker_mode="required")
                if _portable_binding(observed) != prepared_binding:
                    raise ValueError("binding changed after publish")
            except Exception:
                self._state = "PUBLISHED_UNVERIFIED"
                raise ProvisionError("PUBLISHED_UNVERIFIED_PRESERVE") from None

            self._state = "PUBLISHED"
            return {
                "status": "PUBLISHED",
                "format": live.MARKER_VALUE["format"],
                "run_names": sorted(observed),
                "scope": PUBLICATION_SCOPE,
            }
        except ProvisionError:
            raise
        except Exception:
            # Once publication entry begins, unknown local failures never imply
            # cleanup, rollback, replay, overwrite, or permission to republish.
            raise ProvisionError("PROVISION_UNKNOWN_PRESERVE") from None


def begin():
    """Acquire the one fixed staging namespace or fail closed."""
    base, app, final, staging = _fixed_paths(create_app=True)
    if os.path.lexists(final):
        raise ProvisionError("PROVISION_FINAL_EXISTS")
    if os.path.lexists(staging):
        raise ProvisionError("PROVISION_STAGING_EXISTS_PRESERVE")
    try:
        staging.mkdir(exist_ok=False)
    except FileExistsError:
        raise ProvisionError("PROVISION_STAGING_EXISTS_PRESERVE") from None
    except Exception:
        raise ProvisionError("PROVISION_STAGING_CREATE") from None
    try:
        exact = _plain_directory(staging, app)
        if exact != staging:
            raise ProvisionError("PROVISION_NAMESPACE_INVALID")
    except ProvisionError:
        # Do not delete a namespace object after exclusive creation if its
        # identity is no longer exactly what this process created/expected.
        raise
    return ProvisioningSession(base, app, exact, final)

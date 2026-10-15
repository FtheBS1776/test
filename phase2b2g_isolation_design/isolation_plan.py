"""Pure validation for the Phase 2B2 isolation recovery design.

This module cannot launch Codex, move credentials, or alter authentication.  It
only turns synthetic metadata into a fail-closed design decision.
"""

from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Iterable


ALLOWED_AUTH_FILE = "auth.json"
REQUIRED_BYPASS_FLAG = "--ignore-user-config"
PROHIBITED_CHILD_INPUTS = frozenset({
    "genie_token",
    "queue_path",
    "owned_root",
    "registry_path",
    "mutation_tool",
    "callback",
    "authority_secret",
})


@dataclass(frozen=True)
class RuntimeSnapshot:
    version: str
    supports_ignore_user_config: bool
    auth_file_exists: bool
    explicit_credentials_store: str | None
    mcp_section_count: int
    plugin_or_app_section_count: int


@dataclass(frozen=True)
class DesignDecision:
    status: str
    preferred_mechanism: str
    credential_copy_allowed: bool
    process_launch_allowed: bool
    next_authorization: str
    reasons: tuple[str, ...]


def decide(snapshot: RuntimeSnapshot) -> DesignDecision:
    """Return the offline decision without touching the host."""
    reasons: list[str] = []
    if not snapshot.supports_ignore_user_config:
        reasons.append("BOUND_RUNTIME_LACKS_DOCUMENTED_CONFIG_BYPASS")
    if snapshot.auth_file_exists:
        reasons.append("AUTH_FILE_IS_PASSWORD_EQUIVALENT")
    if snapshot.mcp_section_count:
        reasons.append("USER_HOME_HAS_MCP_CONFIGURATION")
    if snapshot.plugin_or_app_section_count:
        reasons.append("USER_HOME_HAS_PLUGIN_OR_APP_CONFIGURATION")
    if snapshot.explicit_credentials_store is None:
        reasons.append("CREDENTIAL_STORE_USES_UNBOUND_DEFAULT_OR_FALLBACK")

    ready = (
        snapshot.supports_ignore_user_config
        and snapshot.auth_file_exists
        and snapshot.mcp_section_count >= 0
        and snapshot.plugin_or_app_section_count >= 0
    )
    if ready:
        return DesignDecision(
            status="DESIGN_READY_NONCLAIM",
            preferred_mechanism="USER_HOME_WITH_DOCUMENTED_CONFIG_BYPASS",
            credential_copy_allowed=False,
            process_launch_allowed=False,
            next_authorization="ONE_FRESH_NO_MODEL_ISOLATION_PREFLIGHT",
            reasons=tuple(reasons),
        )
    return DesignDecision(
        status="DESIGN_BLOCKED_NONCLAIM",
        preferred_mechanism="UPGRADE_OR_REBIND_THEN_VERIFY_FLAG_OFFLINE",
        credential_copy_allowed=False,
        process_launch_allowed=False,
        next_authorization="CODEX_UPGRADE_OR_REBIND_ONLY",
        reasons=tuple(reasons),
    )


def validate_isolated_paths(
    codex_home: PureWindowsPath,
    sqlite_home: PureWindowsPath,
    scratch: PureWindowsPath,
    prohibited_roots: Iterable[PureWindowsPath],
) -> tuple[str, ...]:
    """Validate a future isolated layout using lexical absolute paths only."""
    paths = (codex_home, sqlite_home, scratch)
    if any(not path.is_absolute() for path in paths):
        return ("PATH_NOT_ABSOLUTE",)
    folded = tuple(str(path).casefold().rstrip("\\/") for path in paths)
    if len(set(folded)) != len(folded):
        return ("PATHS_NOT_DISTINCT",)
    errors: list[str] = []
    for path in folded:
        for root in prohibited_roots:
            root_text = str(root).casefold().rstrip("\\/")
            if path == root_text or path.startswith(root_text + "\\"):
                errors.append("PATH_INTERSECTS_PROHIBITED_ROOT")
                break
    return tuple(errors)


def validate_child_inputs(keys: Iterable[str]) -> tuple[str, ...]:
    """Reject authority-bearing fields from a future child envelope."""
    return tuple(sorted(PROHIBITED_CHILD_INPUTS.intersection(keys)))

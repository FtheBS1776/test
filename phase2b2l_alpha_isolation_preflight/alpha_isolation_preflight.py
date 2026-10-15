"""Bind the accepted one-shot containment harness to the audited alpha."""

from __future__ import annotations

import os
from pathlib import Path

from phase2b2c_preflight import recovery_preflight as recovery
from shared_interfaces import live_codex_worker as live


KIND = "genie-phase2b2-alpha-isolation-preflight-v1"
MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "low"
SERVICE_TIER = "default"
DISABLED_FEATURES = (
    "apps", "plugins", "plugin_sharing", "recommended_plugins",
    "multi_agent", "multi_agent_v2", "multi_agent_v2_dynamic_tools",
    "remote_plugin", "auth_elicitation", "tool_call_mcp_elicitation",
    "browser_use", "browser_use_external", "browser_use_full_cdp_access",
    "computer_use", "in_app_browser", "image_generation", "hooks",
    "shell_tool", "shell_snapshot", "shell_snapshot_v2", "unified_exec",
    "unified_exec_tty", "view_image", "workspace_dependencies",
    "skill_search", "skill_mcp_dependency_install", "tool_suggest",
    "daemon_auto_start", "worktrees", "code_mode", "code_mode_host",
    "code_mode_tool_search", "sleep_tool", "system_proxy_fallback",
    "network_proxy", "standalone_web_search", "request_permissions_tool",
    "enable_mcp_apps", "codex_apps_mcp_2026_07_28", "mcp_2026_07_28",
)


def command_line(executable):
    args = [
        str(Path(executable).resolve()), "app-server", "--strict-config",
        "-c", "mcp_servers={}",
        "-c", "apps._default.enabled=false",
        "-c", "apps._default.destructive_enabled=false",
        "-c", "apps._default.open_world_enabled=false",
        "-c", 'sandbox_mode="read-only"',
        "-c", 'approval_policy="never"',
        "-c", f'model="{MODEL}"',
        "-c", f'model_reasoning_effort="{REASONING_EFFORT}"',
        "-c", f'service_tier="{SERVICE_TIER}"',
    ]
    for feature in DISABLED_FEATURES:
        args.extend(("--disable", feature))
    args.extend(("--listen", "stdio://"))
    return args


def child_environment(codex_home):
    home = Path(codex_home).resolve()
    if not home.is_dir() or any(home.iterdir()):
        raise ValueError("CODEX_HOME_NOT_FRESH_EMPTY")
    required = (
        "SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP", "PATH",
        "PATHEXT", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
    )
    result = {key: os.environ[key] for key in required if key in os.environ}
    result.update({
        "CODEX_HOME": str(home),
        "NO_COLOR": "1",
        "TERM": "dumb",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
    })
    forbidden = [key for key in result if (
        key.upper().startswith("GENIE")
        or key.upper() in ("OPENAI_API_KEY", "OPENAI_ADMIN_KEY",
                           "CODEX_ACCESS_TOKEN"))]
    if forbidden:
        raise ValueError("AUTHORITY_ENVIRONMENT")
    return result


def run_once(*, executable, version, codex_home, ledger_path,
             timeout_seconds=90, operation_context):
    home = Path(codex_home).resolve()
    child_environment(home)
    originals = (
        recovery.KIND, recovery.preflight_command_line,
        recovery.EFFECTIVE_DISABLED_FEATURES, live.child_environment,
        live.MODEL, live.REASONING_EFFORT, live.SERVICE_TIER,
    )
    try:
        recovery.KIND = KIND
        recovery.preflight_command_line = command_line
        recovery.EFFECTIVE_DISABLED_FEATURES = DISABLED_FEATURES
        live.child_environment = child_environment
        live.MODEL = MODEL
        live.REASONING_EFFORT = REASONING_EFFORT
        live.SERVICE_TIER = SERVICE_TIER
        return recovery.run_once(
            executable=executable, version=version, codex_home=home,
            ledger_path=ledger_path, timeout_seconds=timeout_seconds,
            operation_context=operation_context)
    finally:
        (recovery.KIND, recovery.preflight_command_line,
         recovery.EFFECTIVE_DISABLED_FEATURES, live.child_environment,
         live.MODEL, live.REASONING_EFFORT, live.SERVICE_TIER) = originals


__all__ = ["DISABLED_FEATURES", "KIND", "child_environment", "command_line",
           "run_once"]

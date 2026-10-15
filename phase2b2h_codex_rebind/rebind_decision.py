"""Pure, no-install decision logic for a Codex executable rebind."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    version: str
    channel: str
    executable_sha256: str
    supports_ignore_user_config: bool


@dataclass(frozen=True)
class Decision:
    status: str
    install_allowed: bool
    rebind_allowed: bool
    process_launch_allowed: bool
    reason: str


def decide(installed: Candidate, candidate: Candidate | None) -> Decision:
    if candidate is None:
        return Decision(
            "REJECT_NONCLAIM", False, False, False,
            "NO_SUPPORTED_STABLE_REPLACEMENT")
    if candidate.channel != "stable":
        return Decision(
            "REJECT_NONCLAIM", False, False, False,
            "PRERELEASE_NOT_AUTHORIZED")
    if candidate.executable_sha256 == installed.executable_sha256:
        return Decision(
            "REJECT_NONCLAIM", False, False, False,
            "CANDIDATE_NOT_DISTINCT")
    if not candidate.supports_ignore_user_config:
        return Decision(
            "REJECT_NONCLAIM", False, False, False,
            "REQUIRED_FLAG_UNSUPPORTED")
    return Decision(
        "REBIND_READY_NONCLAIM", True, True, False,
        "DISTINCT_STABLE_CANDIDATE_SUPPORTS_REQUIRED_FLAG")

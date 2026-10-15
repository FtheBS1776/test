"""Pure decision logic for a downloaded, never-executed prerelease candidate."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StaticCandidate:
    prerelease_audit_authorized: bool
    registry_integrity_verified: bool
    os_name: str
    cpu_arch: str
    archive_paths_safe: bool
    lifecycle_scripts: tuple[str, ...]
    authenticode_valid: bool
    signer_subject: str
    executable_sha256: str
    installed_executable_sha256: str
    required_flag_literal_present: bool


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    install_allowed: bool = False
    execute_allowed: bool = False
    process_launch_allowed: bool = False
    runtime_support_proven: bool = False
    effective_isolation_proven: bool = False
    next_authorization: str | None = None


def decide(candidate: StaticCandidate) -> Decision:
    """Classify static evidence without granting install or execution authority."""
    checks = (
        (candidate.prerelease_audit_authorized, "PRERELEASE_AUDIT_NOT_AUTHORIZED"),
        (candidate.registry_integrity_verified, "REGISTRY_INTEGRITY_NOT_VERIFIED"),
        (candidate.os_name == "win32" and candidate.cpu_arch == "x64",
         "PLATFORM_MISMATCH"),
        (candidate.archive_paths_safe, "UNSAFE_ARCHIVE_PATH"),
        (not candidate.lifecycle_scripts, "LIFECYCLE_SCRIPTS_PRESENT"),
        (candidate.authenticode_valid, "AUTHENTICODE_NOT_VALID"),
        ("OpenAI OpCo, LLC" in candidate.signer_subject,
         "SIGNER_NOT_OPENAI"),
        (candidate.executable_sha256 != candidate.installed_executable_sha256,
         "CANDIDATE_NOT_DISTINCT"),
        (candidate.required_flag_literal_present,
         "REQUIRED_FLAG_LITERAL_ABSENT"),
    )
    for passed, reason in checks:
        if not passed:
            return Decision("REJECT_NONCLAIM", reason)

    return Decision(
        status="STATIC_CANDIDATE_NONCLAIM",
        reason="STATIC_PREREQUISITES_SATISFIED_RUNTIME_UNPROVEN",
        next_authorization="ONE_ALPHA_OFFLINE_PARSER_PROBE",
    )

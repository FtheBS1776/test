"""Pure adjudication for the corrected alpha exec parser probe."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    launch_count: int
    candidate_hash_matched: bool
    arguments: tuple[str, ...]
    exit_code: int
    help_lists_required_flag: bool
    original_auth_unchanged: bool
    original_config_unchanged: bool
    alpha_processes_remaining: int
    prompt_supplied: bool
    model_turn_attempted: bool


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    parser_support_proven: bool = False
    runtime_isolation_proven: bool = False
    worker_allowed: bool = False


def decide(observation: Observation) -> Decision:
    if observation.launch_count != 1:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "LAUNCH_COUNT_NOT_ONE")
    if not observation.candidate_hash_matched:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "CANDIDATE_IDENTITY_MISMATCH")
    if observation.arguments != ("exec", "--ignore-user-config", "--help"):
        return Decision("INVALID_EVIDENCE_NONCLAIM", "UNEXPECTED_ARGUMENT_VECTOR")
    if observation.prompt_supplied or observation.model_turn_attempted:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "MODEL_PATH_OUT_OF_SCOPE")
    if not observation.original_auth_unchanged:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "AUTHENTICATION_CHANGED")
    if not observation.original_config_unchanged:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "CONFIGURATION_CHANGED")
    if observation.alpha_processes_remaining:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "ALPHA_PROCESS_REMAINS")
    if observation.exit_code != 0 or not observation.help_lists_required_flag:
        return Decision("PARSER_PROBE_REJECT_NONCLAIM", "EXEC_PARSER_DID_NOT_CONFIRM_FLAG")
    return Decision(
        status="EXEC_PARSER_ACCEPTED_NONCLAIM",
        reason="EXACT_HELP_VECTOR_ACCEPTED_AND_FLAG_LISTED",
        parser_support_proven=True,
    )

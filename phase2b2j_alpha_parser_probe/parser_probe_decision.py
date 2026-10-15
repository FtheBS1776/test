"""Pure adjudication for the bounded alpha parser probe."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    launch_count: int
    candidate_hash_matched: bool
    arguments: tuple[str, ...]
    exit_code: int
    unexpected_argument: bool
    original_auth_unchanged: bool
    original_config_unchanged: bool
    alpha_processes_remaining: int
    model_turn_attempted: bool


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    retry_allowed: bool = False
    runtime_flag_support_proven: bool = False
    live_worker_allowed: bool = False
    next_authorization: str | None = None


def decide(observation: Observation) -> Decision:
    if observation.launch_count != 1:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "LAUNCH_COUNT_NOT_ONE")
    if not observation.candidate_hash_matched:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "CANDIDATE_IDENTITY_MISMATCH")
    if observation.model_turn_attempted:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "MODEL_TURN_OUT_OF_SCOPE")
    if not observation.original_auth_unchanged:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "AUTHENTICATION_CHANGED")
    if not observation.original_config_unchanged:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "CONFIGURATION_CHANGED")
    if observation.alpha_processes_remaining:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "ALPHA_PROCESS_REMAINS")

    expected = ("--ignore-user-config", "--version")
    if observation.arguments != expected:
        return Decision("INVALID_EVIDENCE_NONCLAIM", "UNEXPECTED_ARGUMENT_VECTOR")
    if observation.exit_code == 2 and observation.unexpected_argument:
        return Decision(
            status="PARSER_PROBE_INCONCLUSIVE_NONCLAIM",
            reason="ROOT_PARSER_REJECTED_EXEC_SCOPED_FLAG",
            next_authorization="ONE_CORRECTED_ALPHA_EXEC_HELP_PARSER_PROBE",
        )
    if observation.exit_code == 0:
        return Decision(
            status="PARSER_ACCEPTED_NONCLAIM",
            reason="EXACT_ARGUMENT_VECTOR_ACCEPTED",
            runtime_flag_support_proven=True,
        )
    return Decision("PARSER_PROBE_REJECT_NONCLAIM", "UNCLASSIFIED_NONZERO_EXIT")

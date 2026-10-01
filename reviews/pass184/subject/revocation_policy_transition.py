"""Reference-only policy succession for revocation-source selection.

This module deliberately models binding, not a production signing backend.  A
transition warrant is content-addressed and names both policy instances,
their consecutive generations, and the execution that evaluated it.  It has
no ``authorized`` flag: independent authentication/provisioning remains an
external HOLD.
"""
from dataclasses import asdict, dataclass
import hashlib
import json

from capability_authority import AuthorityError, Evidence as AuthorizationEvidence, VerifierSession
from revocation_source_selection import Evidence, Hold, SourcePolicy, decide, validate_policy_shape


_POLICY_DOMAIN = "BRAINS10-REVOCATION-SOURCE-POLICY-v1"
_TRANSITION_DOMAIN = "BRAINS10-REVOCATION-POLICY-TRANSITION-v1"
_AUTHORIZATION_PROTOCOL = "BRAINS10-REVOCATION-POLICY-AUTHORIZATION-v1"


def _hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def policy_digest(generation, authorized_sources, mode, primary=""):
    if not isinstance(generation, int) or generation < 0:
        raise Hold("generation")
    sources = frozenset(authorized_sources)
    if not sources or any(not isinstance(source, str) or not source for source in sources):
        raise Hold("sources")
    if not isinstance(mode, str) or not mode:
        raise Hold("mode")
    if not isinstance(primary, str):
        raise Hold("primary")
    return _hash({
        "domain": _POLICY_DOMAIN,
        "generation": generation,
        "authorized_sources": sorted(sources),
        "mode": mode,
        "primary": primary,
    })


def make_policy(generation, authorized_sources, mode, primary="", digest=None):
    sources = frozenset(authorized_sources)
    return SourcePolicy(
        digest or policy_digest(generation, sources, mode, primary),
        generation,
        sources,
        mode,
        primary,
    )


def _check_policy(policy):
    if type(policy) is not SourcePolicy:
        raise Hold("policy type")
    if not isinstance(policy.digest, str) or not policy.digest:
        raise Hold("policy digest")
    # The supplied digest names the exact policy artifact.  The separately
    # derived semantic digest prevents that name from being reused for a
    # changed source-selection rule.
    policy_digest(policy.generation, policy.authorized_sources, policy.mode, policy.primary)
    validate_policy_shape(policy)


def policy_semantic_digest(policy):
    _check_policy(policy)
    return policy_digest(
        policy.generation, policy.authorized_sources, policy.mode, policy.primary
    )


@dataclass(frozen=True)
class TransitionAuthorization:
    incumbent_policy_digest: str
    successor_policy_digest: str
    incumbent_generation: int
    successor_generation: int
    incumbent_policy_semantic_digest: str
    successor_policy_semantic_digest: str
    authorization_execution_id: str
    activation_execution_id: str
    incumbent_authorization_evidence_digest: str


def authorization_digest(authorization):
    if type(authorization) is not TransitionAuthorization:
        raise Hold("authorization type")
    fields = asdict(authorization)
    if any(not value for value in fields.values() if not isinstance(value, int)):
        raise Hold("authorization evidence")
    if authorization.incumbent_generation < 0 or authorization.successor_generation < 0:
        raise Hold("authorization generation")
    return _hash({"domain": _TRANSITION_DOMAIN, "fields": fields})


def authorization_lineage(incumbent):
    _check_policy(incumbent)
    return _hash({
        "domain": _TRANSITION_DOMAIN,
        "incumbent_policy_digest": incumbent.digest,
        "incumbent_generation": incumbent.generation,
        "incumbent_policy_semantic_digest": policy_semantic_digest(incumbent),
    })


def issue_reference_authorization(session, incumbent, authorization):
    """Test-only issuer adapter; external verification/provisioning is a HOLD."""
    if type(session) is not VerifierSession:
        raise Hold("authorization session")
    evidence = AuthorizationEvidence(
        _AUTHORIZATION_PROTOCOL,
        authorization_digest(authorization),
        authorization_lineage(incumbent),
    )
    try:
        return session.authorize(evidence)
    except AuthorityError as error:
        raise Hold("authorization issuance") from error


def _require_authorization(session, capability, incumbent, authorization, expected_digest):
    if type(session) is not VerifierSession:
        raise Hold("authorization session")
    try:
        evidence = session.require(capability, _AUTHORIZATION_PROTOCOL)
    except AuthorityError as error:
        raise Hold("authorization capability") from error
    if evidence.lineage_digest != authorization_lineage(incumbent):
        raise Hold("authorization lineage")
    if evidence.evidence_digest != expected_digest:
        raise Hold("authorization evidence")
    if expected_digest != authorization_digest(authorization):
        raise Hold("authorization digest")


def activate(incumbent, successor, authorization, expected_authorization_digest, execution_id,
             authorization_session, authorization_capability):
    """Return the exact successor only under an incumbent-bound transition."""
    _check_policy(incumbent)
    _check_policy(successor)
    if type(authorization) is not TransitionAuthorization:
        raise Hold("authorization type")
    if not isinstance(execution_id, str) or not execution_id:
        raise Hold("execution")
    if not isinstance(expected_authorization_digest, str) or not expected_authorization_digest:
        raise Hold("expected authorization")
    if (
        not isinstance(authorization.authorization_execution_id, str)
        or not authorization.authorization_execution_id
        or not isinstance(authorization.activation_execution_id, str)
        or not authorization.activation_execution_id
    ):
        raise Hold("authorization execution")
    if authorization.activation_execution_id != execution_id:
        raise Hold("authorization execution")
    _require_authorization(
        authorization_session,
        authorization_capability,
        incumbent,
        authorization,
        expected_authorization_digest,
    )
    if (
        authorization.incumbent_policy_digest != incumbent.digest
        or authorization.incumbent_generation != incumbent.generation
        or authorization.successor_policy_digest != successor.digest
        or authorization.successor_generation != successor.generation
        or authorization.incumbent_policy_semantic_digest != policy_semantic_digest(incumbent)
        or authorization.successor_policy_semantic_digest != policy_semantic_digest(successor)
    ):
        raise Hold("authorization binding")
    if successor.generation != incumbent.generation + 1:
        raise Hold("generation")
    return successor


@dataclass(frozen=True)
class SelectionReceipt:
    policy_digest: str
    policy_generation: int
    evidence: tuple[Evidence, ...]
    status: str
    execution_id: str


def authorize_current_receipt(current, receipt):
    """Accept only a receipt created under this exact current policy."""
    _check_policy(current)
    if type(receipt) is not SelectionReceipt or not receipt.execution_id:
        raise Hold("receipt")
    if (
        receipt.policy_digest != current.digest
        or receipt.policy_generation != current.generation
    ):
        raise Hold("historical policy")
    if decide(current, receipt.evidence, current.digest, current.generation) != receipt.status:
        raise Hold("receipt outcome")
    return receipt.status

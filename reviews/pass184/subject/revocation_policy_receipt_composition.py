"""Reference composition of policy-generation, source-selection, and CRL receipts."""
from dataclasses import asdict, dataclass
import hashlib
import json

from revocation_policy_transition import SelectionReceipt, authorize_current_receipt
from revocation_receipt import Hold, RevocationPolicy, RevocationReceipt, authorize as authorize_crl
from revocation_source_selection import Hold as SelectionHold, SourcePolicy


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def selection_receipt_digest(receipt):
    if type(receipt) is not SelectionReceipt:
        raise Hold("selection receipt type")
    return _digest({"domain": "BRAINS10-SELECTION-RECEIPT-v1", "receipt": asdict(receipt)})


def revocation_receipt_digest(receipt):
    if type(receipt) is not RevocationReceipt:
        raise Hold("revocation receipt type")
    return _digest({"domain": "BRAINS10-REVOCATION-RECEIPT-v1", "receipt": asdict(receipt)})


@dataclass(frozen=True)
class ComposedReceipt:
    selection_receipt: SelectionReceipt
    selection_digest: str
    revocation_receipt: RevocationReceipt
    revocation_digest: str
    composition_execution_id: str


def authorize_composed(source_policy, revocation_policy, receipt, expected_cert, expected_time,
                       time_interval):
    if type(source_policy) is not SourcePolicy or type(revocation_policy) is not RevocationPolicy:
        raise Hold("policy type")
    if not receipt.composition_execution_id:
        raise Hold("composition execution")
    if (
        source_policy.digest != revocation_policy.digest
        or source_policy.generation != revocation_policy.generation
    ):
        raise Hold("policy composition")
    if receipt.selection_digest != selection_receipt_digest(receipt.selection_receipt):
        raise Hold("selection digest")
    if receipt.revocation_digest != revocation_receipt_digest(receipt.revocation_receipt):
        raise Hold("revocation digest")
    try:
        selected = authorize_current_receipt(source_policy, receipt.selection_receipt)
        status = authorize_crl(
            revocation_policy, receipt.revocation_receipt, expected_cert, expected_time, time_interval
        )
    except SelectionHold as error:
        raise Hold("selection receipt") from error
    if selected != status:
        raise Hold("status conflict")
    # This profile evaluates a CRL.  A matching policy generation and outcome
    # alone do not establish that the source-selection receipt selected the
    # same CRL bytes used by the revocation receipt.  The policy names the
    # admissible source role explicitly; different evaluator executions may be
    # composed, but the selected source object must be exact.
    if (
        not isinstance(revocation_policy.revocation_source_id, str)
        or not revocation_policy.revocation_source_id
    ):
        raise Hold("revocation source")
    matches = [
        evidence
        for evidence in receipt.selection_receipt.evidence
        if evidence.source == revocation_policy.revocation_source_id
    ]
    if len(matches) != 1:
        raise Hold("revocation source")
    selected_evidence = matches[0]
    if (
        selected_evidence.object_digest != receipt.revocation_receipt.object_digest
        or selected_evidence.status != status
    ):
        raise Hold("revocation object binding")
    return status

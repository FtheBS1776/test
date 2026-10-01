
from dataclasses import dataclass, replace
import hashlib, json, secrets

class AuthorityError(Exception): pass

@dataclass(frozen=True)
class Evidence:
    protocol:str
    evidence_digest:str
    lineage_digest:str

@dataclass(frozen=True)
class AuthorizedEvidence:
    evidence:Evidence
    _nonce:str

class VerifierSession:
    """Reference API-discipline capability issuer.
    NOT a sandbox/security boundary against hostile same-process Python code.
    """
    def __init__(self, lineage_digest:str):
        self.__lineage=lineage_digest
        self.__issued={}
    def authorize(self,e:Evidence)->AuthorizedEvidence:
        if e.lineage_digest!=self.__lineage: raise AuthorityError("lineage")
        nonce=secrets.token_hex(32)
        a=AuthorizedEvidence(e,nonce)
        self.__issued[nonce]=(e.protocol,e.evidence_digest,e.lineage_digest,id(a))
        return a
    def require(self,a:AuthorizedEvidence, protocol:str):
        if type(a) is not AuthorizedEvidence: raise AuthorityError("type")
        row=self.__issued.get(a._nonce)
        want=(a.evidence.protocol,a.evidence.evidence_digest,a.evidence.lineage_digest,id(a))
        if row!=want: raise AuthorityError("not-issued-for-object")
        if a.evidence.protocol!=protocol or a.evidence.lineage_digest!=self.__lineage:
            raise AuthorityError("scope")
        return a.evidence
    def serialize_evidence(self,a:AuthorizedEvidence)->bytes:
        e=self.require(a,a.evidence.protocol)
        return json.dumps({"protocol":e.protocol,"evidence_digest":e.evidence_digest,
                           "lineage_digest":e.lineage_digest},
                          sort_keys=True,separators=(",",":")).encode()

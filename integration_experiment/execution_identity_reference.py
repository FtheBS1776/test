from dataclasses import dataclass
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
DOMAIN="BRAINS10/EXECUTION-ENVELOPE/v1"
def exact_text(x): return type(x) is str and bool(x.strip())

@dataclass(frozen=True)
class ExecutionEnvelope:
 execution_id:str; trust_domain:str; issuer_id:str; key_id:str; authority_config:str
 subject_digest:str; config_digest:str; input_digest:str; result_digest:str; runtime_id:str
 def canonical(self):
  if any(not exact_text(v) for v in self.__dict__.values()): raise ValueError("MALFORMED_IDENTITY")
  return json.dumps({"domain":DOMAIN,**self.__dict__},sort_keys=True,separators=(",",":")).encode()

@dataclass(frozen=True)
class SignedEnvelope:
 envelope:ExecutionEnvelope; signature:bytes

@dataclass(frozen=True)
class IssuerAuthorization:
 trust_domain:str; issuer_id:str; key_id:str; authority_config:str; public_key:bytes
 def __post_init__(self):
  if any(not exact_text(x) for x in (self.trust_domain,self.issuer_id,self.key_id,self.authority_config)):
   raise ValueError("MALFORMED_AUTHORITY")
  if type(self.public_key) is not bytes or len(self.public_key)!=32: raise ValueError("MALFORMED_KEY")

class VerificationError(Exception): pass

class ExecutionIdentityVerifier:
 __slots__=("_auth",)
 def __init__(self,authorizations):
  if type(authorizations) is not tuple or not authorizations: raise ValueError("AUTHORITY_REQUIRED")
  if any(type(a) is not IssuerAuthorization for a in authorizations): raise ValueError("EXACT_AUTHORITY_TYPE_REQUIRED")
  idx={}
  for a in authorizations:
   k=(a.trust_domain,a.issuer_id,a.key_id,a.authority_config)
   if k in idx: raise ValueError("DUPLICATE_AUTHORITY")
   idx[k]=a
  self._auth=idx
 def verify(self,signed):
  if type(signed) is not SignedEnvelope or type(signed.envelope) is not ExecutionEnvelope:
   raise VerificationError("EXACT_EVIDENCE_TYPE_REQUIRED")
  if type(signed.signature) is not bytes or len(signed.signature)!=64:
   raise VerificationError("MALFORMED_SIGNATURE")
  e=signed.envelope
  try: payload=e.canonical()
  except ValueError as ex: raise VerificationError(str(ex))
  a=self._auth.get((e.trust_domain,e.issuer_id,e.key_id,e.authority_config))
  if a is None: raise VerificationError("ISSUER_NOT_AUTHORIZED")
  try: Ed25519PublicKey.from_public_bytes(a.public_key).verify(signed.signature,payload)
  except (InvalidSignature,ValueError): raise VerificationError("BAD_SIGNATURE")
  return e

def sign(private_key,envelope):
 if not isinstance(private_key,Ed25519PrivateKey) or type(envelope) is not ExecutionEnvelope:
  raise ValueError("EXACT_ENVELOPE_REQUIRED")
 return SignedEnvelope(envelope,private_key.sign(envelope.canonical()))

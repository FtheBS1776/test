from dataclasses import dataclass
import hashlib,json
from execution_identity_reference import ExecutionIdentityVerifier, IssuerAuthorization

def S(x): return type(x) is str and bool(x.strip())
def digest_registry(config, entries):
    if not S(config) or type(entries) is not tuple or not entries: raise ValueError("BAD_REGISTRY")
    rows=[]
    for a in entries:
        if type(a) is not IssuerAuthorization: raise ValueError("BAD_REGISTRY_ENTRY")
        rows.append([a.trust_domain,a.issuer_id,a.key_id,a.authority_config,a.public_key.hex()])
        if a.authority_config!=config: raise ValueError("ENTRY_CONFIG_MISMATCH")
    rows.sort()
    return hashlib.sha256(json.dumps(["registry-v1",config,rows],separators=(",",":")).encode()).hexdigest()

@dataclass(frozen=True)
class RegistrySnapshot:
    config:str
    entries:tuple
    digest:str
    def __post_init__(self):
        if self.digest!=digest_registry(self.config,self.entries): raise ValueError("REGISTRY_DIGEST_MISMATCH")
    def verifier(self): return ExecutionIdentityVerifier(self.entries)

@dataclass(frozen=True)
class LifecycleState:
    generation:int
    config:str
    registry_digest:str
    predecessor_digest:str
    def __post_init__(self):
        if type(self.generation) is not int or self.generation<0: raise ValueError("BAD_GENERATION")
        if not all(S(x) for x in (self.config,self.registry_digest,self.predecessor_digest)): raise ValueError("BAD_STATE")
    def digest(self):
        return hashlib.sha256(json.dumps(["lifecycle-v1",self.generation,self.config,
          self.registry_digest,self.predecessor_digest],separators=(",",":")).encode()).hexdigest()

class ProvisionedLifecycle:
    __slots__=("_state","_snapshot")
    def __init__(self, genesis_state, genesis_snapshot, bootstrap_authorized=False):
        # Boolean is intentionally not authority. Test/reference construction requires an exact
        # already-provisioned state/snapshot pair; real OOB bootstrap remains HOLD.
        if bootstrap_authorized is not False: raise ValueError("CALLER_AUTHORITY_FORBIDDEN")
        if type(genesis_state) is not LifecycleState or type(genesis_snapshot) is not RegistrySnapshot:
            raise ValueError("EXACT_GENESIS_TYPES")
        if genesis_state.generation!=0 or genesis_state.registry_digest!=genesis_snapshot.digest or genesis_state.config!=genesis_snapshot.config:
            raise ValueError("GENESIS_BINDING_MISMATCH")
        self._state=genesis_state; self._snapshot=genesis_snapshot
    @property
    def state(self): return self._state
    def verifier_for(self, config):
        if config!=self._state.config or self._snapshot.digest!=self._state.registry_digest:
            return None
        return self._snapshot.verifier()
    def install_successor(self, successor_state, successor_snapshot, incumbent_authorized, successor_authorized):
        # Signatures/threshold evaluation are supplied by the inherited root layer. This reference
        # accepts only exact booleans produced by that layer; it does not claim these booleans are
        # independently authoritative in production.
        if type(successor_state) is not LifecycleState or type(successor_snapshot) is not RegistrySnapshot:
            return "REJECT"
        if incumbent_authorized is not True or successor_authorized is not True: return "REJECT"
        if successor_state.generation!=self._state.generation+1: return "REJECT"
        if successor_state.predecessor_digest!=self._state.digest(): return "REJECT"
        if successor_state.config!=successor_snapshot.config or successor_state.registry_digest!=successor_snapshot.digest:
            return "REJECT"
        self._state=successor_state; self._snapshot=successor_snapshot
        return "OK"

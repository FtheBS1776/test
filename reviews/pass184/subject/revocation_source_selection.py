from dataclasses import dataclass
class Hold(Exception):pass
@dataclass(frozen=True)
class SourcePolicy:
 digest:str;generation:int;authorized_sources:frozenset;mode:str;primary:str=""
@dataclass(frozen=True)
class Evidence:
 source:str;status:str;fresh:bool;authorized:bool;object_digest:str;execution_id:str
def validate_policy_shape(policy):
 if type(policy) is not SourcePolicy:raise Hold("policy type")
 if not isinstance(policy.generation,int) or policy.generation<0:raise Hold("generation")
 if not isinstance(policy.authorized_sources,frozenset) or not policy.authorized_sources:raise Hold("sources")
 if any(not isinstance(source,str) or not source for source in policy.authorized_sources):raise Hold("sources")
 if policy.mode=="SINGLE_REQUIRED":
  if len(policy.authorized_sources)!=1 or policy.primary:raise Hold("policy shape")
  return
 if policy.mode=="PRIMARY_NO_FALLBACK":
  if policy.primary not in policy.authorized_sources:raise Hold("primary")
  return
 if policy.mode=="ALL_REQUIRED_CONSENSUS":
  if policy.primary:raise Hold("policy shape")
  return
 raise Hold("unsupported mode")
def _valid(e,policy):
 if e.source not in policy.authorized_sources or not e.authorized:raise Hold("source")
 if not e.fresh or not e.object_digest or not e.execution_id:raise Hold("evidence")
 if e.status not in ("good","revoked","unknown"):raise Hold("status")
def decide(policy,evidence,expected_digest,expected_generation):
 validate_policy_shape(policy)
 if policy.digest!=expected_digest or policy.generation!=expected_generation:raise Hold("policy")
 by={}
 for e in evidence:
  if e.source in by:raise Hold("duplicate")
  _valid(e,policy);by[e.source]=e
 if policy.mode=="SINGLE_REQUIRED":
  s=next(iter(policy.authorized_sources))
  if s not in by:raise Hold("required")
  if by[s].status=="unknown":raise Hold("unknown")
  return by[s].status
 if policy.mode=="PRIMARY_NO_FALLBACK":
  if policy.primary not in by:raise Hold("primary")
  e=by[policy.primary]
  if e.status=="unknown":raise Hold("unknown")
  return e.status
 if policy.mode=="ALL_REQUIRED_CONSENSUS":
  if set(by)!=set(policy.authorized_sources):raise Hold("required")
  sts={e.status for e in by.values()}
  if "unknown" in sts or len(sts)!=1:raise Hold("conflict")
  return next(iter(sts))
 raise Hold("unreachable")

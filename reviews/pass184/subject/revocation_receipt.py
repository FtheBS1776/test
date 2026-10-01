from dataclasses import dataclass
class Hold(Exception):pass
@dataclass(frozen=True)
class RevocationPolicy:
 digest:str;generation:int;profile:str;issuer_digest:str;revocation_source_id:str
@dataclass(frozen=True)
class RevocationReceipt:
 policy_digest:str;policy_generation:int;profile:str;cert_digest:str;issuer_digest:str
 object_digest:str;status:str;valid_lo:int;valid_hi:int;time_receipt_digest:str
 execution_id:str
def authorize(policy,r,expected_cert,expected_time,time_interval):
 if r.policy_digest!=policy.digest or r.policy_generation!=policy.generation:raise Hold("policy")
 if policy.profile!="DIRECT_COMPLETE_CRL_V1" or r.profile!=policy.profile:raise Hold("profile")
 if policy.revocation_source_id!="crl":raise Hold("source")
 if r.issuer_digest!=policy.issuer_digest:raise Hold("issuer")
 if r.cert_digest!=expected_cert or r.time_receipt_digest!=expected_time:raise Hold("binding")
 if not r.object_digest or not r.execution_id:raise Hold("evidence")
 if r.status not in ("good","revoked"):raise Hold("status")
 lo,hi=time_interval
 if lo<r.valid_lo or hi>r.valid_hi:raise Hold("freshness")
 return r.status

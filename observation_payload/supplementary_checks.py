"""Reviewer-prompted gaps; unchanged frozen suite, no authority checks inferred."""
import importlib.util,json,subprocess,tempfile
from pathlib import Path
from acceptance import sample,canonical
candidate=Path(__file__).parent/'output/observe_payload_1.py'
spec=importlib.util.spec_from_file_location('reviewed_supplement',candidate);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
def check(name,fn):
 try:fn();checks.append({'check':name,'passed':True})
 except Exception as e:checks.append({'check':name,'passed':False,'error':type(e).__name__+': '+str(e)})
def reject(e):
 try:m.build_observation(sample(),e,'UNKNOWN',None)
 except ValueError:return
 raise AssertionError('accepted')
class DictSubclass(dict):pass
check('api_evidence_subclass_rejected',lambda:reject(DictSubclass(valid=True)))
check('api_surrogate_key_rejected',lambda:reject({'\ud800':True}))
def deep():
 root={};cur=root
 for _ in range(2000):cur['nested']={};cur=cur['nested']
 reject(root)
check('api_deep_recursion_normalized_reject',deep)
with tempfile.TemporaryDirectory() as td:
 root=Path(td);d=root/'dispatch.json';e=root/'evidence.json';d.write_text(canonical(sample()))
 def cli(raw,good):
  e.write_bytes(raw);before=(d.read_bytes(),e.read_bytes())
  proc=subprocess.run(['python3.12','-B',str(candidate),'--dispatch',str(d),'--evidence',str(e),'--outcome','UNKNOWN'],capture_output=True,text=True,timeout=5)
  assert proc.returncode==(0 if good else 2) and before==(d.read_bytes(),e.read_bytes())
  if good:assert json.loads(proc.stdout)=={'supplied':sample()['token'],'outcome':'UNKNOWN','agent':None,'evidence':{'valid':True}} and not proc.stderr
  else:assert not proc.stdout and json.loads(proc.stderr)=={'status':'REJECT','scope':'PAYLOAD_RENDER_ONLY'}
 check('cli_overflow_numeric_rejected',lambda:cli(b'{"x":1e999}',False))
 raw=b'{"valid":true}';padded=raw+b' '*(65536-len(raw))
 check('cli_exact_file_byte_limit',lambda:cli(padded,True))
r={'count':len(checks),'checks':checks,'all_passed':all(c['passed'] for c in checks),'scope':'source-review prompted finite supplementary cases; frozen39 suite unchanged'}
(Path(__file__).parent/'SUPPLEMENTARY_RESULTS.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}));raise SystemExit(0 if r['all_passed'] else 1)

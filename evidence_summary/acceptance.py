"""Controller-owned finite report contract checks, frozen before author dispatch."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,tempfile
from pathlib import Path
SCOPE='TEST_LOG_SUMMARY_ONLY'
ENTRY={'path','format','sha256','bytes','read_status','summary'}
TOP={'status','evidence_scope','execution_claim','fresh_sink_claim','entries'}
def run(candidate):
 spec=importlib.util.spec_from_file_location('reviewed_report_logs',candidate)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 checks=[]
 def check(name,fn):
  try:fn();checks.append({'check':name,'passed':True})
  except Exception as e:checks.append({'check':name,'passed':False,'error':type(e).__name__+': '+str(e)})
 def assert_eq(a,b):
  if a!=b:raise AssertionError((a,b))
 def expected(s,n):return {'status':s,'count':n,'evidence_scope':SCOPE}
 def report(inputs):
  r=mod.build_report(inputs)
  assert_eq(set(r),TOP);assert_eq(r['status'],'REPORT_BUILT');assert_eq(r['evidence_scope'],SCOPE)
  assert_eq(r['execution_claim'],'NONE');assert_eq(r['fresh_sink_claim'],'NONE');assert_eq(len(r['entries']),len(inputs))
  for e,i in zip(r['entries'],inputs):
   assert_eq(set(e),ENTRY);assert_eq(e['path'],i['path']);assert_eq(e['format'],i['format'])
  return r['entries']
 with tempfile.TemporaryDirectory() as d:
  d=Path(d)
  def write(name,raw):
   p=d/name;p.write_bytes(raw);return str(p)
  def item(p,fmt='unittest'):return {'path':p,'format':fmt}
  good=write('good.txt',b'Ran 2 tests in 0.01s\nOK\n')
  fail=write('fail.txt',b'Ran 2 tests in 0.01s\nFAILED (failures=1)\n')
  zero=write('zero.txt',b'Ran 0 tests in 0.01s\nOK\n')
  malformed=write('bad.txt',b'OK\n')
  invalidutf=write('utf.txt',b'\xff')
  huge=write('huge.txt',b'x'*(1048576+1))
  exact=write('exact.txt',b'x'*1048576)
  direct=write('direct.json',b'{"status":"FAIL","count":1,"checks":[{"check":"x","passed":false}]}')
  def captured(p,fmt,status,n):
   raw=Path(p).read_bytes();e=report([item(p,fmt)])[0]
   assert_eq(e['summary'],expected(status,n));assert_eq(e['read_status'],'CAPTURED')
   assert_eq(e['bytes'],len(raw));assert_eq(e['sha256'],hashlib.sha256(raw).hexdigest());assert_eq(Path(p).read_bytes(),raw)
  for name,p,fmt,s,n in [('pass',good,'unittest','PASS',2),('failure',fail,'unittest','FAIL',2),('zero',zero,'unittest','NO_COVERAGE',0),('malformed',malformed,'unittest','REJECT',None),('direct_failure',direct,'json','FAIL',1),('exact_limit',exact,'unittest','REJECT',None)]:
   check(name,lambda p=p,fmt=fmt,s=s,n=n:captured(p,fmt,s,n))
  def badread(p,reason,full=False):
   e=report([item(p)])[0];assert_eq(e['summary'],expected('REJECT',None));assert_eq(e['read_status'],reason)
   assert_eq(e['bytes'],Path(p).stat().st_size if full else None)
   assert_eq(e['sha256'],hashlib.sha256(Path(p).read_bytes()).hexdigest() if full else None)
  check('invalid_utf8_retains_full_hash',lambda:badread(invalidutf,'INVALID_UTF8',True))
  check('oversize_has_no_full_hash',lambda:badread(huge,'TOO_LARGE'))
  check('missing_has_no_full_hash',lambda:badread(str(d/'missing'),'UNREADABLE'))
  check('directory_is_unreadable',lambda:badread(str(d),'UNREADABLE'))
  def mixed():
   es=report([item(p) for p in [zero,good,fail,malformed]])
   assert_eq([e['summary']['status'] for e in es],['NO_COVERAGE','PASS','FAIL','REJECT'])
  check('mixed_preserves_order_no_aggregate',mixed)
  actual=Path(__file__).resolve().parents[1]/'comparison_pilot/input'
  def saved():
   paths=[item(str(actual/'zero_discovery.txt')),item(str(actual/'runner_status.txt')),item(str(actual/'direct_checks.json'),'json')]
   es=report(paths);assert_eq([(e['summary']['status'],e['summary']['count']) for e in es],[('NO_COVERAGE',0),('PASS',46),('PASS',17)])
  check('actual_saved_logs',saved)
  invalid=[('not_list',None),('empty',[]),('over_eight',[item(str(d/str(n))) for n in range(9)]),('extra_key',[dict(item(good),extra=1)]),('unknown_format',[item(good,'sql')]),('bool_path',[item(True)]),('empty_path',[item('')]),('nul_path',[item('x\0y')]),('duplicate_path',[item(good),item(good,'json')])]
  for name,inputs in invalid:
   def reject(inputs=inputs):
    try:mod.build_report(inputs)
    except ValueError:return
    raise AssertionError('invalid specification accepted')
   check('api_'+name,reject)
  def cli(args,code,stdout):
   proc=subprocess.run(['python3.12','-B',str(candidate),*args],capture_output=True,text=True,timeout=10)
   assert_eq(proc.returncode,code);assert_eq(json.loads(proc.stdout),stdout)
  ok={'status':'REPORT_WRITTEN','evidence_scope':SCOPE};bad={'status':'REJECT','evidence_scope':SCOPE}
  def cli_success():
   target=d/'new.json';before={p:Path(p).read_bytes() for p in [good,zero,fail]}
   cli(['--output',str(target),'--input','unittest',zero,'--input','unittest',good,'--input','unittest',fail],0,ok)
   r=json.loads(target.read_text());assert_eq([e['summary']['status'] for e in r['entries']],['NO_COVERAGE','PASS','FAIL'])
   assert_eq(before,{p:Path(p).read_bytes() for p in before})
  check('cli_mixed_success_is_not_pass',cli_success)
  def cli_guard(kind):
   target=d/('guard_'+kind)
   if kind=='file':target.write_bytes(b'original')
   elif kind=='dir':target.mkdir()
   elif kind=='symlink':target.symlink_to(good)
   before=Path(good).read_bytes()
   cli(['--output',str(target),'--input','unittest',good],2,bad)
   assert_eq(Path(good).read_bytes(),before)
   if kind=='file':assert_eq(target.read_bytes(),b'original')
   elif kind=='dir':assert target.is_dir()
   else:assert target.is_symlink()
  for kind in ['file','dir','symlink']:check('cli_existing_'+kind,lambda kind=kind:cli_guard(kind))
  def invalidcli(args):
   target=d/'invalid-output.json';cli(['--output',str(target),*args],2,bad);assert not target.exists()
  check('cli_no_inputs',lambda:invalidcli([]))
  check('cli_duplicate_inputs',lambda:invalidcli(['--input','unittest',good,'--input','json',good]))
  check('cli_unknown_format',lambda:invalidcli(['--input','sql',good]))
  check('cli_missing_parent',lambda:cli(['--output',str(d/'absent/new.json'),'--input','unittest',good],2,bad))
  def pin():
   root=d/'copied';(root/'evidence_summary').mkdir(parents=True);(root/'comparison_pilot').mkdir()
   shutil.copyfile(candidate,root/'evidence_summary/report_logs.py')
   dep=Path(__file__).resolve().parents[1]/'comparison_pilot/validation_summary.py'
   (root/'comparison_pilot/validation_summary.py').write_bytes(dep.read_bytes()+b'\n# mutation\n')
   target=root/'out.json'
   proc=subprocess.run(['python3.12','-B',str(root/'evidence_summary/report_logs.py'),'--output',str(target),'--input','unittest',good],capture_output=True,timeout=10)
   assert proc.returncode!=0 and not target.exists()
  check('dependency_pin_rejects_mutation',pin)
 return {'candidate_sha256':hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),'checks':checks,'count':len(checks),'all_passed':all(x['passed'] for x in checks),'scope':'finite controller report checks; no supplied-log execution or filesystem security assurance'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('candidate');ap.add_argument('output');a=ap.parse_args()
 r=run(Path(a.candidate).resolve());Path(a.output).write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='checks'}));raise SystemExit(0 if r['all_passed'] else 1)

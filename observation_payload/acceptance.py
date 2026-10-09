"""Finite controller formatter checks frozen before author dispatch."""
import argparse,copy,hashlib,importlib.util,json,math,os,subprocess,tempfile
from pathlib import Path
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sample():
 token={'run_id':'sample-run','task_id':'sample-task','input_sha256':'a'*64,'attempt':1,'slot_id':'b'*64,'call_id':'c'*64}
 request={k:token[k] for k in ('task_id','input_sha256','attempt')};request.update(goal='Render observation',feedback=None)
 return {'action':'INVOKE_WORKER','request':request,'token':token}
def run(path):
 spec=importlib.util.spec_from_file_location('reviewed_payload',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 checks=[]
 def check(name,fn):
  try:fn();checks.append({'check':name,'passed':True})
  except Exception as e:checks.append({'check':name,'passed':False,'error':type(e).__name__+': '+str(e)})
 def equal(a,b):
  if a!=b:raise AssertionError((a,b))
 def reject(d,e,o='OBSERVED_ACCEPTED',a='worker'):
  try:m.build_observation(d,e,o,a)
  except ValueError:return
  raise AssertionError('accepted malformed input')
 def valid(outcome,agent):
  d=sample();e={'tool':'host','nested':[{'ok':True},None,1.5]};before=copy.deepcopy((d,e))
  r=m.build_observation(d,e,outcome,agent);equal(r,{'supplied':d['token'],'outcome':outcome,'agent':agent,'evidence':e});equal((d,e),before)
  d['token']['task_id']='mutated';e['nested'][0]['ok']=False
  equal(r['supplied']['task_id'],'sample-task');equal(r['evidence']['nested'][0]['ok'],True)
 check('accepted_exact_detached_copy',lambda:valid('OBSERVED_ACCEPTED','worker'))
 check('unknown_stays_unknown',lambda:valid('UNKNOWN',None))
 for name,evidence in [('string','host observation'),('empty',{}),('nonstring_key',{1:'x'}),('tuple',{'x':(1,2)}),('nan',{'x':float('nan')}),('infinity',{'x':float('inf')}),('surrogate',{'x':'\ud800'}),('oversize',{'x':'x'*16001}),('multibyte_size',{'x':'é'*8000})]:
  check('evidence_'+name,lambda evidence=evidence:reject(sample(),evidence))
 cycle={};cycle['self']=cycle;check('evidence_cycle',lambda:reject(sample(),cycle))
 exact={'x':'x'*15992};equal(len(canonical(exact).encode()),16000)
 check('exact_evidence_byte_limit',lambda:equal(m.build_observation(sample(),exact,'UNKNOWN',None)['evidence'],exact))
 def changed(which,key,value):
  d=sample();d[which][key]=value;reject(d,{'valid':True})
 for name,which,key,value in [('bool_attempt','token','attempt',True),('float_attempt','request','attempt',1.0),('wrong_input','request','input_sha256','d'*64),('wrong_task','request','task_id','other'),('attempt_mismatch','request','attempt',2),('extra_token','token','extra',True),('nonhex_slot','token','slot_id','z'*64),('bad_goal','request','goal',' goal'),('bad_feedback','request','feedback','')]:
  check('dispatch_'+name,lambda which=which,key=key,value=value:changed(which,key,value))
 d=sample();d['action']='STOP';check('dispatch_wrong_action',lambda:reject(d,{'valid':True}))
 check('unknown_with_agent',lambda:reject(sample(),{'valid':True},'UNKNOWN','worker'))
 check('accepted_no_agent',lambda:reject(sample(),{'valid':True},'OBSERVED_ACCEPTED',None))
 check('accepted_unstripped_agent',lambda:reject(sample(),{'valid':True},'OBSERVED_ACCEPTED',' worker'))
 check('unsupported_outcome',lambda:reject(sample(),{'valid':True},'PASS',None))
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);dispatch=root/'dispatch.json';evidence=root/'evidence.json'
  dispatch.write_text(canonical(sample()),encoding='utf8');evidence.write_text('{"tool":"host"}',encoding='utf8')
  default=['--dispatch',str(dispatch),'--evidence',str(evidence),'--outcome','OBSERVED_ACCEPTED','--agent','worker']
  def cli(args,good=False):
   before={str(p):p.read_bytes() for p in root.iterdir() if p.is_file()}
   proc=subprocess.run(['python3.12','-B',str(path),*args],capture_output=True,text=True,timeout=5)
   equal(proc.returncode,0 if good else 2)
   if good:
    equal(proc.stderr,'');equal(proc.stdout,canonical({'supplied':sample()['token'],'outcome':'OBSERVED_ACCEPTED','agent':'worker','evidence':{'tool':'host'}})+'\n')
   else:equal(proc.stdout,'');equal(json.loads(proc.stderr),{'status':'REJECT','scope':'PAYLOAD_RENDER_ONLY'})
   equal(before,{str(p):p.read_bytes() for p in root.iterdir() if p.is_file()})
  check('cli_success_readonly_exact',lambda:cli(default,True))
  check('cli_duplicate_option',lambda:cli(default+['--agent','other']))
  check('cli_unknown_option',lambda:cli(default+['--unknown']))
  check('cli_no_arguments',lambda:cli([]))
  def badfile(name,raw,which='evidence'):
   bad=root/name;bad.write_bytes(raw);args=list(default);args[args.index('--'+which)+1]=str(bad);cli(args)
  check('cli_duplicate_nested_key',lambda:badfile('duplicate.json',b'{"x":{"a":1,"a":2}}'))
  check('cli_duplicate_dispatch_key',lambda:badfile('dispatchdup.json',b'{"action":"STOP","action":"INVOKE_WORKER"}','dispatch'))
  check('cli_invalid_utf8',lambda:badfile('invalid.json',b'\xff'))
  check('cli_nonstandard_constant',lambda:badfile('nan.json',b'{"x":NaN}'))
  check('cli_truncated_json',lambda:badfile('truncated.json',b'{"x":'))
  check('cli_file_size_limit',lambda:badfile('oversize.json',b' '*(65537)))
  args=list(default);args[3]=str(root/'missing');check('cli_missing_input',lambda:cli(args))
  def fifo():
   fifo=root/'fifo';os.mkfifo(fifo);args=list(default);args[3]=str(fifo);cli(args)
  check('unix_fifo_rejected_without_writer',fifo)
 return {'candidate_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'checks':checks,'count':len(checks),'all_passed':all(c['passed'] for c in checks),'scope':'finite formatter checks; rendering is not execution/authority/provenance evidence'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('output');a=p.parse_args();r=run(Path(a.candidate).resolve());Path(a.output).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}));raise SystemExit(0 if r['all_passed'] else 1)

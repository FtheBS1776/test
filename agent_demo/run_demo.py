"""One owned etcd/report-inbox integration with abrupt worker and coordinator exits."""
import argparse,base64,dataclasses,hashlib,json,platform,sqlite3,subprocess,sys,time,cryptography
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from owned_etcd import OwnedCluster,demand,save,seal,sha
from execution_identity_reference import ExecutionEnvelope,IssuerAuthorization,sign
from lifecycle_registry import RegistrySnapshot,digest_registry
from etcd_lifecycle_adapter import TestProviderBinding,fixture_authority_state
from report_worker import render
import stateful_subject as st
ROOT=Path(__file__).resolve().parent

def snapshot(path):
 db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
 try:return {'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],'reports':db.execute('SELECT * FROM reports ORDER BY effect_id').fetchall(),'applications':db.execute('SELECT * FROM applications ORDER BY effect_id').fetchall()}
 finally:db.close()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);status={'status':'INDETERMINATE','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False};work=out/'task';work.mkdir()
 def run(label,cmd,expected):
  start=time.monotonic_ns();p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);save(out/(label+'_PROCESS.json'),{'argv':cmd,'start_monotonic_ns':start,'end_monotonic_ns':time.monotonic_ns(),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});demand(p.returncode==expected,label+'_EXIT');return p
 try:
  save(out/'RUNTIME.json',{'python':platform.python_version(),'platform':platform.platform(),'cryptography':cryptography.__version__,'sqlite':sqlite3.sqlite_version,'live_model_calls':0})
  run('REPORT_WORKER',[sys.executable,'-B',str(ROOT/'report_worker.py'),str(ROOT/'VERIFIED_INPUT.json'),str(work/'CANDIDATE.md')],0)
  demand((work/'CANDIDATE.md').read_bytes()==render((ROOT/'VERIFIED_INPUT.json').read_bytes()),'CANDIDATE_CONTRACT')
  with OwnedCluster(out,1) as c:
   baseline=json.loads(c.ctl('baseline_status',0,['endpoint','status'])['stdout'])[0]['Status'];cluster=str(baseline['header']['cluster_id'])
   key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);issuer=IssuerAuthorization('report-demo','fixture-issuer','fixture-key','C1',public);registry=RegistrySnapshot('C1',(issuer,),digest_registry('C1',(issuer,)))
   binding=TestProviderBinding(c.endpoints[0],'owned-demo-etcd',cluster,'/brains10/report-demo/'+c.work.name,'C1');tid='genie-report-task-01';programs={p.name:sha(p) for p in sorted(ROOT.glob('*.py'))}
   payload=(work/'CANDIDATE.md').read_text();result_digest=hashlib.sha256(payload.encode()).hexdigest();config_digest=hashlib.sha256(b'one-owned-report-inbox-v1').hexdigest()
   env=ExecutionEnvelope(tid+'-execution','report-demo','fixture-issuer','fixture-key','C1',programs['report_worker.py'],config_digest,sha(ROOT/'VERIFIED_INPUT.json'),result_digest,'hosted-python-fixture');signed=sign(key,env)
   plan={'task_id':tid,'input_sha256':env.input_digest,'result_sha256':result_digest,'programs':programs,'binding':dataclasses.asdict(binding),'issuer':{**dataclasses.asdict(issuer),'public_key':public.hex()},'envelope':dataclasses.asdict(env),'signature':signed.signature.hex()};save(work/'TASK.json',plan);planhash=sha(work/'TASK.json');save(out/'PLAN_BINDING.json',{'task_sha256':planhash,'input_sha256':env.input_digest,'candidate_sha256':result_digest})
   initial=fixture_authority_state(binding,generation=0,head_digest='TASK-READY',authority_config='C1',lifecycle_generation=7,registry_digest=registry.digest);head=binding.namespace+'/authority-current';effect_id=st.EID(tid,'publish','genie-report-inbox')
   keys={'head':head,'receipt':binding.namespace+'/transition/'+tid,'execution':binding.namespace+'/execution/'+env.execution_id,'outbox':binding.namespace+'/outbox/'+effect_id};save(out/'KEYS.json',keys)
   script=f'version({json.dumps(head)}) = "0"\n\nput {json.dumps(head)} {json.dumps(initial.decode())}\n\nget {json.dumps(head)}\n\n';demand(json.loads(c.ctl('initialize',0,['txn'],script)['stdout']).get('succeeded') is True,'FRESH_NAMESPACE')
   for label,interrupt,expected in [('first',True,75),('resume',False,0),('repeat',False,0)]:
    cmd=[sys.executable,'-B',str(ROOT/'coordinator.py'),str(work),planhash,label]+(['--interrupt'] if interrupt else []);run(label,cmd,expected)
    save(out/(label+'_SINK_SNAPSHOT.json'),snapshot(work/'report_inbox.sqlite'))
    for name,path in keys.items():c.ctl(label+'_'+name,0,['get',path,'--consistency=l'])
   report=snapshot(work/'report_inbox.sqlite');body=json.loads(report['reports'][0][2]);demand(body['payload']==payload,'SINK_REPORT_BINDING');(out/'REPORT.md').write_text(body['payload']+'\n')
   # Hostile retry candidate is a bounded negative; it must not mutate the existing destination.
   bad={**body,'payload':body['payload']+' altered'};p=subprocess.run([sys.executable,'-B',str(ROOT/'report_sink.py'),str(work/'report_inbox.sqlite')],input=json.dumps(bad),capture_output=True,text=True,timeout=15);save(out/'MISMATCH_NEGATIVE.json',{'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'snapshot_after':snapshot(work/'report_inbox.sqlite')});demand(p.returncode==2 and snapshot(work/'report_inbox.sqlite')==report,'MISMATCH_NOT_REJECTED')
   c.ctl('final_status',0,['endpoint','status']);status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
 except Exception as e:status['error']=type(e).__name__+': '+str(e)
 finally:seal(out,status)
 print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

"""Fresh-process task resume using unchanged authority adapter and sink readback."""
import argparse,dataclasses,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from execution_identity_reference import ExecutionEnvelope,SignedEnvelope,IssuerAuthorization
from lifecycle_registry import RegistrySnapshot,digest_registry
from atomic_join import BoundRegistryStore
from etcd_lifecycle_adapter import Gateway,TestProviderBinding,EtcdLifecycleAdapter,EXCHANGE_LOG
from report_worker import render
from report_sink import observe
from owned_etcd import demand,save,sha
import stateful_subject as st
ROOT=Path(__file__).resolve().parent

def load_task(work,expected):
 raw=(work/'TASK.json').read_bytes();demand(hashlib.sha256(raw).hexdigest()==expected,'TASK_PLAN_CHANGED');p=json.loads(raw)
 for n,h in p['programs'].items():demand(sha(ROOT/n)==h,'PROGRAM_CHANGED_'+n)
 data=(ROOT/'VERIFIED_INPUT.json').read_bytes();candidate=(work/'CANDIDATE.md').read_bytes()
 demand(hashlib.sha256(data).hexdigest()==p['input_sha256'],'INPUT_CHANGED')
 demand(candidate==render(data) and hashlib.sha256(candidate).hexdigest()==p['result_sha256'],'RESULT_CHANGED')
 demand(p['envelope']['input_digest']==p['input_sha256'] and p['envelope']['result_digest']==p['result_sha256'] and p['envelope']['subject_digest']==p['programs']['report_worker.py'],'ENVELOPE_CONTENT_BINDING')
 return p,candidate.decode()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('work');ap.add_argument('expected_plan');ap.add_argument('label');ap.add_argument('--interrupt',action='store_true');a=ap.parse_args();work=Path(a.work);trace=[];status={'status':'UNKNOWN','process_id':os.getpid(),'label':a.label}
 def event(name,**values):trace.append({'event':name,'monotonic_ns':time.monotonic_ns(),**values});save(work/(a.label+'_TRACE.json'),trace)
 try:
  p,payload=load_task(work,a.expected_plan)
  issuer=IssuerAuthorization(**{**p['issuer'],'public_key':bytes.fromhex(p['issuer']['public_key'])});registry=RegistrySnapshot('C1',(issuer,),digest_registry('C1',(issuer,)));store=BoundRegistryStore((registry,))
  binding=TestProviderBinding(**p['binding']);adapter=EtcdLifecycleAdapter(Gateway(binding.endpoint,timeout=2),binding,store)
  signed=SignedEnvelope(ExecutionEnvelope(**p['envelope']),bytes.fromhex(p['signature']));tid=p['task_id'];eid=st.EID(tid,'publish','genie-report-inbox')
  outcome,result=adapter.activate(challenge=b'governed-report-task',expected_generation=0,expected_head_digest='TASK-READY',successor_head_digest=p['result_sha256'],transition_id=tid,signed=signed,effects=(('publish','genie-report-inbox',payload),));event('authority_result',outcome=outcome,result=result)
  demand(outcome=='OK','AUTHORITY_NOT_RESOLVED')
  outbox=adapter._read_record(adapter.effect_key(eid));expected={'effect_id':eid,'transition_id':tid,'kind':'publish','target':'genie-report-inbox','payload':payload,'generation':1,'authority_config':'C1'}
  demand(outbox==expected,'OUTBOX_NOT_EXACT_PLAN');event('governed_intent_read',effect_id=eid,payload_sha256=p['result_sha256'])
  sink=work/'report_inbox.sqlite';cmd=[sys.executable,'-B',str(ROOT/'report_sink.py'),str(sink),'--crash','after_commit' if a.interrupt else 'none']
  start=time.monotonic_ns();child=subprocess.run(cmd,input=json.dumps(outbox),capture_output=True,text=True,timeout=15)
  save(work/(a.label+'_SINK_PROCESS.json'),{'argv':cmd,'start_monotonic_ns':start,'end_monotonic_ns':time.monotonic_ns(),'returncode':child.returncode,'stdout':child.stdout,'stderr':child.stderr})
  event('delivery_process_returned',returncode=child.returncode,worker_stdout_used_for_completion=False)
  if a.interrupt:
   demand(child.returncode==73 and child.stdout=='','FAULT_NOT_REACHED')
   status['status']='INTERRUPTED_BEFORE_ACK';save(work/(a.label+'_STATUS.json'),status);save(work/(a.label+'_EXCHANGES.json'),EXCHANGE_LOG);os._exit(75)
  # Neither successful stdout nor an old completion file establishes destination state.
  disposition=observe(sink,expected);event('destination_readback',disposition=disposition)
  demand(disposition=='CONFIRMED','DESTINATION_NOT_CONFIRMED')
  status.update(status='COMPLETE',effect_id=eid,payload_sha256=p['result_sha256'],completion_basis='FRESH_EXACT_DESTINATION_READBACK');returncode=0
 except Exception as e:status['error']=type(e).__name__+': '+str(e);returncode=2
 finally:
  save(work/(a.label+'_STATUS.json'),status);save(work/(a.label+'_EXCHANGES.json'),EXCHANGE_LOG)
 print(json.dumps(status));return returncode
if __name__=='__main__':raise SystemExit(main())

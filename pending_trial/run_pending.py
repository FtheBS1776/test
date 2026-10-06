"""One fixed leader-isolated pending transaction capture; offline adjudication required. NONCLAIM."""
import argparse,base64,dataclasses,json,os,platform,shutil,time,cryptography,threading
from boundary_helpers import stopped_child,copy_paused,GatewayExceptionTrace,OwnedMember
from pathlib import Path
from peer_fixture import PeerFixture
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from owned_etcd import OwnedCluster,canonical,demand,save,seal,sha
from atomic_join import BoundRegistryStore
from execution_identity_reference import ExecutionEnvelope,IssuerAuthorization,sign
from lifecycle_registry import RegistrySnapshot,digest_registry
from etcd_lifecycle_adapter import EtcdLifecycleAdapter,Gateway,TestProviderBinding,EXCHANGE_LOG,fixture_authority_state
import stateful_subject as st
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
 status={'attempt':'fixed-attempt01','status':'INDETERMINATE','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False};calls=[]
 save(out/'RUNTIME_DECLARATIONS.json',{'python':platform.python_version(),'platform':platform.platform(),'cryptography':cryptography.__version__,'dependency_installation':'NONE','diagnostic_execution':'thread-local source-bound Gateway exception trace; original methods unchanged','clock':vars(time.get_clock_info('monotonic'))})
 def call(label,fn):
  v={'label':label,'exchange_start':len(EXCHANGE_LOG),'start_monotonic_ns':time.monotonic_ns()};outcome,result=fn();
  if dataclasses.is_dataclass(result):
   result=dataclasses.asdict(result);result['challenge']=result['challenge'].hex();result['raw_value']=base64.b64encode(result['raw_value']).decode()
  v.update(outcome=outcome,result=result,exchange_end=len(EXCHANGE_LOG),end_monotonic_ns=time.monotonic_ns());calls.append(v);save(out/'CALLS.json',calls);return outcome
 try:
  fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.split(':',1)[0] in ('Pid','NSpid')}
  save(out/'OWN_PID_VIEW.json',{'os_getpid':os.getpid(),'proc_fields':fields,'same_pid_view':str(os.getpid())==fields['Pid']});demand(str(os.getpid())==fields['Pid'],'PID_VIEW_MISMATCH_LOCAL_ENVIRONMENT_HOLD')
  with PeerFixture(out) as c:
   candidates=[json.loads(c.ctl(f'candidate_status_{i}',i,['endpoint','status'])['stdout'])[0] for i in range(3)]
   demand(len({v['Status']['leader'] for v in candidates})==1,'BASELINE_LEADER_DISAGREEMENT');selected=next(i for i in range(3) if candidates[i]['Status']['header']['member_id']==candidates[i]['Status']['leader'])
   baseline=json.loads(c.ctl('baseline_status',selected,['endpoint','status'])['stdout'])[0];member=OwnedMember.select(c,selected,baseline);save(out/'SELECTED_MEMBER.json',member.record());s=baseline['Status'];cluster=str(s['header']['cluster_id'])
   private=Ed25519PrivateKey.generate();pub=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
   issuer=IssuerAuthorization('test-domain','issuer-1','key-1','C1',pub);registry=RegistrySnapshot('C1',(issuer,),digest_registry('C1',(issuer,)));store=BoundRegistryStore((registry,))
   binding=TestProviderBinding(c.endpoints[selected],'owned-test-etcd',cluster,'/brains10/wal-control/'+c.work.name,'C1');adapter=EtcdLifecycleAdapter(Gateway(binding.endpoint,timeout=2),binding,store)
   save(out/'FIXTURE_BINDING.json',{'binding':dataclasses.asdict(binding),'binding_digest':binding.digest(),'registry_digest':registry.digest,'issuer_public_key':pub.hex(),'member_id':str(s['header']['member_id']),'cluster_id':cluster})
   initial=fixture_authority_state(binding,generation=0,head_digest='HEAD-A',authority_config='C1',lifecycle_generation=7,registry_digest=registry.digest)
   script=f'version({json.dumps(adapter.current_key.decode())}) = "0"\n\nput {json.dumps(adapter.current_key.decode())} {json.dumps(initial.decode())}\n\nget {json.dumps(adapter.current_key.decode())}\n\n'
   demand(json.loads(c.ctl('initialize',selected,['txn'],script)['stdout']).get('succeeded') is True,'REUSED_NAMESPACE')
   c.ctl('parent_head',selected,['get',adapter.current_key.decode(),'--consistency=l'])
   tid='wal_control_activation';eid=tid+'-execution';envelope=ExecutionEnvelope(eid,'test-domain','issuer-1','key-1','C1','subject-1','config-1','input-1','result-1','runtime-1');signed=sign(private,envelope)
   save(out/'ENVELOPE.json',dataclasses.asdict(envelope))
   keys={'head':adapter.current_key,'receipt':adapter.receipt_key(tid),'execution':adapter.execution_key(eid),'outbox':adapter.effect_key(st.EID(tid,'publish','wal-control-target'))};save(out/'KEYS.json',{k:v.decode() for k,v in keys.items()})
   def activate():return adapter.activate(challenge=b'wal-control-challenge',expected_generation=0,expected_head_digest='HEAD-A',successor_head_digest='HEAD-B',transition_id=tid,signed=signed,effects=(('publish','wal-control-target','wal-control-payload'),))
   fingerprint=st.FP(0,'HEAD-A','HEAD-B',tid,'C1',(('publish','wal-control-target','wal-control-payload'),))
   envelope_fp=__import__('hashlib').sha256(envelope.canonical()).hexdigest()
   c.ctl('before_pause_status',selected,['endpoint','status'])
   before_status=json.loads((out/'before_pause_status.json').read_text())
   current=json.loads(before_status['stdout'])[0]['Status']
   demand(current['leader']==int(member.member_id) and current['raftTerm']==s['raftTerm'],'LEADER_CHANGED_BEFORE_TRIAL')
   tracer=GatewayExceptionTrace();worker_error=[];hook=[];hook_ready=threading.Event()
   def before_txn(body):
    digest=__import__('hashlib').sha256(body).hexdigest()
    demand(not hook,'SECOND_HOOK_FORBIDDEN')
    hook.append({'event':'hook_entered','monotonic_ns':time.monotonic_ns(),'request_sha256':digest,'thread_id':threading.get_ident()})
    (out/'ORIGINAL_TXN.json').write_bytes(body)
    c.network.isolate(selected,[v['Status']['header']['member_id'] for v in candidates])
    hook.append({'event':'hook_completed','monotonic_ns':time.monotonic_ns(),'request_sha256':digest,'thread_id':threading.get_ident()})
    save(out/'HOOK.json',hook);hook_ready.set()
   adapter.gateway.before_txn=before_txn
   def original_activation():
    try:
     with tracer:demand(call('original_activation',activate)=='UNKNOWN_COMMIT','ORIGINAL_NOT_UNKNOWN_COMMIT')
    except Exception as e:worker_error.append(type(e).__name__+': '+str(e))
   worker=threading.Thread(target=original_activation,name='owned-pending-txn',daemon=True)
   try:
    worker.start();demand(hook_ready.wait(6),'HOOK_NOT_COMPLETED')
    deadline=hook[-1]['monotonic_ns']+150000000
    while time.monotonic_ns()<deadline:time.sleep(max(0,min(.005,(deadline-time.monotonic_ns())/1e9)))
    with stopped_child(c,out,member) as (pid,task_states):
     copy_paused(c,out,member,pid,task_states)
     worker.join(timeout=3);demand(not worker.is_alive() and not worker_error,'ORIGINAL_CLIENT_INCOMPLETE')
     save(out/'TRACE.json',tracer.record())
     save(out/'AUTHORITY_DECISION.json',{'decision':'HOLD','adapter_outcome':'UNKNOWN_COMMIT','diagnostics_used_for_authority':False})
   finally:
    c.network.heal();adapter.gateway.before_txn=None
    if worker.is_alive():worker.join(timeout=5)
    if tracer.thread_id is not None and hasattr(tracer,'source_hash_after'):save(out/'TRACE.json',tracer.record())
    save(out/'HOOK.json',hook);save(out/'CLIENT_THREAD_ERRORS.json',worker_error)
   demand(not worker.is_alive() and not worker_error,'CLIENT_CLEANUP_INCOMPLETE')
   c.wait_healthy(range(3),'resumed')
   demand(call('resumed_current_read',lambda:adapter.read_current(b'resumed-control-challenge','C1'))=='CURRENT','RESUMED_READ_FAILED')
   demand(call('reconcile_original',lambda:adapter.reconcile(tid,fingerprint,eid,envelope_fp)) in ('OK','UNKNOWN_COMMIT'),'RECONCILE_UNEXPECTED')
   demand(call('same_identity_retry',activate)=='OK','SAME_IDENTITY_RETRY_FAILED')
   for name,key in keys.items():c.ctl('committed_'+name,selected,['get',key.decode(),'--consistency=l'])
   demand(call('exact_retry',activate)=='OK','EXACT_RETRY_FAILED')
   for name,key in keys.items():c.ctl('final_'+name,selected,['get',key.decode(),'--consistency=l'])
   c.ctl('membership',selected,['member','list']);c.ctl('final_status',selected,['endpoint','status'])
   status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
 except Exception as e:status['error']=type(e).__name__+': '+str(e)
 finally:save(out/'HTTP_EXCHANGES.json',EXCHANGE_LOG);save(out/'CALLS.json',calls);seal(out,status)
 print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

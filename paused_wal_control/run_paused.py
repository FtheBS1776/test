"""Healthy actual adapter control with paused WAL snapshot and original read-timeout trace. NONCLAIM."""
import argparse,base64,dataclasses,json,os,platform,shutil,time,cryptography,threading
from boundary_helpers import stopped_child,copy_paused,GatewayExceptionTrace
from pathlib import Path
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
 status={'status':'INDETERMINATE','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False};calls=[]
 save(out/'RUNTIME_DECLARATIONS.json',{'python':platform.python_version(),'platform':platform.platform(),'cryptography':cryptography.__version__,'dependency_installation':'NONE','diagnostic_execution':'thread-local source-bound Gateway exception trace; original methods unchanged','clock':vars(time.get_clock_info('monotonic'))})
 def call(label,fn):
  v={'label':label,'exchange_start':len(EXCHANGE_LOG),'start_monotonic_ns':time.monotonic_ns()};outcome,result=fn();
  if dataclasses.is_dataclass(result):
   result=dataclasses.asdict(result);result['challenge']=result['challenge'].hex();result['raw_value']=base64.b64encode(result['raw_value']).decode()
  v.update(outcome=outcome,result=result,exchange_end=len(EXCHANGE_LOG),end_monotonic_ns=time.monotonic_ns());calls.append(v);save(out/'CALLS.json',calls);return outcome
 try:
  fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.split(':',1)[0] in ('Pid','NSpid')}
  save(out/'OWN_PID_VIEW.json',{'os_getpid':os.getpid(),'proc_fields':fields,'same_pid_view':str(os.getpid())==fields['Pid']});demand(str(os.getpid())==fields['Pid'],'PID_VIEW_MISMATCH_LOCAL_ENVIRONMENT_HOLD')
  with OwnedCluster(out,1) as c:
   s=json.loads(c.ctl('baseline_status',0,['endpoint','status'])['stdout'])[0]['Status'];cluster=str(s['header']['cluster_id'])
   private=Ed25519PrivateKey.generate();pub=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
   issuer=IssuerAuthorization('test-domain','issuer-1','key-1','C1',pub);registry=RegistrySnapshot('C1',(issuer,),digest_registry('C1',(issuer,)));store=BoundRegistryStore((registry,))
   binding=TestProviderBinding(c.endpoints[0],'owned-test-etcd',cluster,'/brains10/wal-control/'+c.work.name,'C1');adapter=EtcdLifecycleAdapter(Gateway(binding.endpoint,timeout=2),binding,store)
   save(out/'FIXTURE_BINDING.json',{'binding':dataclasses.asdict(binding),'binding_digest':binding.digest(),'registry_digest':registry.digest,'issuer_public_key':pub.hex(),'member_id':str(s['header']['member_id']),'cluster_id':cluster})
   initial=fixture_authority_state(binding,generation=0,head_digest='HEAD-A',authority_config='C1',lifecycle_generation=7,registry_digest=registry.digest)
   script=f'version({json.dumps(adapter.current_key.decode())}) = "0"\n\nput {json.dumps(adapter.current_key.decode())} {json.dumps(initial.decode())}\n\nget {json.dumps(adapter.current_key.decode())}\n\n'
   demand(json.loads(c.ctl('initialize',0,['txn'],script)['stdout']).get('succeeded') is True,'REUSED_NAMESPACE')
   c.ctl('parent_head',0,['get',adapter.current_key.decode(),'--consistency=l'])
   tid='wal_control_activation';eid=tid+'-execution';envelope=ExecutionEnvelope(eid,'test-domain','issuer-1','key-1','C1','subject-1','config-1','input-1','result-1','runtime-1');signed=sign(private,envelope)
   save(out/'ENVELOPE.json',dataclasses.asdict(envelope))
   keys={'head':adapter.current_key,'receipt':adapter.receipt_key(tid),'execution':adapter.execution_key(eid),'outbox':adapter.effect_key(st.EID(tid,'publish','wal-control-target'))};save(out/'KEYS.json',{k:v.decode() for k,v in keys.items()})
   def activate():return adapter.activate(challenge=b'wal-control-challenge',expected_generation=0,expected_head_digest='HEAD-A',successor_head_digest='HEAD-B',transition_id=tid,signed=signed,effects=(('publish','wal-control-target','wal-control-payload'),))
   demand(call('activation',activate)=='OK','CONTROL_ACTIVATION_FAILED')
   for name,key in keys.items():c.ctl('committed_'+name,0,['get',key.decode(),'--consistency=l'])
   c.ctl('before_pause_status',0,['endpoint','status'])
   tracer=GatewayExceptionTrace();worker_error=[]
   def paused_read():
    try:
     with tracer:demand(call('paused_current_read',lambda:adapter.read_current(b'paused-control-challenge','C1'))=='UNAVAILABLE','PAUSED_READ_AUTHORITY_ACCEPTED')
    except Exception as e:worker_error.append(type(e).__name__+': '+str(e))
   worker=threading.Thread(target=paused_read,name='owned-paused-read',daemon=True)
   try:
    with stopped_child(c,out) as (pid,task_states):
     worker.start();demand(tracer.started.wait(.5),'ORIGINAL_GATEWAY_CALL_NOT_OBSERVED');copy_paused(c,out,pid,task_states);worker.join(timeout=3);demand(not worker.is_alive() and not worker_error,'CLIENT_READ_INCOMPLETE');save(out/'TRACE.json',tracer.record());demand(tracer.restore_ok and not tracer.errors,'TRACE_INVALID')
     timeout_events=[e for e in tracer.events if e.get('exact_timeout_type') is True];demand(len(timeout_events)==1,'EXACT_ORIGINAL_TIMEOUT_NOT_OBSERVED');boundary=json.loads((out/'SNAPSHOT_BOUNDARY.json').read_text());demand(boundary['end_monotonic_ns']<timeout_events[0]['monotonic_ns'],'COPY_NOT_BEFORE_OBSERVED_TIMEOUT');save(out/'AUTHORITY_DECISION.json',{'decision':'HOLD','adapter_outcome':'UNAVAILABLE','diagnostics_used_for_authority':False})
   finally:
    if worker.is_alive():worker.join(timeout=3)
    if tracer.thread_id is not None and hasattr(tracer,'source_hash_after'):save(out/'TRACE.json',tracer.record())
    save(out/'CLIENT_THREAD_ERRORS.json',worker_error)
   c.wait_healthy(range(1),'resumed');demand(call('resumed_current_read',lambda:adapter.read_current(b'resumed-control-challenge','C1'))=='CURRENT','RESUMED_READ_FAILED')
   demand(call('exact_retry',activate)=='OK','EXACT_RETRY_FAILED')
   for name,key in keys.items():c.ctl('final_'+name,0,['get',key.decode(),'--consistency=l'])
   c.ctl('membership',0,['member','list']);c.ctl('final_status',0,['endpoint','status'])
   c.stop(0);demand(c.processes[0].returncode in (0,-15),'UNEXPECTED_STOP');demand(not any(e['action']=='cleanup_forced' for e in c.events),'FORCED_STOP')
   logs=[json.loads(line) for line in (out/'SERVER_0_START_0.txt').read_text().splitlines()];demand(any(v.get('msg')=='closed etcd server' and v.get('data-dir')==str(c.work/'m0') for v in logs),'SERVER_CLOSE_NOT_OBSERVED')
   status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
 except Exception as e:status['error']=type(e).__name__+': '+str(e)
 finally:save(out/'HTTP_EXCHANGES.json',EXCHANGE_LOG);save(out/'CALLS.json',calls);seal(out,status)
 print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

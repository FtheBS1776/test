"""Healthy actual adapter control, then post-stop WAL snapshot. NONCLAIM."""
import argparse,base64,dataclasses,json,os,platform,shutil,time,cryptography
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
 save(out/'RUNTIME_DECLARATIONS.json',{'python':platform.python_version(),'platform':platform.platform(),'cryptography':cryptography.__version__,'dependency_installation':'NONE'})
 def call(label,fn):
  v={'label':label,'exchange_start':len(EXCHANGE_LOG),'start_monotonic_ns':time.monotonic_ns()};outcome,result=fn();v.update(outcome=outcome,result=result,exchange_end=len(EXCHANGE_LOG),end_monotonic_ns=time.monotonic_ns());calls.append(v);save(out/'CALLS.json',calls);return outcome
 try:
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
   demand(call('exact_retry',activate)=='OK','EXACT_RETRY_FAILED')
   for name,key in keys.items():c.ctl('final_'+name,0,['get',key.decode(),'--consistency=l'])
   c.ctl('membership',0,['member','list']);c.ctl('final_status',0,['endpoint','status'])
   c.stop(0);demand(c.processes[0].returncode in (0,-15),'UNEXPECTED_STOP');demand(not any(e['action']=='cleanup_forced' for e in c.events),'FORCED_STOP')
   logs=[json.loads(line) for line in (out/'SERVER_0_START_0.txt').read_text().splitlines()]
   demand(any(v.get('msg')=='received signal; shutting down' and v.get('signal')=='terminated' for v in logs),'SIGNAL_HANDLER_NOT_OBSERVED')
   demand(any(v.get('msg')=='closed etcd server' and v.get('data-dir')==str(c.work/'m0') for v in logs),'SERVER_CLOSE_NOT_OBSERVED')
   start=time.monotonic_ns();snapshot=out/'snapshot';snapshot.mkdir();(snapshot/'member').mkdir()
   (snapshot/'member/wal').mkdir();(snapshot/'member/snap').mkdir()
   source_files=sorted((c.work/'m0/member/wal').iterdir());wals=[p for p in source_files if p.suffix=='.wal']
   demand(len(wals)==1 and wals[0].name=='0000000000000000-0000000000000000.wal','INITIAL_SEGMENT_REQUIRED')
   demand(all(p.is_file() and p.suffix in ('.wal','.tmp') for p in source_files),'UNEXPECTED_WAL_DIRECTORY_FILE')
   for p in wals:shutil.copyfile(p,snapshot/'member/wal'/p.name)
   snaps=list((c.work/'m0/member/snap').glob('*.snap'));demand(not snaps,'RAFT_SNAPSHOT_UNSUPPORTED')
   end=time.monotonic_ns();save(out/'SNAPSHOT_BOUNDARY.json',{'mode':'POST_CLEAN_PROCESS_EXIT','start_monotonic_ns':start,'end_monotonic_ns':end,'source':str(c.work/'m0'),'source_wal_directory_names':[p.name for p in source_files],'excluded_preallocated_temporary_files':[p.name for p in source_files if p.suffix=='.tmp'],'raft_snapshot_count':len(snaps),'backend_database_copied':False,'scope':'initial WAL segment; no compaction or recovery test'})
   save(out/'SNAPSHOT_MANIFEST.json',{str(p.relative_to(snapshot)):sha(p) for p in sorted(snapshot.rglob('*')) if p.is_file()})
   status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
 except Exception as e:status['error']=type(e).__name__+': '+str(e)
 finally:save(out/'HTTP_EXCHANGES.json',EXCHANGE_LOG);save(out/'CALLS.json',calls);seal(out,status)
 print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

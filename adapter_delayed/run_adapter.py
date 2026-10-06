"""Two adapter-level pending-completion schedules; existing adapter unchanged."""
import argparse,base64,dataclasses,hashlib,json,os,platform,time,cryptography
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from owned_etcd import OwnedCluster,save,seal,demand,canonical
from transport_fixture import TransportFixture
from atomic_join import BoundRegistryStore
from execution_identity_reference import ExecutionEnvelope,IssuerAuthorization,sign
from lifecycle_registry import RegistrySnapshot,digest_registry
from etcd_lifecycle_adapter import EtcdLifecycleAdapter,Gateway,TestProviderBinding,EXCHANGE_LOG,fixture_authority_state
import stateful_subject as st
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);calls=[]
    status={'status':'INDETERMINATE','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False,'scope':'unchanged adapter; owned request held before upstream submission'}
    context={k:os.environ.get(k) for k in ['GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA']};save(out/'EXECUTION_CONTEXT.json',{'mode':'GITHUB_HOSTED' if context['GITHUB_RUN_ID'] else 'LOCAL_REHEARSAL','provider_declarations':context});save(out/'RUNTIME_DECLARATIONS.json',{'python':platform.python_version(),'platform':platform.platform(),'cryptography':cryptography.__version__,'dependency_installation':'NONE; runner-provided dependency observed'})
    def call(label,fn):
        r={'label':label,'exchange_start':len(EXCHANGE_LOG),'start_monotonic_ns':time.monotonic_ns()};outcome,result=fn();r.update(outcome=outcome,result=result,exchange_end=len(EXCHANGE_LOG),end_monotonic_ns=time.monotonic_ns());calls.append(r);save(out/'CALLS.json',calls);return outcome,result
    try:
        with OwnedCluster(out,1) as c:
            c.ctl('endpoint_before',0,['endpoint','status']);endpoint=json.loads((out/'endpoint_before.json').read_text());header=json.loads(endpoint['stdout'])[0]['Status']['header'];cid=str(header['cluster_id'])
            private=Ed25519PrivateKey.generate();pub=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);issuer=IssuerAuthorization('test-domain','issuer-1','key-1','C1',pub);snapshot=RegistrySnapshot('C1',(issuer,),digest_registry('C1',(issuer,)));store=BoundRegistryStore((snapshot,))
            for label,retry_pending in [('late_commit',False),('retry_pending',True)]:
                prefix='/brains10/adapter-delayed/'+c.work.name+'/'+label
                with TransportFixture(out,label,c.endpoints[0],prefix) as transport:
                    binding=TestProviderBinding(transport.address,'owned-test-etcd',cid,prefix,'C1');gateway=Gateway(binding.endpoint,timeout=1);adapter=EtcdLifecycleAdapter(gateway,binding,store);env=ExecutionEnvelope(label+'-execution','test-domain','issuer-1','key-1','C1','subject-1','config-1','input-1','result-1','runtime-1');signed=sign(private,env);envelope_fp=hashlib.sha256(env.canonical()).hexdigest()
                    keys={'head':adapter.current_key.decode(),'receipt':adapter.receipt_key(label).decode(),'execution':adapter.execution_key(env.execution_id).decode(),'outbox':adapter.effect_key(st.EID(label,'publish',label+'-target')).decode()};save(out/(label+'_FIXTURE.json'),{'binding':dataclasses.asdict(binding),'binding_digest':binding.digest(),'registry_digest':snapshot.digest,'issuer_public_key':pub.hex(),'envelope':json.loads(env.canonical()),'envelope_fingerprint':envelope_fp,'keys':keys,'retry_pending':retry_pending})
                    initial=fixture_authority_state(binding,generation=0,head_digest='HEAD-A',authority_config='C1',lifecycle_generation=7,registry_digest=snapshot.digest).decode();init=f'version({json.dumps(keys["head"])}) = "0"\n\nput {json.dumps(keys["head"])} {json.dumps(initial)}\n\nget {json.dumps(keys["head"])}\n\n';demand(json.loads(c.ctl(label+'_initialize',0,['txn'],init)['stdout']).get('succeeded') is True,'NAMESPACE_REUSED')
                    def activate():return adapter.activate(challenge=(label+'-challenge').encode(),expected_generation=0,expected_head_digest='HEAD-A',successor_head_digest='HEAD-B',transition_id=label,signed=signed,effects=(('publish',label+'-target',label+'-payload'),))
                    transport.arm();outcome,ident=call(label+':initial_activation',activate);demand(outcome=='UNKNOWN_COMMIT' and transport.accepted.is_set() and not transport.completed.is_set(),'REAL_PENDING_TIMEOUT_REQUIRED')
                    def reconcile():return adapter.reconcile(ident['transition_id'],ident['fingerprint'],env.execution_id,envelope_fp)
                    demand(call(label+':before_reconcile',reconcile)[0]=='UNKNOWN_COMMIT','ABSENT_MUST_STAY_UNKNOWN')
                    for name,key in keys.items():
                        d=json.loads(c.ctl(label+'_before_'+name,0,['get',key,'--consistency=l'])['stdout']);demand(bool(d.get('kvs')) if name=='head' else not d.get('kvs'),'PENDING_STATE_CHANGED')
                    transport.event('absence_verified')
                    if retry_pending:
                        demand(call(label+':pending_exact_retry',activate)[0]=='OK','PENDING_RETRY_FAILED');transport.event('pending_retry_committed')
                        for name,key in keys.items():c.ctl(label+'_pending_retry_'+name,0,['get',key,'--consistency=l'])
                    transport.resume();demand(transport.completed.wait(5),'HELD_REQUEST_INCOMPLETE')
                    demand(call(label+':after_reconcile',reconcile)[0]=='OK','RECONCILIATION_FAILED')
                    for name,key in keys.items():c.ctl(label+'_after_'+name,0,['get',key,'--consistency=l'])
                    demand(call(label+':final_exact_retry',activate)[0]=='OK','FINAL_REPLAY_FAILED')
                    for name,key in keys.items():c.ctl(label+'_final_'+name,0,['get',key,'--consistency=l'])
            c.ctl('endpoint_after',0,['endpoint','status']);status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
    except Exception as e:status['error']=type(e).__name__+': '+str(e)
    finally:save(out/'HTTP_EXCHANGES.json',EXCHANGE_LOG);save(out/'CALLS.json',calls);seal(out,status)
    print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

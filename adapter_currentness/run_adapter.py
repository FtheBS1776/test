"""Unchanged bounded adapter under owned follower currentness unavailability."""
import argparse,base64,dataclasses,json,os,time,platform,cryptography
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from owned_etcd import canonical,demand,save,seal
from peer_fixture import PeerFixture
from atomic_join import BoundRegistryStore
from execution_identity_reference import ExecutionEnvelope,IssuerAuthorization,sign
from lifecycle_registry import RegistrySnapshot,digest_registry
from etcd_lifecycle_adapter import EtcdLifecycleAdapter,Gateway,TestProviderBinding,EXCHANGE_LOG,fixture_authority_state
import stateful_subject as st
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args()
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);calls=[]
    status={'status':'INDETERMINATE','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False,'scope':'unchanged bounded adapter; same-host three-member follower currentness unavailable'}
    context={k:os.environ.get(k) for k in ['GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA']};save(out/'EXECUTION_CONTEXT.json',{'mode':'GITHUB_HOSTED' if context['GITHUB_RUN_ID'] else 'LOCAL_REHEARSAL','provider_declarations':context})
    save(out/'RUNTIME_DECLARATIONS.json',{'python':platform.python_version(),'platform':platform.platform(),'cryptography':cryptography.__version__,'dependency_installation':'NONE; runner-provided dependency observed'})
    def call(label,fn):
        r={'label':label,'exchange_start':len(EXCHANGE_LOG),'start_monotonic_ns':time.monotonic_ns()};outcome,result=fn();r.update(outcome=outcome,exchange_end=len(EXCHANGE_LOG),end_monotonic_ns=time.monotonic_ns())
        if dataclasses.is_dataclass(result):
            result=dataclasses.asdict(result);result['challenge']=result['challenge'].hex();result['raw_value']=result['raw_value'].decode()
        r['result']=result;calls.append(r);save(out/'CALLS.json',calls);return outcome,result
    try:
        with PeerFixture(out) as c:
            statuses=[json.loads(c.ctl(f'baseline_status_{i}',i,['endpoint','status'])['stdout'])[0]['Status'] for i in range(3)]
            ids=[s['header']['member_id'] for s in statuses];leaders={s['leader'] for s in statuses};clusters={s['header']['cluster_id'] for s in statuses};demand(len(leaders)==len(clusters)==1 and len(set(ids))==3,'BASELINE_IDENTITIES')
            leader=ids.index(next(iter(leaders)));follower=next(i for i in range(3) if i!=leader);majority=[i for i in range(3) if i!=follower]
            c.ctl('membership_before',leader,['member','list'])
            private=Ed25519PrivateKey.generate();pub=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
            issuer=IssuerAuthorization('test-domain','issuer-1','key-1','C1',pub);snapshot=RegistrySnapshot('C1',(issuer,),digest_registry('C1',(issuer,)));store=BoundRegistryStore((snapshot,))
            binding=TestProviderBinding(c.endpoints[follower],'owned-test-etcd',str(next(iter(clusters))),'/brains10/adapter-currentness/'+c.work.name,'C1');gateway=Gateway(binding.endpoint,timeout=2);adapter=EtcdLifecycleAdapter(gateway,binding,store)
            save(out/'FIXTURE_BINDING.json',{'binding':dataclasses.asdict(binding),'binding_digest':binding.digest(),'registry_digest':snapshot.digest,'issuer_public_key':pub.hex(),'follower_index':follower,'leader_index':leader,'member_ids':[str(i) for i in ids],'cluster_id':binding.cluster_id,'majority_indices':majority,'adapter_endpoint_unchanged':True})
            initial=fixture_authority_state(binding,generation=0,head_digest='HEAD-A',authority_config='C1',lifecycle_generation=7,registry_digest=snapshot.digest)
            init_script=f'version({json.dumps(adapter.current_key.decode())}) = "0"\n\nput {json.dumps(adapter.current_key.decode())} {json.dumps(initial.decode())}\n\nget {json.dumps(adapter.current_key.decode())}\n\n'
            demand(json.loads(c.ctl('initialize',leader,['txn'],init_script)['stdout']).get('succeeded') is True,'NAMESPACE_REUSED')
            def signed(eid):return sign(private,ExecutionEnvelope(eid,'test-domain','issuer-1','key-1','C1','subject-1','config-1','input-1','result-1','runtime-1'))
            def activate(label,gen,parent,succ):
                return call(label,lambda:adapter.activate(challenge=(label+'-challenge').encode(),expected_generation=gen,expected_head_digest=parent,successor_head_digest=succ,transition_id=label,signed=signed(label+'-execution'),effects=(('publish',label+'-target',label+'-payload'),)))
            def keys(label):return [('head',adapter.current_key),('receipt',adapter.receipt_key(label)),('execution',adapter.execution_key(label+'-execution')),('outbox',adapter.effect_key(st.EID(label,'publish',label+'-target')))]
            keymap={label:{name:key.decode() for name,key in keys(label)} for label in ['baseline_activation','rejected_activation','healed_activation']};save(out/'KEYS.json',keymap)
            demand(activate('baseline_activation',0,'HEAD-A','HEAD-B')[0]=='OK','BASELINE_ACTIVATION_FAILED')
            for name,key in keys('baseline_activation'):c.ctl('baseline_'+name,follower,['get',key.decode(),'--consistency=l'])
            for i in range(3):c.ctl(f'before_isolation_head_{i}',i,['get',adapter.current_key.decode(),'--consistency=l'])
            base=json.loads((out/'baseline_head.json').read_text());kv=json.loads(base['stdout'])['kvs'][0];old=base64.b64decode(kv['value']).decode();new_state=json.loads(old);new_state.update(generation=2,head_digest='HEAD-C');new=canonical(new_state)
            fixture_script=f'mod({json.dumps(adapter.current_key.decode())}) = "{kv["mod_revision"]}"\nvalue({json.dumps(adapter.current_key.decode())}) = {json.dumps(old)}\n\nput {json.dumps(adapter.current_key.decode())} {json.dumps(new)}\n\nget {json.dumps(adapter.current_key.decode())}\n\n'
            save(out/'FIXTURE_ONLY_HEAD_CHANGE.json',{'classification':'TEST_SETUP_ONLY','integrated_activation':False,'old_value':old,'new_value':new,'stdin':fixture_script})
            c.network.isolate(follower,ids);demand(json.loads(c.ctl('fixture_majority_change',leader,['txn'],fixture_script)['stdout']).get('succeeded') is True,'MAJORITY_FIXTURE_WRITE_FAILED')
            for i in majority:c.ctl(f'majority_before_head_{i}',i,['get',adapter.current_key.decode(),'--consistency=l'])
            d=json.loads(c.ctl('isolated_serializable',follower,['get',adapter.current_key.decode(),'--consistency=s'])['stdout']);demand(base64.b64decode(d['kvs'][0]['value']).decode()==old,'ACTUAL_STALE_VALUE_NOT_OBSERVED')
            demand(call('isolated_read',lambda:adapter.read_current(b'isolated-challenge','C1'))[0]=='UNAVAILABLE','ISOLATED_CURRENT_READ_NOT_UNAVAILABLE')
            demand(activate('rejected_activation',1,'HEAD-B','HEAD-D')[0]=='UNAVAILABLE','ISOLATED_ACTIVATION_NOT_UNAVAILABLE')
            save(out/'AUTHORITY_DECISION.json',{'decision':'HOLD','diagnostic_used_for_authority':False,'inputs':['isolated_read','rejected_activation']})
            for name,key in keys('rejected_activation'):
                rec=c.ctl('rejected_'+name,leader,['get',key.decode(),'--consistency=l']);d=json.loads(rec['stdout']);demand(bool(d.get('kvs')) if name=='head' else not d.get('kvs'),'REJECTED_PATH_WRITE')
            for i in majority:c.ctl(f'majority_after_head_{i}',i,['get',adapter.current_key.decode(),'--consistency=l'])
            c.network.heal();c.wait_healthy(range(3),'healed')
            demand(call('healed_read',lambda:adapter.read_current(b'healed-challenge','C1'))[0]=='CURRENT','HEALED_READ_FAILED')
            demand(activate('healed_activation',2,'HEAD-C','HEAD-D')[0]=='OK','HEALED_ACTIVATION_FAILED')
            for name,key in keys('healed_activation'):c.ctl('healed_'+name,follower,['get',key.decode(),'--consistency=l'])
            demand(activate('healed_activation',2,'HEAD-C','HEAD-D')[0]=='OK','EXACT_REPLAY_FAILED')
            calls[-1]['label']='healed_exact_retry';save(out/'CALLS.json',calls)
            for name,key in keys('healed_activation'):c.ctl('final_'+name,follower,['get',key.decode(),'--consistency=l'])
            for i in range(3):c.ctl(f'final_status_{i}',i,['endpoint','status']);c.ctl(f'final_head_{i}',i,['get',adapter.current_key.decode(),'--consistency=l'])
            c.ctl('membership_after',leader,['member','list']);status['status']='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION'
    except Exception as e:status['error']=type(e).__name__+': '+str(e)
    finally:save(out/'HTTP_EXCHANGES.json',EXCHANGE_LOG);save(out/'CALLS.json',calls);seal(out,status)
    print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

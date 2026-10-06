"""Actual older serializable value on an isolated live follower, ordinary owned fixture."""
import argparse,base64,json,os
from pathlib import Path
from owned_etcd import canonical,demand,save,seal
from peer_fixture import PeerFixture
from gate_inputs import build_init_script,build_txn_script
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    status={'status':'INDETERMINATE','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False,'scope':'same-host three-member peer-relay isolation; serializable stale read'}
    context={k:os.environ.get(k) for k in ['GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA']}
    save(out/'EXECUTION_CONTEXT.json',{'mode':'GITHUB_HOSTED' if context['GITHUB_RUN_ID'] else 'LOCAL_REHEARSAL','provider_declarations':context})
    try:
        with PeerFixture(out) as cluster:
            def endpoint(label,index):return json.loads(cluster.ctl(label,index,['endpoint','status'])['stdout'])[0]['Status']
            baseline=[endpoint(f'baseline_status_{i}',i) for i in range(3)];ids=[r['header']['member_id'] for r in baseline];leaders={r['leader'] for r in baseline};clusters={r['header']['cluster_id'] for r in baseline}
            demand(len(leaders)==len(clusters)==1 and 0 not in leaders and len(set(ids))==3,'BASELINE_IDENTITIES')
            leader=ids.index(next(iter(leaders)));follower=next(i for i in range(3) if i!=leader);majority=[i for i in range(3) if i!=follower]
            cluster.ctl('membership_before',leader,['member','list'])
            prefix='/brains10/stale/'+cluster.work.name;head=prefix+'/head';receipt_key=prefix+'/tx/T1'
            state=lambda gen:canonical({'generation':gen,'digest':f'G{gen}','authority_config':'C0','lifecycle_generation':0,'registry_digest':'R0'})
            parent=state(0);successor=state(1)
            init=json.loads(cluster.ctl('initialize',leader,['txn'],build_init_script(head,receipt_key,parent))['stdout']);demand(init.get('succeeded') is True,'NAMESPACE_REUSED')
            for i in range(3):cluster.ctl(f'initial_head_{i}',i,['get',head,'--consistency=l'])
            initial=json.loads((out/f'initial_head_{leader}.json').read_text());kv=json.loads(initial['stdout'])['kvs'][0]
            request={'head_key':head,'transition_id':receipt_key,'expected_parent':parent,'expected_revision':str(kv['mod_revision']),'successor':successor,'authority_config':'C0'}
            receipt=canonical({'request':request,'result':successor})
            script=f'mod({json.dumps(head)}) = "{request["expected_revision"]}"\nversion({json.dumps(receipt_key)}) = "0"\n'+build_txn_script(head,receipt_key,parent,successor,receipt)
            save(out/'REQUEST.json',{'request':request,'receipt':receipt,'transaction_stdin':script})
            cluster.network.isolate(follower,ids)
            txn=json.loads(cluster.ctl('majority_transition',leader,['txn'],script)['stdout']);demand(txn.get('succeeded') is True,'MAJORITY_NOT_COMMITTED')
            for i in majority:
                cluster.ctl(f'majority_head_{i}',i,['get',head,'--consistency=l']);cluster.ctl(f'majority_receipt_{i}',i,['get',receipt_key,'--consistency=l'])
            serial=cluster.ctl('isolated_serializable',follower,['get',head,'--consistency=s']);data=json.loads(serial['stdout'])
            demand(len(data.get('kvs',[]))==1 and base64.b64decode(data['kvs'][0]['value']).decode()==parent,'ACTUAL_STALE_VALUE_NOT_OBSERVED')
            linear=cluster.ctl('isolated_linearizable',follower,['get',head,'--consistency=l'],checked=False);demand(linear['returncode']!=0,'ISOLATED_NORMAL_READ_SUCCEEDED')
            save(out/'AUTHORITY_DECISION.json',{'authority_decision':'HOLD','diagnostic_used_for_authority':False,'inputs':['isolated_linearizable.json'],'diagnostic_record':'isolated_serializable.json'})
            cluster.network.heal();cluster.wait_healthy(range(3),'healed')
            healed=[endpoint(f'healed_status_{i}',i) for i in range(3)]
            demand(all(r['header']['cluster_id']==next(iter(clusters)) and r['header']['member_id']==ids[i] for i,r in enumerate(healed)),'HEALED_IDENTITIES_CHANGED')
            cluster.ctl('membership_after',leader,['member','list'])
            for i in range(3):cluster.ctl(f'healed_head_{i}',i,['get',head,'--consistency=l']);cluster.ctl(f'healed_receipt_{i}',i,['get',receipt_key,'--consistency=l'])
            retry=json.loads(cluster.ctl('exact_retry',leader,['txn'],script)['stdout']);demand(not retry.get('succeeded',False),'RETRY_WROTE_AGAIN')
            cluster.ctl('final_head',leader,['get',head,'--consistency=l']);cluster.ctl('final_receipt',leader,['get',receipt_key,'--consistency=l'])
            status.update(status='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION',cluster_id=str(next(iter(clusters))),member_ids=[str(value) for value in ids],leader_index=leader,isolated_follower_index=follower,majority_indices=majority)
    except Exception as e:status['error']=type(e).__name__+': '+str(e)
    finally:seal(out,status)
    print(json.dumps(status));return 0 if status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

"""Read-only offline adjudication. No driver imports or network activity."""
import base64,hashlib,json,pathlib,sys
PINS={'etcd':'030b4b2efd1bcc9ab043080c35f7bb68551e962b23efe62e2f2713429bd9e0f2','etcdctl':'18416269c49d0f25624938b0b45d5bd5d3eb980ab92048dc4652c66a4246141e'}
def check(v,label):
    if not v:raise ValueError(label)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def verify(root):
    root=pathlib.Path(root)
    def load(name):return json.loads((root/name).read_text())
    inventory={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!='EVIDENCE_MANIFEST.json'}
    check(inventory==load('EVIDENCE_MANIFEST.json'),'MANIFEST')
    status=load('STATUS.json');check(status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' and status['classification']=='NONCLAIM' and status['controlling_pass']==186 and status['promotion'] is False and status['freeze'] is False,'STATUS')
    identity=load('IDENTITY.json');check(identity['binary_sha256']==PINS,'BINARY_PINS')
    for name,h in identity['sources'].items():check(inventory.get(name)==h,'SOURCE_IDENTITY')
    cfg=load('CONFIGURATION.json');check(cfg['members']==3 and cfg['tls'] is False,'CONFIGURATION')
    for group in ['endpoints','advertised_peers']:
        check(len(cfg[group])==3 and len(set(cfg[group]))==3 and all(u.startswith('http://127.0.0.1:') and u.rsplit(':',1)[1].isdigit() for u in cfg[group]),'OWNED_LOOPBACK')
    backends=cfg['peer_backends'];check(len(backends)==3 and len({tuple(b) for b in backends})==3 and all(len(b)==2 and b[0]=='127.0.0.1' and isinstance(b[1],int) and 0<b[1]<65536 for b in backends),'OWNED_BACKENDS')
    cid=int(status['cluster_id']);ids=list(map(int,status['member_ids']));leader=status['leader_index'];follower=status['isolated_follower_index'];majority=status['majority_indices']
    check(len(set(ids))==3 and sorted(majority+[follower])==[0,1,2] and follower!=leader and leader in majority,'MEMBERS')
    def rec(name,i,args,ok=True):
        r=load(name+'.json');a=r['argv'];check(pathlib.Path(a[0]).name=='etcdctl' and a[1:]==['--endpoints='+cfg['endpoints'][i],'--command-timeout=2s','--dial-timeout=1s','--write-out=json']+args,'EXACT_COMMAND_'+name)
        check(r['start_monotonic_ns']<r['end_monotonic_ns'],'TIME_'+name)
        if ok:check(r['returncode']==0,'RETURN_'+name)
        return r
    def response(r,i):
        d=json.loads(r['stdout']);h=d['header'];check(h['cluster_id']==cid and h['member_id']==ids[i],'RESPONSE_IDENTITY');return d
    for phase in ['baseline','healed']:
        for i in range(3):
            r=rec(f'{phase}_status_{i}',i,['endpoint','status']);d=json.loads(r['stdout']);check(len(d)==1 and d[0]['Endpoint']==cfg['endpoints'][i],'STATUS_ENDPOINT')
            s=d[0]['Status'];check(s['header']['cluster_id']==cid and s['header']['member_id']==ids[i],'STATUS_IDENTITIES')
            if phase=='baseline':check(s['leader']==ids[leader],'LEADER')
    before=response(rec('membership_before',leader,['member','list']),leader);after=response(rec('membership_after',leader,['member','list']),leader)
    check(before['members']==after['members'] and {m['ID'] for m in before['members']}==set(ids),'MEMBERSHIP_UNCHANGED')
    request_record=load('REQUEST.json');q=request_record['request'];head=q['head_key'];receipt_key=q['transition_id'];parent=canonical({'authority_config':'C0','digest':'G0','generation':0,'lifecycle_generation':0,'registry_digest':'R0'});successor=canonical({'authority_config':'C0','digest':'G1','generation':1,'lifecycle_generation':0,'registry_digest':'R0'})
    check(head.startswith('/brains10/stale/') and head.endswith('/head') and receipt_key==head[:-5]+'/tx/T1','KEYS')
    check(q=={'head_key':head,'transition_id':receipt_key,'expected_parent':parent,'expected_revision':'2','successor':successor,'authority_config':'C0'},'FULL_REQUEST')
    receipt=canonical({'request':q,'result':successor});check(request_record['receipt']==receipt,'FULL_RECEIPT')
    j=json.dumps
    init_script=f'version({j(head)}) = "0"\nversion({j(receipt_key)}) = "0"\n\nput {j(head)} {j(parent)}\n\nget {j(head)}\nget {j(receipt_key)}\n\n'
    script=f'mod({j(head)}) = "2"\nversion({j(receipt_key)}) = "0"\nvalue({j(head)}) = {j(parent)}\n\nput {j(head)} {j(successor)}\nput {j(receipt_key)} {j(receipt)}\n\nget {j(head)}\n\n'
    init=rec('initialize',leader,['txn']);check(init['stdin']==init_script and response(init,leader)['succeeded'] is True,'INITIALIZATION')
    check(request_record['transaction_stdin']==script,'EXACT_TRANSACTION')
    def get(name,i,key,value,create,mod,version,mode='l'):
        r=rec(name,i,['get',key,'--consistency='+mode]);check(r['stdin'] is None,'NO_STDIN');d=response(r,i);check(d['count']==1 and len(d['kvs'])==1,'SINGLE_KEY')
        kv=d['kvs'][0];check(kv=={'key':base64.b64encode(key.encode()).decode(),'value':base64.b64encode(value.encode()).decode(),'create_revision':create,'mod_revision':mod,'version':version},'FULL_KEY_RECORD_'+name);check(d['header']['revision']>=mod,'HEADER_REVISION');return r
    initial=[get(f'initial_head_{i}',i,head,parent,2,2,1) for i in range(3)]
    transition=rec('majority_transition',leader,['txn']);td=response(transition,leader)
    check(transition['stdin']==script and td['succeeded'] is True and td['header']['revision']==3 and len(td['responses'])==2 and all(r['Response']['response_put']['header']['revision']==3 for r in td['responses']),'ATOMIC_TRANSITION')
    peers=load('PEER_EVENTS.json');isolates=[e for e in peers if e['event']=='isolate'];heals=[e for e in peers if e['event']=='heal'];clean=[e for e in peers if e['event']=='relay_cleanup']
    check(len(isolates)==len(heals)==len(clean)==1,'RELAY_EVENTS');isolate=isolates[0];heal=heals[0]
    check(isolate['member_index']==follower and isolate['member_ids_hex']==[format(i,'x') for i in ids] and isolate['closed_connections'],'ISOLATION_IDENTITY')
    check(max(r['end_monotonic_ns'] for r in initial)<isolate['monotonic_ns']<transition['start_monotonic_ns'],'ISOLATION_ORDER')
    majority_reads=[]
    for i in majority:
        majority_reads.extend([get(f'majority_head_{i}',i,head,successor,2,3,2),get(f'majority_receipt_{i}',i,receipt_key,receipt,3,3,1)])
    stale=get('isolated_serializable',follower,head,parent,2,2,1,'s')
    check(transition['end_monotonic_ns']<min(r['start_monotonic_ns'] for r in majority_reads) and max(r['end_monotonic_ns'] for r in majority_reads)<stale['start_monotonic_ns'],'ACTUAL_STALE_AFTER_COMMIT')
    unavailable=rec('isolated_linearizable',follower,['get',head,'--consistency=l'],False)
    check(unavailable['returncode']!=0 and unavailable['stdout']=='' and 'context deadline exceeded' in unavailable['stderr'] and not unavailable.get('harness_timeout'),'NORMAL_READ_UNAVAILABLE')
    check(stale['end_monotonic_ns']<unavailable['start_monotonic_ns']<unavailable['end_monotonic_ns']<heal['monotonic_ns'],'HEAL_ORDER')
    check(load('AUTHORITY_DECISION.json')=={'authority_decision':'HOLD','diagnostic_used_for_authority':False,'inputs':['isolated_linearizable.json'],'diagnostic_record':'isolated_serializable.json'},'FAIL_CLOSED_AUTHORITY')
    selected=format(ids[follower],'x');blocked=[e for e in peers if e['event']=='blocked' and isolate['monotonic_ns']<e['monotonic_ns']<heal['monotonic_ns']]
    check(any(e['source']==selected for e in blocked) and any(e['destination']==follower for e in blocked),'BOTH_DIRECTIONS_OBSERVED')
    for e in peers:
        if e['event']=='connected' and isolate['monotonic_ns']<e['monotonic_ns']<heal['monotonic_ns']:check(e['source'] in isolate['member_ids_hex'] and e['source']!=selected and e['destination']!=follower,'NO_ISOLATED_RECONNECT')
    for i in range(3):
        for name,key,value,create,version in [(f'healed_head_{i}',head,successor,2,2),(f'healed_receipt_{i}',receipt_key,receipt,3,1)]:check(get(name,i,key,value,create,3,version)['start_monotonic_ns']>heal['monotonic_ns'],'HEALED_READ_ORDER')
    retry=rec('exact_retry',leader,['txn']);rd=response(retry,leader);check(retry['stdin']==script and rd.get('succeeded',False) is False and rd['header']['revision']==3 and len(rd['responses'])==1 and 'response_range' in rd['responses'][0]['Response'],'RETRY_NO_WRITE')
    for name,key,value,create,version in [('final_head',head,successor,2,2),('final_receipt',receipt_key,receipt,3,1)]:check(get(name,leader,key,value,create,3,version)['start_monotonic_ns']>retry['end_monotonic_ns'],'FINAL_ORDER')
    events=load('PROCESS_EVENTS.json');starts=[e for e in events if e['action']=='start'];exits=[e for e in events if e['action']=='exit']
    check(len(starts)==len(exits)==3 and {e['member_index'] for e in starts}=={0,1,2} and all(e['start_number']==0 for e in starts),'NO_RESTART')
    for s in starts:check(any(e['pid']==s['pid'] and e['member_index']==s['member_index'] and e['monotonic_ns']>retry['end_monotonic_ns'] for e in exits),'OWNED_CLEANUP')
    check(clean[0]['active_connections']==0 and clean[0]['live_threads']==0 and clean[0]['overflow'] is False,'RELAY_CLEANUP')
    return {'verification':'PASS','classification':'NONCLAIM','controlling_pass':186,'scope':'same-host owned three-member stale serializable observation; unavailable normal read yields HOLD; heal and exact retry','evidence_files':len(inventory),'promotion':False,'freeze':False}
if __name__=='__main__':
    try:print(json.dumps(verify(sys.argv[1]),sort_keys=True))
    except Exception as e:print(json.dumps({'verification':'REJECTED','error':type(e).__name__+': '+str(e)}));raise SystemExit(2)

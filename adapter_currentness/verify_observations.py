"""Read-only offline verifier; no subject imports, execution or network access."""
import base64,hashlib,json,pathlib,sys
PINS={'etcd':'030b4b2efd1bcc9ab043080c35f7bb68551e962b23efe62e2f2713429bd9e0f2','etcdctl':'18416269c49d0f25624938b0b45d5bd5d3eb980ab92048dc4652c66a4246141e'}
def need(v,label):
    if not v:raise ValueError(label)
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def enc(s):return base64.b64encode(s.encode()).decode()
def dec(s):return base64.b64decode(s,validate=True).decode()
def digest(parts):return hashlib.sha256(json.dumps(parts,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def verify(root):
    root=pathlib.Path(root)
    def load(n):return json.loads((root/(n+'.json')).read_text())
    inventory={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!='EVIDENCE_MANIFEST.json'}
    need(inventory==load('EVIDENCE_MANIFEST'),'INVENTORY');s=load('STATUS');need(s['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION' and s['classification']=='NONCLAIM' and s['controlling_pass']==186 and s['promotion'] is s['freeze'] is False,'STATUS')
    ident=load('IDENTITY');need(ident['binary_sha256']==PINS and all(inventory[n]==h for n,h in ident['sources'].items()),'IDENTITIES')
    cfg=load('CONFIGURATION');need(cfg['members']==3 and cfg['tls'] is False and len(set(cfg['endpoints']))==3 and all(u.startswith('http://127.0.0.1:') for u in cfg['endpoints']),'OWNED_CONFIG')
    b=load('FIXTURE_BINDING');f=b['follower_index'];leader=b['leader_index'];ids=list(map(int,b['member_ids']));cid=int(b['cluster_id']);majority=b['majority_indices'];binding=b['binding'];need(sorted(majority+[f])==[0,1,2] and leader in majority and f!=leader and len(set(ids))==3,'TOPOLOGY')
    need(binding['endpoint']==cfg['endpoints'][f] and binding['cluster_id']==str(cid) and binding['tls'] is False and binding['auth_mode']=='none' and binding['adapter_version']=='pass219-etcd-nonclaim-v1' and binding['authority_config']=='C1' and b['adapter_endpoint_unchanged'] is True,'FIXED_BINDING')
    need(hashlib.sha256(canon(binding).encode()).hexdigest()==b['binding_digest'],'BINDING_DIGEST')
    rd=digest(['registry-v1','C1',[['test-domain','issuer-1','key-1','C1',b['issuer_public_key']]]]);need(rd==b['registry_digest'],'REGISTRY_DIGEST')
    def state(gen,head):return {'generation':gen,'head_digest':head,'authority_config':'C1','lifecycle_generation':7,'registry_digest':rd,'provider_binding_digest':b['binding_digest']}
    states=[state(0,'HEAD-A'),state(1,'HEAD-B'),state(2,'HEAD-C'),state(3,'HEAD-D')];keys=load('KEYS');prefix=binding['namespace'];headkey=prefix+'/authority-current'
    for label in ['baseline_activation','rejected_activation','healed_activation']:
        eid=digest(['effect-v1',label,'publish',label+'-target']);need(keys[label]=={'head':headkey,'receipt':prefix+'/transition/'+label,'execution':prefix+'/execution/'+label+'-execution','outbox':prefix+'/outbox/'+eid},'KEY_DOMAINS')
    def command(name,i,args):
        r=load(name);need(pathlib.Path(r['argv'][0]).name=='etcdctl' and r['argv'][1:]==['--endpoints='+cfg['endpoints'][i],'--command-timeout=2s','--dial-timeout=1s','--write-out=json']+args and r['returncode']==0 and r['start_monotonic_ns']<r['end_monotonic_ns'],'EXACT_COMMAND_'+name);return r
    def response(r,i):
        d=json.loads(r['stdout']);need(d['header']['cluster_id']==cid and d['header']['member_id']==ids[i],'RESPONSE_MEMBER');return d
    def read(name,i,key,value=None,revision=None,version=None,create=None,mode='l'):
        r=command(name,i,['get',key,'--consistency='+mode]);d=response(r,i)
        if value is None:need(not d.get('kvs') and d.get('count',0)==0,'ABSENT_'+name)
        else:
            need(d['count']==1 and len(d['kvs'])==1,'EXACT_KEY');kv=d['kvs'][0];need(kv=={'key':enc(key),'value':enc(value),'mod_revision':revision,'create_revision':create,'version':version},'KEY_METADATA_'+name)
        return r,d
    for phase in ['baseline','final']:
        for i in range(3):
            r=command(f'{phase}_status_{i}',i,['endpoint','status']);d=json.loads(r['stdout']);need(len(d)==1 and d[0]['Endpoint']==cfg['endpoints'][i],'ENDPOINT');h=d[0]['Status']['header'];need(h['cluster_id']==cid and h['member_id']==ids[i],'UNCHANGED_IDENTITIES')
            if phase=='baseline':need(d[0]['Status']['leader']==ids[leader],'LEADER')
    before=response(command('membership_before',leader,['member','list']),leader);after=response(command('membership_after',leader,['member','list']),leader);need(before['members']==after['members'] and {m['ID'] for m in before['members']}==set(ids),'MEMBERSHIP')
    init=command('initialize',leader,['txn']);jd=json.dumps;expected_init=f'version({jd(headkey)}) = "0"\n\nput {jd(headkey)} {jd(canon(states[0]))}\n\nget {jd(headkey)}\n\n';need(init['stdin']==expected_init and response(init,leader)['succeeded'] is True,'INIT')
    calls=load('CALLS');labels=['baseline_activation','isolated_read','rejected_activation','healed_read','healed_activation','healed_exact_retry'];need([c['label'] for c in calls]==labels,'CALL_SEQUENCE');exchanges=load('HTTP_EXCHANGES');cursor=0
    for c in calls:
        need(c['exchange_start']==cursor and c['start_monotonic_ns']<c['end_monotonic_ns'],'CALL_BOUNDS');cursor=c['exchange_end'];need(cursor<=len(exchanges),'EXCHANGE_BOUNDS')
    need(cursor==len(exchanges),'COMPLETE_EXCHANGES')
    def chunk(label):
        c=calls[labels.index(label)];return c,exchanges[c['exchange_start']:c['exchange_end']]
    def check_range(e,key,success=True):
        need(e['path']=='/v3/kv/range' and json.loads(dec(e['request_b64']))=={'key':enc(key),'serializable':False} and e['authorization_present'] is False,'CURRENT_RANGE_ONLY')
        if success:
            need(e['transport_error'] is None and e['response_b64'] is not None,'RANGE_COMPLETED');d=json.loads(dec(e['response_b64']));need(d['header']['cluster_id']==str(cid) and d['header']['member_id']==str(ids[f]),'GATEWAY_IDENTITY');return d
        need(e['response_b64'] is None and e['transport_error'] in ['TimeoutError','HTTP_STATUS_504','URLError'],'ACTUAL_READ_UNAVAILABLE')
    def records(label,parentgen,parenthead,successorgen,successorhead):
        eid=label+'-execution';effect=digest(['effect-v1',label,'publish',label+'-target']);envelope={'domain':'BRAINS10/EXECUTION-ENVELOPE/v1','execution_id':eid,'trust_domain':'test-domain','issuer_id':'issuer-1','key_id':'key-1','authority_config':'C1','subject_digest':'subject-1','config_digest':'config-1','input_digest':'input-1','result_digest':'result-1','runtime_id':'runtime-1'};efp=hashlib.sha256(canon(envelope).encode()).hexdigest();effects=[['publish',label+'-target',label+'-payload']];fp=digest(['tx-v1',str(parentgen),parenthead,successorhead,label,'C1',json.dumps(effects,separators=(',',':'))]);result={'generation':successorgen,'head_digest':successorhead,'authority_config':'C1'}
        return {'head':canon(state(successorgen,successorhead)),'receipt':canon({'transition_id':label,'fingerprint':fp,'execution_id':eid,'envelope_fingerprint':efp,'result':result}),'execution':canon({'execution_id':eid,'envelope_fingerprint':efp,'transition_id':label}),'outbox':canon({'effect_id':effect,'transition_id':label,'kind':'publish','target':label+'-target','payload':label+'-payload','generation':successorgen,'authority_config':'C1'})},result
    for label,pg,ph,ng,nh,parentrev,writerev in [('baseline_activation',0,'HEAD-A',1,'HEAD-B',2,3),('healed_activation',2,'HEAD-C',3,'HEAD-D',4,5)]:
        c,es=chunk(label);vals,result=records(label,pg,ph,ng,nh);need(c['outcome']=='OK' and c['result']==result and len(es)==3,'ACTIVATION_OUTCOME');current=check_range(es[0],headkey);need(dec(current['kvs'][0]['value'])==canon(state(pg,ph)) and int(current['kvs'][0]['mod_revision'])==parentrev,'CURRENT_PARENT');absent=check_range(es[1],keys[label]['receipt']);need(not absent.get('kvs'),'NO_PRIOR_RECEIPT')
        tx=es[2];body=json.loads(dec(tx['request_b64']));compares=[{'key':enc(headkey),'target':'MOD','result':'EQUAL','modRevision':str(parentrev)},{'key':enc(headkey),'target':'VALUE','result':'EQUAL','value':enc(canon(state(pg,ph)))}]+[{'key':enc(keys[label][n]),'target':'VERSION','result':'EQUAL','version':'0'} for n in ['receipt','execution','outbox']];writes=[{'requestPut':{'key':enc(keys[label][n]),'value':enc(vals[n])}} for n in ['head','receipt','execution','outbox']]
        need(tx['path']=='/v3/kv/txn' and body=={'compare':compares,'success':writes,'failure':[]} and tx['transport_error'] is None and tx['response_b64'] is not None,'EXACT_ATOMIC_TXN');d=json.loads(dec(tx['response_b64']));need(d['header']['cluster_id']==str(cid) and d['header']['member_id']==str(ids[f]) and d['succeeded'] is True and int(d['header']['revision'])==writerev and len(d['responses'])==4 and all(int(x['response_put']['header']['revision'])==writerev for x in d['responses']),'SHARED_WRITE_REVISION')
        for n in vals:read(('baseline_' if pg==0 else 'healed_')+n,f,keys[label][n],vals[n],writerev,2 if pg==0 and n=='head' else 4 if n=='head' else 1,2 if n=='head' else writerev)
    pre=[read(f'before_isolation_head_{i}',i,headkey,canon(states[1]),3,2,2)[0] for i in range(3)];peers=load('PEER_EVENTS');iso=[e for e in peers if e['event']=='isolate'];heal=[e for e in peers if e['event']=='heal'];clean=[e for e in peers if e['event']=='relay_cleanup'];need(len(iso)==len(heal)==len(clean)==1,'PEER_EVENTS');iso=iso[0];heal=heal[0];need(iso['member_index']==f and iso['member_ids_hex']==[format(i,'x') for i in ids] and iso['closed_connections'] and max(x['end_monotonic_ns'] for x in pre)<iso['monotonic_ns'],'ISOLATE')
    fixture=load('FIXTURE_ONLY_HEAD_CHANGE');need(fixture['classification']=='TEST_SETUP_ONLY' and fixture['integrated_activation'] is False and fixture['old_value']==canon(states[1]) and fixture['new_value']==canon(states[2]),'FIXTURE_SCOPE');script=f'mod({jd(headkey)}) = "3"\nvalue({jd(headkey)}) = {jd(canon(states[1]))}\n\nput {jd(headkey)} {jd(canon(states[2]))}\n\nget {jd(headkey)}\n\n';r=command('fixture_majority_change',leader,['txn']);d=response(r,leader);need(fixture['stdin']==r['stdin']==script and d['succeeded'] is True and d['header']['revision']==4 and iso['monotonic_ns']<r['start_monotonic_ns'],'FIXTURE_WRITE')
    reads=[read(f'majority_before_head_{i}',i,headkey,canon(states[2]),4,3,2)[0] for i in majority];stale,_=read('isolated_serializable',f,headkey,canon(states[1]),3,2,2,'s');need(r['end_monotonic_ns']<min(x['start_monotonic_ns'] for x in reads) and max(x['end_monotonic_ns'] for x in reads)<stale['start_monotonic_ns'],'STALE_ORDER')
    for label in ['isolated_read','rejected_activation']:
        c,es=chunk(label);need(c['outcome']=='UNAVAILABLE' and c['result'] is None and len(es)==1,'FAIL_CLOSED_NO_TXN');check_range(es[0],headkey,False);need(stale['end_monotonic_ns']<c['start_monotonic_ns']<c['end_monotonic_ns']<heal['monotonic_ns'],'UNAVAILABLE_ORDER')
    need(load('AUTHORITY_DECISION')=={'decision':'HOLD','diagnostic_used_for_authority':False,'inputs':['isolated_read','rejected_activation']},'HOLD')
    for n,key in keys['rejected_activation'].items():
        rr,_=read('rejected_'+n,leader,key,canon(states[2]) if n=='head' else None,4,3,2);need(rr['start_monotonic_ns']>calls[2]['end_monotonic_ns'] and rr['end_monotonic_ns']<heal['monotonic_ns'],'REJECTED_VERIFICATION_ORDER')
    for i in majority:read(f'majority_after_head_{i}',i,headkey,canon(states[2]),4,3,2)
    c,es=chunk('healed_read');need(c['outcome']=='CURRENT' and len(es)==1 and c['start_monotonic_ns']>heal['monotonic_ns'],'HEALED_CURRENT');d=check_range(es[0],headkey);need(dec(d['kvs'][0]['value'])==canon(states[2]) and c['result']['state']==states[2] and c['result']['raw_value']==canon(states[2]) and c['result']['mod_revision']==4,'HEALED_VALUE')
    c,es=chunk('healed_exact_retry');vals,result=records('healed_activation',2,'HEAD-C',3,'HEAD-D');need(c['outcome']=='OK' and c['result']==result and len(es)==2,'RETRY_NO_TXN');check_range(es[0],headkey);check_range(es[1],keys['healed_activation']['receipt'])
    for n in vals:
        rr,_=read('final_'+n,f,keys['healed_activation'][n],vals[n],5,4 if n=='head' else 1,2 if n=='head' else 5);need(rr['start_monotonic_ns']>c['end_monotonic_ns'],'FINAL_AFTER_RETRY')
    for i in range(3):read(f'final_head_{i}',i,headkey,canon(states[3]),5,4,2)
    events=load('PROCESS_EVENTS');starts=[e for e in events if e['action']=='start'];exits=[e for e in events if e['action']=='exit'];need(len(starts)==len(exits)==3 and {e['member_index'] for e in starts}=={0,1,2} and all(e['start_number']==0 for e in starts),'NO_RESTART');need(all(any(x['member_index']==e['member_index'] and x['pid']==e['pid'] and x['monotonic_ns']>c['end_monotonic_ns'] for x in exits) for e in starts),'OWNED_CLEANUP');need(clean[0]['active_connections']==clean[0]['live_threads']==0 and clean[0]['overflow'] is False,'RELAY_CLEANUP')
    return {'verification':'PASS','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False,'scope':'unchanged adapter refuses stale-follower activation before Txn; healing restores bounded atomic activation','evidence_files':len(inventory),'adapter_calls':len(calls),'http_exchanges':len(exchanges)}
if __name__=='__main__':
    try:print(json.dumps(verify(sys.argv[1]),sort_keys=True))
    except Exception as e:print(json.dumps({'verification':'REJECTED','error':type(e).__name__+': '+str(e)}));raise SystemExit(2)

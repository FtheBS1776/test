"""Offline recomputation; does not import the runner, contact etcd, or execute fixtures."""
import argparse,base64,hashlib,json,pathlib
def need(v,label):
    if not v:raise ValueError(label)
def enc(s):return base64.b64encode(s.encode()).decode()
def verify(out):
    out=pathlib.Path(out)
    load=lambda name:json.loads((out/name).read_text())
    m=load('EVIDENCE_MANIFEST.json')
    need({str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(m)|{'EVIDENCE_MANIFEST.json'},'EXACT_INVENTORY')
    for name,h in m.items():
        path=pathlib.PurePosixPath(name);need(not path.is_absolute() and '..' not in path.parts,'PATH')
        need(hashlib.sha256((out/name).read_bytes()).hexdigest()==h,'HASH_'+name)
    status=load('STATUS.json');need(status['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION','INCOMPLETE')
    need(status['controlling_pass']==186 and status['promotion'] is False and status['freeze'] is False,'GOVERNANCE')
    for name in m:
        if name.endswith('.json'):
            row=load(name)
            if isinstance(row,dict) and 'argv' in row and 'returncode' in row and '_health_' not in name:need(row['returncode']==0,'COMMAND_'+name)
    before=load('endpoint_before.json');after=load('endpoint_after.json')
    h0=json.loads(before['stdout'])[0]['Status']['header'];h1=json.loads(after['stdout'])[0]['Status']['header']
    need(h0['cluster_id']==h1['cluster_id'] and h0['member_id']==h1['member_id'],'CLUSTER_CONTINUITY')
    def read(name,key,value=None,absent=False):
        rec=load(name+'.json');argv=rec['argv']
        need(rec['returncode']==0 and argv[-3:]==['get',key,'--consistency=l'],'NORMAL_RANGE_'+name)
        d=json.loads(rec['stdout']);h=d['header'];need(str(h['cluster_id'])==str(h0['cluster_id']) and str(h['member_id'])==str(h0['member_id']),'RANGE_IDENTITY')
        if absent:need(not d.get('kvs') and int(d.get('count',0))==0,'ABSENT_RECEIPT');return None
        need(len(d.get('kvs',[]))==1 and int(d['count'])==1,'ONE_KEY')
        kv=d['kvs'][0];need(kv['key']==enc(key) and kv['value']==enc(value),'EXACT_VALUE_'+name)
        return kv
    receipts=[];namespaces=[]
    for label,delayed,retried in [('control',False,False),('late_commit',True,False),('retry_pending',True,True)]:
        req=load(label+'_request.json');r=req['request'];key=r['transition_id'];head=r['head_key'];namespaces.append(head)
        need(json.loads(r['expected_parent'])=={'generation':0,'digest':'G0','authority_config':'C0','lifecycle_generation':0,'registry_digest':'R0'},'PARENT_FIELDS')
        need(json.loads(r['successor'])=={'generation':1,'digest':'G1','authority_config':'C0','lifecycle_generation':0,'registry_digest':'R0'},'SUCCESSOR_FIELDS')
        receipt=req['receipt'];need(json.loads(receipt)=={'request':r,'result':r['successor']},'FULL_RECEIPT')
        initial=read(label+'_initial_head',head,r['expected_parent'])
        need(str(initial['mod_revision'])==r['expected_revision'] and str(initial['version'])=='1','INITIAL_REVISION')
        expected={'compare':[{'target':'VALUE','result':'EQUAL','key':enc(head),'value':enc(r['expected_parent'])},{'target':'MOD','result':'EQUAL','key':enc(head),'mod_revision':r['expected_revision']},{'target':'VERSION','result':'EQUAL','key':enc(key),'version':'0'}],
          'success':[{'request_put':{'key':enc(head),'value':enc(r['successor'])}},{'request_put':{'key':enc(key),'value':enc(receipt)}}],
          'failure':[{'request_range':{'key':enc(head),'serializable':False}}]}
        need(req['txn']==expected and json.loads(req['request_body'])==expected,'EXACT_TRANSACTION')
        client=load(label+'_client.json');need(client['request_body']==req['request_body'],'CLIENT_BYTES')
        events=load(label+'_events.json');need(not any(e['event']=='handler_error' for e in events),'HANDLER_ERROR')
        by={e['event']:e for e in events};need(len(by)==len(events),'DUPLICATE_EVENTS')
        for event in ['accepted','forward']:need(by[event]['request_body']==req['request_body'],'RELAY_BYTES')
        witness=load(label+'_upstream_witness.json');need(witness['http_status']==200,'UPSTREAM_HTTP');w=json.loads(witness['raw_response'])
        need(w.get('succeeded',False) is (not retried),'ORIGINAL_OUTCOME')
        need(str(w['header']['cluster_id'])==str(h0['cluster_id']),'UPSTREAM_CLUSTER')
        if delayed:
            need(client['transport_result']=='TRANSPORT_ERROR' and client['exception_type']=='TimeoutError','ACTUAL_TIMEOUT')
            read(label+'_before_receipt_read',key,absent=True);old=read(label+'_before_head',head,r['expected_parent']);need(old==initial,'NO_EARLY_WRITE')
            decision=load(label+'_before_decision.json');need(decision['receipt_decision']=='UNKNOWN' and decision['witness_used'] is False,'UNKNOWN_PRESERVED')
            readrec=load(label+'_before_receipt_read.json')
            need(by['accepted']['monotonic_ns']<client['end_monotonic_ns']<readrec['start_monotonic_ns']<readrec['end_monotonic_ns']<by['absence_observed_before_release']['monotonic_ns']<by['release']['monotonic_ns']<=by['forward']['monotonic_ns']<witness['monotonic_ns'],'DELAY_ORDER')
            if retried:
                retry=load(label+'_pending_retry.json');need(retry['request_body']==req['request_body'] and retry['http_status']==200 and json.loads(retry['raw_response']).get('succeeded') is True,'EXACT_PENDING_RETRY')
                need(by['absence_observed_before_release']['monotonic_ns']<by['exact_retry_committed_before_release']['monotonic_ns']<by['release']['monotonic_ns'],'RETRY_ORDER')
        else:need(client['transport_result']=='RESPONSE_RECEIVED' and json.loads(client['raw_response']).get('succeeded') is True,'CONTROL')
        committed=load(label+'_decision.json');need(committed['receipt_decision']=='COMMITTED' and committed['witness_used'] is False and committed['inputs']==[label+'_request.json',label+'_receipt_read.json'],'RECONCILIATION_INPUTS')
        hk=read(label+'_head',head,r['successor']);rk=read(label+'_receipt_read',key,receipt)
        need(str(hk['mod_revision'])==str(rk['mod_revision']) and str(hk['version'])=='2' and str(rk['version'])=='1','ONE_SHARED_COMMIT')
        finalretry=load(label+'_final_retry.json');need(finalretry['request_body']==req['request_body'] and finalretry['http_status']==200 and not json.loads(finalretry['raw_response']).get('succeeded',False),'FINAL_RETRY')
        need(read(label+'_head_after',head,r['successor'])==hk and read(label+'_receipt_after',key,receipt)==rk,'RETRY_UNCHANGED')
        if retried:need(read(label+'_retry_head',head,r['successor'])==hk and read(label+'_retry_receipt',key,receipt)==rk,'RELEASE_UNCHANGED')
        receipts.append({'case':label,'head_revision':str(hk['mod_revision']),'original_succeeded':not retried,'state_updates':1})
    need(len(set(namespaces))==3,'SEPARATE_CASES')
    events=load('PROCESS_EVENTS.json');starts=[e for e in events if e['action']=='start'];exits=[e for e in events if e['action']=='exit']
    need(len(starts)==len(exits)==1 and starts[0]['pid']==exits[0]['pid'] and exits[0]['monotonic_ns']>starts[0]['monotonic_ns'],'OWNED_PROCESS_CLEANUP')
    need(load('IDENTITY.json')['binary_sha256']=={'etcd':'030b4b2efd1bcc9ab043080c35f7bb68551e962b23efe62e2f2713429bd9e0f2','etcdctl':'18416269c49d0f25624938b0b45d5bd5d3eb980ab92048dc4652c66a4246141e'},'BINARY_PINS')
    return {'verification':'PASS','disposition':'VERIFIED_WITHIN_TESTED_SCOPE_NONCLAIM','cases':receipts,'scope':'one owned member; positive control and two transport-pending timeout schedules','controlling_pass':186,'promotion':False,'freeze':False,'evidence_files':len(m)}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('evidence');args=ap.parse_args();print(json.dumps(verify(args.evidence),indent=2))

"""Offline pending-entry adjudicator. Diagnostics cannot authorize a transition."""
import argparse,base64,copy,hashlib,json,os,signal
from pathlib import Path
from owned_etcd import demand,save,sha,canonical
from inert_controls import select_txn
from etcd_lifecycle_adapter import Gateway
from execution_identity_reference import ExecutionEnvelope
import stateful_subject as st

def load(p):return json.loads(p.read_text())
def b64(s):return base64.b64decode(s,validate=True)
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def normalized(txn,proto=False):
 demand(set(txn)=={'compare','success','failure'},'TXN_FIELDS');demand(txn['failure']==[],'FAILURE_NOT_EMPTY')
 compares=[]
 for c in txn['compare']:
  target=c['target'];field={'MOD':'modRevision','VALUE':'value','VERSION':'version'}.get(target);demand(field is not None,'COMPARE_TARGET')
  allowed={'key','target','result',field}|({'rangeEnd'} if proto else set());demand(set(c)==allowed,'COMPARE_FIELDS')
  demand(c['result']=='EQUAL' and c.get('rangeEnd','') in (None,''),'COMPARE_OPERATION')
  b64(c['key']);val=c[field];b64(val) if field=='value' else demand(str(int(val))==str(val),'COMPARE_INTEGER')
  compares.append({'key':c['key'],'target':target,'result':'EQUAL',field:str(val)})
 puts=[]
 for op in txn['success']:
  demand(set(op)=={'requestPut'},'SUCCESS_OPERATION');p=op['requestPut']
  allowed={'key','value'}|({'lease','prevKv','ignoreValue','ignoreLease'} if proto else set());demand(set(p)==allowed,'PUT_FIELDS')
  if proto:demand(p['lease']=='0' and p['prevKv'] is False and p['ignoreValue'] is False and p['ignoreLease'] is False,'PUT_SEMANTICS')
  b64(p['key']);b64(p['value']);puts.append({'requestPut':{'key':p['key'],'value':p['value']}})
 return {'compare':compares,'success':puts,'failure':[]}
def model(root,observer):
 names=['HTTP_EXCHANGES','CALLS','KEYS','FIXTURE_BINDING','SNAPSHOT_BOUNDARY','PROCESS_EVENTS','ENVELOPE','TRACE','AUTHORITY_DECISION','CLIENT_THREAD_ERRORS','OWN_PID_VIEW','SELECTED_MEMBER','CONFIGURATION','SERVER_COMMANDS','HOOK','PEER_EVENTS','ORIGINAL_TXN']
 d={n:load(root/(n+'.json')) for n in names};d['observer']=observer
 for n in ['parent_head','committed_head','committed_receipt','committed_execution','committed_outbox','final_head','final_receipt','final_execution','final_outbox','final_status','baseline_status','before_pause_status']:
  r=load(root/(n+'.json'));demand(r['returncode']==0,'COMMAND_FAILED_'+n);d[n]=json.loads(r['stdout']);d[n+'_timing']={'start':r['start_monotonic_ns'],'end':r['end_monotonic_ns']}
 d['candidate_status']=[json.loads(load(root/f'candidate_status_{i}.json')['stdout'])[0] for i in range(3)]
 return d

def validate(d):
 obs=d['observer'];f=d['FIXTURE_BINDING'];m=d['SELECTED_MEMBER'];b=d['SNAPSHOT_BOUNDARY'];tr=d['TRACE'];base=d['baseline_status'][0]['Status'];pre=d['before_pause_status'][0]['Status'];final=d['final_status'][0]['Status'];idx=m['index'];endpoint=f['binding']['endpoint']
 demand(type(idx) is int and idx in range(3),'SELECTED_INDEX')
 demand(obs['schema']=='WAL_DECODE_V2' and obs['scope']=='INITIAL_SEGMENT_READ_ONLY_DECODE','OBSERVER_SCOPE')
 demand(obs['cluster_id']==f['cluster_id']==m['cluster_id']==str(base['header']['cluster_id'])==str(pre['header']['cluster_id'])==str(final['header']['cluster_id']),'CLUSTER_BINDING')
 demand(obs['node_id']==f['member_id']==m['member_id']==str(base['header']['member_id'])==str(pre['header']['member_id'])==str(final['header']['member_id']),'MEMBER_BINDING')
 demand(base['leader']==pre['leader']==int(m['member_id']) and base['raftTerm']==pre['raftTerm']==obs['term'] and final['raftTerm']>=obs['term'],'SELECTED_ACTUAL_LEADER_TERM')
 candidates=d['candidate_status'];ids=[v['Status']['header']['member_id'] for v in candidates]
 demand(len(set(ids))==3 and ids[idx]==int(m['member_id']) and all(v['Status']['leader']==base['leader'] and str(v['Status']['header']['cluster_id'])==obs['cluster_id'] for v in candidates),'BASELINE_MEMBERSHIP')
 cfg=d['CONFIGURATION'];commands=d['SERVER_COMMANDS']
 demand(cfg['members']==3 and len(commands)==3 and m==b['member_binding'] and m['pid']==b['pid'] and m['directory']==b['source_data_directory'] and m['endpoint']==endpoint==cfg['endpoints'][idx] and m['argv']==commands[idx],'SELECTED_CONFIG_BINDING')
 demand(m['directory']==str(Path(m['directory']).parent/f'm{idx}') and commands[idx][commands[idx].index('--data-dir')+1]==m['directory'] and commands[idx][commands[idx].index('--listen-client-urls')+1]==endpoint,'SELECTED_DIRECTORY_ENDPOINT')
 demand(all(v['Endpoint']==cfg['endpoints'][i] for i,v in enumerate(candidates)),'CANDIDATE_ENDPOINTS')
 own=d['OWN_PID_VIEW'];demand(own['same_pid_view'] is True and str(own['os_getpid'])==own['proc_fields']['Pid'],'PID_VIEW')
 events=d['PROCESS_EVENTS'];selected=[e for e in events if e['member_index']==idx]
 def one(action):
  rows=[e for e in selected if e['action']==action];demand(len(rows)==1,'EVENT_'+action);return rows[0]
 start,stop,confirmed,resume,continued,term,exit=[one(n) for n in ['start','SIGSTOP','stop_confirmed','SIGCONT','resume_confirmed','SIGTERM','exit']]
 demand(all(e['pid']==m['pid'] for e in [start,stop,confirmed,resume,continued,term,exit]),'PROCESS_PID_BINDING')
 demand(os.WIFSTOPPED(confirmed['wait_status']) and os.WSTOPSIG(confirmed['wait_status'])==signal.SIGSTOP and confirmed['stop_signal']==signal.SIGSTOP and os.WIFCONTINUED(continued['wait_status']),'STOP_CONTINUE_STATUS')
 demand(confirmed['tasks']==b['tasks_before']==b['tasks_after'] and bool(b['tasks_before']) and set(b['tasks_before'].values())=={'T'},'STOPPED_TASKS')
 for i in range(3):
  starts=[e for e in events if e['action']=='start' and e['member_index']==i];ends=[e for e in events if e['action']=='exit' and e['member_index']==i]
  demand(len(starts)==len(ends)==1 and starts[0]['pid']==ends[0]['pid'] and ends[0]['returncode'] in (0,-15),'ALL_PROVIDER_CLEANUP')
 demand(not any(e['action'] in ('cleanup_forced','SIGKILL') for e in events),'NO_FORCED_CLEANUP')
 terminal=obs['terminal']
 demand(b['mode']=='OWNED_STOP_CONFIRMED_STABLE_BYTE_COPY' and b['source_sha256_before']==b['source_sha256_after']==b['copy_sha256']==terminal['file_sha256'] and b['source_identity_before']==b['source_identity_after'],'STABLE_COPY')
 demand(terminal['condition']=='EOF' and terminal['canonical_frames_and_padding'] is True and terminal['unexpected_eof_accepted'] is False and terminal['last_valid_offset']+terminal['zero_suffix_bytes']==terminal['file_size']==b['source_identity_before']['size'],'STRICT_TERMINAL')
 demand(b['authority_input'] is False and b['durability_claim'] is False and b['raft_snapshot_count']==0,'DIAGNOSTIC_SCOPE')
 demand(tr['previous_trace_absent'] is True and tr['exception_values_or_headers_retained'] is False,'TRACE_SCOPE')
 body=json.dumps(d['ORIGINAL_TXN'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();digest=hashlib.sha256(body).hexdigest()
 select_txn(tr,body,endpoint,d['HOOK']);te=[e for e in tr['events'] if e['path']=='/v3/kv/txn'];hook=d['HOOK']
 demand(all(e['thread_id']==tr['thread_id'] for e in hook),'HOOK_THREAD')
 demand(te[1]['exception_type']=='TimeoutError' and te[1]['exact_timeout_type'] is True and te[2]['exception_type']=='ConnectionError' and te[2]['exact_connection_error_type'] is True,'ORIGINAL_TIMEOUT_TYPES')
 peers=d['PEER_EVENTS'];isolates=[e for e in peers if e['event']=='isolate'];heals=[e for e in peers if e['event']=='heal'];clean=[e for e in peers if e['event']=='relay_cleanup']
 demand(len(isolates)==len(heals)==len(clean)==1,'PEER_EVENT_COUNTS');iso=isolates[0];heal=heals[0]
 demand(iso['member_index']==heal['member_index']==idx and iso['member_ids_hex']==[format(v,'x') for v in ids] and bool(iso['closed_connections']),'EXACT_PEER_GATE')
 demand(clean[0]['active_connections']==clean[0]['live_threads']==0 and clean[0]['overflow'] is False,'PEER_CLEANUP')
 demand(d['before_pause_status_timing']['end']<te[0]['monotonic_ns']<hook[0]['monotonic_ns']<=iso['monotonic_ns']<=hook[1]['monotonic_ns'],'PREFLIGHT_HOOK_ORDER')
 demand(hook[1]['monotonic_ns']+150000000<=stop['monotonic_ns']<confirmed['monotonic_ns']<=b['start_monotonic_ns']<b['end_monotonic_ns']+100000000<te[1]['monotonic_ns']<=te[2]['monotonic_ns']<=te[3]['monotonic_ns']<=resume['monotonic_ns']<=continued['monotonic_ns']<=heal['monotonic_ns']<term['monotonic_ns']<exit['monotonic_ns'],'PENDING_CAPTURE_CHRONOLOGY')
 demand(continued['monotonic_ns']-stop['monotonic_ns']<4000000000,'BOUNDED_PAUSE')
 demand(d['CLIENT_THREAD_ERRORS']==[] and d['AUTHORITY_DECISION']=={'decision':'HOLD','adapter_outcome':'UNKNOWN_COMMIT','diagnostics_used_for_authority':False},'UNKNOWN_NOT_AUTHORITY')
 calls=d['CALLS'];ex=d['HTTP_EXCHANGES'];labels=['original_activation','resumed_current_read','reconcile_original','same_identity_retry','exact_retry']
 demand([c['label'] for c in calls]==labels and [c['outcome'] for c in calls[:2]]==['UNKNOWN_COMMIT','CURRENT'] and calls[2]['outcome'] in ('OK','UNKNOWN_COMMIT') and [c['outcome'] for c in calls[3:]]==['OK','OK'],'ORDINARY_ADAPTER_OUTCOMES')
 demand(calls[0]['start_monotonic_ns']<=te[0]['monotonic_ns'] and te[3]['monotonic_ns']<=calls[0]['end_monotonic_ns']<=resume['monotonic_ns'] and heal['monotonic_ns']<calls[1]['start_monotonic_ns'],'CALL_LIFECYCLE')
 demand(all(a['end_monotonic_ns']<=z['start_monotonic_ns'] for a,z in zip(calls,calls[1:])),'SEQUENTIAL_CALLS')
 demand(calls[0]['exchange_start']==0 and calls[-1]['exchange_end']==len(ex) and all(a['exchange_end']==z['exchange_start'] for a,z in zip(calls,calls[1:])),'EXACT_CALL_EXCHANGES')
 slices=[[e for e in ex[c['exchange_start']:c['exchange_end']]] for c in calls]
 demand([e['path'] for e in slices[0]]==['/v3/kv/range','/v3/kv/range','/v3/kv/txn'],'PRELIMINARY_READS_THEN_TXN')
 demand(all(e['authorization_present'] is False for e in ex),'FIXTURE_AUTH_SCOPE')
 txn=slices[0][-1];demand(b64(txn['request_b64'])==body and txn['response_b64'] is None and txn['transport_error']=='TimeoutError','ORIGINAL_EXCHANGE_TIMEOUT')
 for i,e in enumerate(ex):
  if i!=2:demand(e['transport_error'] is None and e['response_b64'] is not None,'OTHER_EXCHANGE_COMPLETE')
  if e['path']=='/v3/kv/range':demand(json.loads(b64(e['request_b64']))['serializable'] is False,'NORMAL_READS_ONLY')
 demand(all(e['path']=='/v3/kv/range' for j in (1,2,4) for e in slices[j]),'RECONCILE_AND_FINAL_RETRY_READ_ONLY')
 expected=normalized(d['ORIGINAL_TXN']);txns=[e for e in ex if e['path']=='/v3/kv/txn'];demand(len(txns) in (1,2) and all(b64(e['request_b64'])==body for e in txns),'ONLY_IDENTICAL_TXNS')
 entries=obs['entries'];demand(bool(entries) and [e['index'] for e in entries]==list(range(1,entries[-1]['index']+1)),'CONTIGUOUS_ENTRIES')
 for e in entries:demand(0<e['term']<=obs['term'] and hashlib.sha256(b64(e['data_b64'])).hexdigest()==e['sha256'],'RAW_ENTRY_HASH')
 candidates=[]
 for e in entries:
  r=e['request']
  if r and r.get('txn') is not None and len(r['txn']['success'])==4 and any(c.get('key')==expected['compare'][0]['key'] for c in r['txn']['compare']):
   demand(e['type']=='EntryNormal' and e['roundtrip_exact'] is True and normalized(r['txn'],True)==expected,'EXACT_COMPLETE_TXN_ENTRY')
   demand(r.get('ID')=='0' and all(v is None for k,v in r.items() if k not in ('ID','header','txn')),'REQUEST_UNION')
   demand(set(r['header'])=={'ID','username','authRevision'} and int(r['header']['ID'])>0 and r['header']['username']=='' and r['header']['authRevision']=='0','REQUEST_HEADER');candidates.append(e)
 demand(len(candidates)==1,'POSITIVE_UNIQUE_PENDING_ENTRY');target=candidates[0]
 demand(pre['raftIndex']==pre['raftAppliedIndex']<target['index']<=entries[-1]['index'] and 0<obs['commit_index']<=entries[-1]['index'],'DISTINCT_PRE_AND_CAPTURE_INDICES')
 keys=d['KEYS'];ordered=['head','receipt','execution','outbox'];encoded={n:base64.b64encode(keys[n].encode()).decode() for n in ordered};parent=d['parent_head']['kvs'][0]
 demand(parent['key']==encoded['head'],'PARENT_KEY')
 demand(expected['compare']==[{'key':encoded['head'],'target':'MOD','result':'EQUAL','modRevision':str(parent['mod_revision'])},{'key':encoded['head'],'target':'VALUE','result':'EQUAL','value':parent['value']}]+[{'key':encoded[n],'target':'VERSION','result':'EQUAL','version':'0'} for n in ordered[1:]],'EXACT_PARENT_ABSENCE_COMPARES')
 demand([p['requestPut']['key'] for p in expected['success']]==[encoded[n] for n in ordered],'FOUR_EXACT_WRITES')
 first_read=json.loads(b64(slices[0][0]['response_b64']));expected_parent={k:(str(v) if k in ('create_revision','mod_revision','version') else v) for k,v in parent.items()};demand(first_read['kvs']==[expected_parent],'PRELIMINARY_PARENT_READ')
 demand(json.loads(b64(slices[0][1]['response_b64'])).get('kvs',[])==[],'PRELIMINARY_RECEIPT_ABSENT')
 values={};revisions=set()
 for n,put in zip(ordered,expected['success']):
  a=d['committed_'+n]['kvs'];z=d['final_'+n]['kvs'];demand(len(a)==len(z)==1 and a==z,'FINAL_RETRY_METADATA_'+n);kv=z[0]
  demand(kv['key']==encoded[n] and kv['value']==put['requestPut']['value'] and int(kv['version'])==(int(parent['version'])+1 if n=='head' else 1),'EXACT_FINAL_VALUE_VERSION_'+n)
  revisions.add(int(kv['mod_revision']))
  if n!='head':demand(kv['create_revision']==kv['mod_revision'],'SINGLE_CREATION_'+n)
  values[n]=json.loads(b64(kv['value']))
 demand(len(revisions)==1,'ATOMIC_REVISION')
 old=json.loads(b64(parent['value']));demand(old['generation']==0 and values['head']==dict(old,generation=1,head_digest='HEAD-B'),'ONE_HEAD_TRANSITION')
 tid='wal_control_activation';eid=tid+'-execution';fp=st.FP(0,'HEAD-A','HEAD-B',tid,'C1',(('publish','wal-control-target','wal-control-payload'),));envfp=hashlib.sha256(ExecutionEnvelope(**d['ENVELOPE']).canonical()).hexdigest();result={'generation':1,'head_digest':'HEAD-B','authority_config':'C1'}
 demand(d['ENVELOPE']['execution_id']==eid and values['receipt']=={'transition_id':tid,'fingerprint':fp,'execution_id':eid,'envelope_fingerprint':envfp,'result':result},'FULL_RECEIPT')
 demand(values['execution']=={'execution_id':eid,'envelope_fingerprint':envfp,'transition_id':tid},'EXECUTION_RECORD')
 demand(values['outbox']=={'effect_id':st.EID(tid,'publish','wal-control-target'),'transition_id':tid,'kind':'publish','target':'wal-control-target','payload':'wal-control-payload','generation':1,'authority_config':'C1'},'OUTBOX_RECORD')
 demand(calls[0]['result']=={'transition_id':tid,'fingerprint':fp} and calls[3]['result']==calls[4]['result']==result,'STABLE_RESULTS')
 if calls[2]['outcome']=='OK':demand(calls[2]['result']==result and len(txns)==1,'PRIOR_COMMIT_READ_ONLY')
 else:demand(calls[2]['result'] is None,'UNKNOWN_RECONCILIATION')
 return {'status':'PASS','scope':'EXACT_LOCAL_ENTRY_BEFORE_ORIGINAL_TXN_TIMEOUT_AND_SAME_IDENTITY_RECONCILIATION','selected_member_index':idx,'target_entry':target['index'],'saved_wal_commit':obs['commit_index'],'pretrial_applied':pre['raftAppliedIndex'],'captured_last_entry':entries[-1]['index'],'final_applied':final['raftAppliedIndex'],'copy_to_timeout_margin_ns':te[1]['monotonic_ns']-b['end_monotonic_ns'],'reconcile_after_heal':calls[2]['outcome'],'adapter_txns':len(txns),'atomic_revision':next(iter(revisions)),'uncommittedness_proven':False,'durability_proven':False,'production_trust_proven':False,'controlling_pass':186,'classification':'NONCLAIM'}

def check(root,observer_path):
 demand(load(root/'EVIDENCE_MANIFEST.json')=={k:v for k,v in inventory(root).items() if k!='EVIDENCE_MANIFEST.json'},'OBSERVATION_INVENTORY')
 inv=inventory(root/'snapshot');demand(load(root/'SNAPSHOT_MANIFEST.json')==inv and set(inv)=={'member/wal/0000000000000000-0000000000000000.wal'},'SNAPSHOT_INVENTORY')
 d=model(root,load(observer_path));return check_model(d)

def check_model(d):
 result=validate(d);negative=[]
 mutations={
 'wrong_member':lambda v:v['observer'].__setitem__('node_id','1'),
 'wrong_pid':lambda v:v['SELECTED_MEMBER'].__setitem__('pid',-1),
 'wrong_endpoint':lambda v:v['SELECTED_MEMBER'].__setitem__('endpoint','http://127.0.0.1:1'),
 'wrong_leader':lambda v:v['before_pause_status'][0]['Status'].__setitem__('leader',0),
 'late_copy':lambda v:v['SNAPSHOT_BOUNDARY'].__setitem__('end_monotonic_ns',10**30),
 'early_pause':lambda v:next(e for e in v['PROCESS_EVENTS'] if e['action']=='SIGSTOP').__setitem__('monotonic_ns',0),
 'changed_tasks':lambda v:v['SNAPSHOT_BOUNDARY'].__setitem__('tasks_after',{}),
 'missing_hook':lambda v:v['HOOK'].pop(),
 'wrong_gate_member':lambda v:next(e for e in v['PEER_EVENTS'] if e['event']=='isolate').__setitem__('member_index',-1),
 'changed_request':lambda v:v['ORIGINAL_TXN']['success'][0]['requestPut'].__setitem__('value','eA=='),
 'missing_target':lambda v:v['observer'].__setitem__('entries',[e for e in v['observer']['entries'] if e['index']!=result['target_entry']]),
 'wrong_trace_request':lambda v:next(e for e in v['TRACE']['events'] if e['path']=='/v3/kv/txn').__setitem__('request_sha256','0'*64),
 'wrong_trace_bytecode':lambda v:v['TRACE'].__setitem__('bytecode_sha256','0'*64),
 'not_timeout':lambda v:next(e for e in v['TRACE']['events'] if e.get('exact_timeout_type')).__setitem__('exact_timeout_type',False),
 'not_unknown':lambda v:v['CALLS'][0].__setitem__('outcome','OK'),
 'retry_version':lambda v:v['final_outbox']['kvs'][0].__setitem__('version',99),
 'partial_tail':lambda v:v['observer']['terminal'].__setitem__('unexpected_eof_accepted',True),
 'diagnostic_authority':lambda v:v['AUTHORITY_DECISION'].__setitem__('diagnostics_used_for_authority',True),
 'relay_not_clean':lambda v:next(e for e in v['PEER_EVENTS'] if e['event']=='relay_cleanup').__setitem__('live_threads',1),
 'already_applied':lambda v:v['before_pause_status'][0]['Status'].__setitem__('raftAppliedIndex',result['target_entry']),
 }
 for name,mutate in mutations.items():
  v=copy.deepcopy(d);mutate(v)
  try:validate(v)
  except Exception as e:negative.append({'mutation':name,'rejected':True,'reason':type(e).__name__+': '+str(e)})
  else:raise RuntimeError('NEGATIVE_ACCEPTED_'+name)
 result['model_negatives']=negative;return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('observations');ap.add_argument('observer_json');ap.add_argument('--output',required=True);a=ap.parse_args()
 try:r=check(Path(a.observations),Path(a.observer_json));code=0
 except Exception as e:r={'status':'INDETERMINATE_OR_REJECTED','error':type(e).__name__+': '+str(e),'classification':'NONCLAIM'};code=2
 save(Path(a.output),r);print(json.dumps(r));return code
if __name__=='__main__':raise SystemExit(main())

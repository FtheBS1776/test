"""Independent offline binding of a healthy paused initial-segment control."""
import argparse,base64,copy,hashlib,json
from pathlib import Path
from owned_etcd import demand,save,sha,canonical
def b64(s):return base64.b64decode(s,validate=True)
def load(p):return json.loads(p.read_text())
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
def model(root,observed):
 names=['HTTP_EXCHANGES','CALLS','KEYS','FIXTURE_BINDING','SNAPSHOT_BOUNDARY','PROCESS_EVENTS','ENVELOPE','TRACE','AUTHORITY_DECISION','CLIENT_THREAD_ERRORS','OWN_PID_VIEW','SELECTED_MEMBER','CONFIGURATION','SERVER_COMMANDS'];d={n:load(root/(n+'.json')) for n in names};d['observer']=observed;d['SERVER_LOG']=[json.loads(line) for line in (root/f"SERVER_{d['SELECTED_MEMBER']['index']}_START_0.txt").read_text().splitlines()]
 for n in ['parent_head','committed_head','committed_receipt','committed_execution','committed_outbox','final_head','final_receipt','final_execution','final_outbox','final_status','baseline_status','before_pause_status']:
  r=load(root/(n+'.json'));demand(r['returncode']==0,'COMMAND_FAILED');d[n]=json.loads(r['stdout']);d[n+'_timing']={'start':r['start_monotonic_ns'],'end':r['end_monotonic_ns']}
 return d
def validate(d):
 obs=d['observer'];f=d['FIXTURE_BINDING'];final=d['final_status'][0]['Status'];base=d['baseline_status'][0]['Status']
 demand(obs['schema']=='WAL_DECODE_V2' and obs['scope']=='INITIAL_SEGMENT_READ_ONLY_DECODE','OBSERVER_SCOPE')
 demand(obs['cluster_id']==f['cluster_id']==str(final['header']['cluster_id'])==str(base['header']['cluster_id']),'CLUSTER_BINDING')
 demand(obs['node_id']==f['member_id']==str(final['header']['member_id'])==str(base['header']['member_id']),'MEMBER_BINDING')
 demand(base['leader']==final['leader'] and base['leader']!=int(obs['node_id']),'HEALTHY_SELECTED_FOLLOWER')
 demand(obs['term']==final['raftTerm']==final['header']['raft_term'],'TERM_BINDING')
 prestatus=d['before_pause_status'][0]['Status'];captured_last=prestatus['raftIndex']
 demand(prestatus['raftIndex']==prestatus['raftAppliedIndex'] and 0<obs['commit_index']<=captured_last<=final['raftIndex']==final['raftAppliedIndex'],'DISTINCT_CAPTURE_AND_FINAL_INDICES')
 demand(str(prestatus['header']['cluster_id'])==obs['cluster_id'] and str(prestatus['header']['member_id'])==obs['node_id'] and prestatus['leader']==base['leader'] and prestatus['raftTerm']==prestatus['header']['raft_term']==obs['term'],'PREPAUSE_IDENTITY_TERM')
 entries=obs['entries'];demand([e['index'] for e in entries]==list(range(1,captured_last+1)),'CONTIGUOUS_CAPTURED_ENTRIES')
 for e in entries:
  demand(e['term']>0 and e['term']<=obs['term'] and hashlib.sha256(b64(e['data_b64'])).hexdigest()==e['sha256'],'ENTRY_RAW_BINDING')
 terminal=obs['terminal'];boundary=d['SNAPSHOT_BOUNDARY'];trace=d['TRACE'];all_events=d['PROCESS_EVENTS'];member=d['SELECTED_MEMBER'];index=member['index'];events=[e for e in all_events if e['member_index']==index]
 demand(type(index) is int and index in (1,2) and member==boundary['member_binding'] and member['pid']==boundary['pid'] and member['directory']==boundary['source_data_directory'] and member['member_id']==obs['node_id'] and member['cluster_id']==obs['cluster_id'] and member['endpoint']==f['binding']['endpoint'],'SELECTED_MEMBER_BINDING')
 config=d['CONFIGURATION'];commands=d['SERVER_COMMANDS'];demand(config['members']==3 and len(commands)==3 and member['endpoint']==config['endpoints'][index] and member['argv']==commands[index],'SELECTED_CONFIG_COMMAND')
 demand(member['directory']==str(Path(member['directory']).parent/f'm{index}') and commands[index][commands[index].index('--data-dir')+1]==member['directory'],'SELECTED_DIRECTORY_BINDING')
 for i in range(3):
  starts=[e for e in all_events if e['action']=='start' and e['member_index']==i];ends=[e for e in all_events if e['action']=='exit' and e['member_index']==i];demand(len(starts)==len(ends)==1 and starts[0]['pid']==ends[0]['pid'] and ends[0]['returncode'] in (0,-15),'ALL_OWNED_MEMBERS_CLEANED')
 demand(not any(e['action'] in ('cleanup_forced','SIGKILL') for e in all_events),'NO_FORCED_CLEANUP')
 demand(terminal['condition']=='EOF' and terminal['file_sha256']==boundary['copy_sha256'] and terminal['canonical_frames_and_padding'] is True and terminal['unexpected_eof_accepted'] is False and terminal['last_valid_offset']+terminal['zero_suffix_bytes']==terminal['file_size']==boundary['source_identity_before']['size'],'STRICT_TERMINAL_BINDING')
 demand(boundary['mode']=='OWNED_STOP_CONFIRMED_STABLE_BYTE_COPY' and boundary['source_sha256_before']==boundary['source_sha256_after']==boundary['copy_sha256'] and boundary['source_identity_before']==boundary['source_identity_after'],'STABLE_SOURCE_BYTES')
 demand(boundary['tasks_before']==boundary['tasks_after'] and bool(boundary['tasks_before']) and set(boundary['tasks_before'].values())=={'T'},'ALL_TASKS_STOPPED')
 demand(boundary['authority_input'] is False and boundary['durability_claim'] is False and boundary['raft_snapshot_count']==0,'BOUNDARY_SCOPE')
 own=d['OWN_PID_VIEW','SELECTED_MEMBER','CONFIGURATION','SERVER_COMMANDS'];demand(own['same_pid_view'] is True and str(own['os_getpid'])==own['proc_fields']['Pid'],'PID_VIEW_MATCH')
 def one(action):
  values=[e for e in events if e['action']==action];demand(len(values)==1,'PROCESS_EVENT_'+action);return values[0]
 stop=one('SIGSTOP');confirmed=one('stop_confirmed');resume=one('SIGCONT');continued=one('resume_confirmed');term=one('SIGTERM');exit=one('exit');started=one('start')
 import os,signal
 demand(all(e['pid']==started['pid']==boundary['pid'] for e in [stop,confirmed,resume,continued,term,exit]) and os.WIFSTOPPED(confirmed['wait_status']) and os.WSTOPSIG(confirmed['wait_status'])==signal.SIGSTOP and confirmed['stop_signal']==signal.SIGSTOP and confirmed['tasks']==boundary['tasks_before'] and os.WIFCONTINUED(continued['wait_status']),'OWNED_STOP_RESUME_STATUS')
 demand(exit['returncode'] in (0,-15) and not any(e['action'] in ('cleanup_forced','SIGKILL') for e in events),'CLEAN_RESUMED_EXIT')
 demand(trace['post_method_unchanged'] is True and trace['restore_ok'] is True and trace['previous_trace_absent'] is True and trace['errors']==[] and trace['source_sha256_before']==trace['source_sha256_after'] and trace['exception_values_or_headers_retained'] is False,'TRACE_VALIDITY')
 from etcd_lifecycle_adapter import Gateway
 demand(trace['source_sha256_before']==sha(Path(__file__).resolve().parent/'etcd_lifecycle_adapter.py') and trace['bytecode_sha256']==__import__('hashlib').sha256(Gateway.post.__code__.co_code).hexdigest(),'ORIGINAL_GATEWAY_SOURCE_CODE_BINDING')
 te=trace['events'];demand([e['event'] for e in te]==['call','exception','exception','return'] and [e['exception_type'] for e in te if e['event']=='exception']==['TimeoutError','ConnectionError'] and te[1]['exact_timeout_type'] is True and te[2]['exact_connection_error_type'] is True,'ORIGINAL_TIMEOUT_TRACE_SEQUENCE')
 demand(all(e['thread_id']==trace['thread_id'] and e['code_identity_match'] is True and e['path']=='/v3/kv/range' and e['endpoint']==f['binding']['endpoint'] and e['request_sha256']==te[0]['request_sha256'] for e in te),'TRACE_THREAD_REQUEST_BINDING')
 demand([e['monotonic_ns'] for e in te]==sorted(e['monotonic_ns'] for e in te),'TRACE_CLOCK_ORDER')
 demand(d['before_pause_status_timing']['end']<stop['monotonic_ns']<confirmed['monotonic_ns']<=te[0]['monotonic_ns']<=boundary['start_monotonic_ns']<boundary['end_monotonic_ns']+100000000<te[1]['monotonic_ns']<=te[2]['monotonic_ns']<=te[3]['monotonic_ns']<=resume['monotonic_ns']<=continued['monotonic_ns']<term['monotonic_ns']<exit['monotonic_ns'],'BEFORE_OBSERVED_TIMEOUT_CHRONOLOGY')
 demand(continued['monotonic_ns']-stop['monotonic_ns']<4000000000,'BOUNDED_PAUSE_DURATION')
 demand(d['CLIENT_THREAD_ERRORS']==[] and d['AUTHORITY_DECISION']=={'decision':'HOLD','adapter_outcome':'UNAVAILABLE','diagnostics_used_for_authority':False},'DIAGNOSTICS_NOT_AUTHORITY')
 demand(prestatus['header']['revision']==d['committed_head']['header']['revision'] and prestatus['raftTerm']==obs['term'],'HEALTHY_PREPAUSE_APPLICATION_BOUNDARY')
 log=d['SERVER_LOG'];demand(any(v.get('msg')=='closed etcd server' and v.get('data-dir')==boundary['source_data_directory'] for v in log),'COMPLETED_SHUTDOWN')
 calls=d['CALLS'];ex=d['HTTP_EXCHANGES'];demand([c['label'] for c in calls]==['activation','paused_current_read','resumed_current_read','exact_retry'] and [c['outcome'] for c in calls]==['OK','UNAVAILABLE','CURRENT','OK'] and calls[0]['result']==calls[3]['result'] and calls[1]['result'] is None,'ADAPTER_RESULTS')
 demand(all(e['authorization_present'] is False for e in ex),'HTTP_CONTROL_ERROR')
 txns=[(i,e) for i,e in enumerate(ex) if e['path']=='/v3/kv/txn'];demand(len(txns)==1,'ONE_ADAPTER_TXN')
 xi,exchange=txns[0];demand(calls[0]['exchange_start']<=xi<calls[0]['exchange_end'] and all(e['path']=='/v3/kv/range' for e in ex[calls[3]['exchange_start']:calls[3]['exchange_end']]),'RETRY_READ_ONLY')
 paused=ex[calls[1]['exchange_start']:calls[1]['exchange_end']];demand(len(paused)==1 and paused[0]['path']=='/v3/kv/range' and paused[0]['transport_error']=='TimeoutError' and paused[0]['response_b64'] is None and __import__('hashlib').sha256(b64(paused[0]['request_b64'])).hexdigest()==te[0]['request_sha256'],'ACTUAL_PAUSED_RANGE_TIMEOUT')
 demand(all(e['transport_error'] is None and e['response_b64'] is not None for i,e in enumerate(ex) if i not in range(calls[1]['exchange_start'],calls[1]['exchange_end'])),'OTHER_EXCHANGES_COMPLETE')
 demand(calls[1]['start_monotonic_ns']<=te[0]['monotonic_ns'] and te[3]['monotonic_ns']<=calls[1]['end_monotonic_ns']<=resume['monotonic_ns'] and continued['monotonic_ns']<=calls[2]['start_monotonic_ns'] and calls[2]['end_monotonic_ns']<=calls[3]['start_monotonic_ns'],'ADAPTER_CALL_CLOCK_BINDING')
 expected=normalized(json.loads(b64(exchange['request_b64'])));reply=json.loads(b64(exchange['response_b64']));demand(reply['succeeded'] is True,'TXN_COMMITTED_RESPONSE')
 candidates=[]
 for e in entries:
  req=e['request']
  if req and req.get('txn') is not None and any(c.get('key')==expected['compare'][0]['key'] for c in req['txn']['compare']):
   # The initialization also compares head; identify activation by its four writes.
   if len(req['txn']['success'])!=4:continue
   demand(e['type']=='EntryNormal' and e['roundtrip_exact'] is True,'EXACT_PROTO_REENCODING')
   demand(normalized(req['txn'],True)==expected,'COMPLETE_TXN_BINDING')
   demand(req.get('ID')=='0' and all(v is None for k,v in req.items() if k not in ('ID','header','txn')),'INTERNAL_REQUEST_UNION')
   header=req['header'];demand(set(header)=={'ID','username','authRevision'} and int(header['ID'])>0 and header['username']=='' and header['authRevision']=='0','INTERNAL_REQUEST_HEADER');candidates.append(e)
 demand(len(candidates)==1,'EXACT_ENTRY_UNIQUE');target=candidates[0];demand(target['index']<=captured_last,'TARGET_PREPAUSE_APPLIED_SCOPE')
 keys=d['KEYS'];parent=d['parent_head']['kvs'][0];headkey=base64.b64encode(keys['head'].encode()).decode();demand(parent['key']==headkey,'PARENT_KEY')
 demand(expected['compare'][:2]==[{'key':headkey,'target':'MOD','result':'EQUAL','modRevision':str(parent['mod_revision'])},{'key':headkey,'target':'VALUE','result':'EQUAL','value':parent['value']}],'EXACT_PARENT_BYTES_REVISION')
 ordered=['head','receipt','execution','outbox'];keyb64={n:base64.b64encode(keys[n].encode()).decode() for n in ordered}
 demand(expected['compare'][2:]==[{'key':keyb64[n],'target':'VERSION','result':'EQUAL','version':'0'} for n in ordered[1:]],'ABSENT_KEY_COMPARES')
 demand([p['requestPut']['key'] for p in expected['success']]==[keyb64[n] for n in ordered],'FOUR_WRITES')
 values={};revision=int(reply['header']['revision'])
 for n,put in zip(ordered,expected['success']):
  before=d['committed_'+n]['kvs'];after=d['final_'+n]['kvs'];demand(len(before)==len(after)==1 and before==after,'RETRY_METADATA_'+n);kv=after[0]
  demand(kv['key']==keyb64[n] and kv['value']==put['requestPut']['value'] and int(kv['mod_revision'])==revision,'WRITE_RECORD_'+n)
  demand(int(kv['version'])==(int(parent['version'])+1 if n=='head' else 1),'WRITE_VERSION_'+n)
  if n!='head':demand(int(kv['create_revision'])==revision,'SINGLE_CREATION_'+n)
  values[n]=json.loads(b64(kv['value']))
 old=json.loads(b64(parent['value']));new=dict(old,generation=1,head_digest='HEAD-B');demand(values['head']==new,'HEAD_TRANSITION')
 receipt=values['receipt'];execution=values['execution'];outbox=values['outbox'];tid='wal_control_activation';eid=tid+'-execution'
 demand(receipt['transition_id']==execution['transition_id']==outbox['transition_id']==tid and receipt['execution_id']==execution['execution_id']==d['ENVELOPE']['execution_id']==eid,'STABLE_IDENTITIES')
 # Use independently reviewed unchanged reference primitives, never imports from returned evidence.
 import stateful_subject as st
 from execution_identity_reference import ExecutionEnvelope
 envfp=hashlib.sha256(ExecutionEnvelope(**d['ENVELOPE']).canonical()).hexdigest()
 demand(receipt['envelope_fingerprint']==execution['envelope_fingerprint']==envfp,'FULL_ENVELOPE_FINGERPRINT')
 demand(receipt['fingerprint']==st.FP(0,'HEAD-A','HEAD-B',tid,'C1',(('publish','wal-control-target','wal-control-payload'),)),'TRANSITION_FINGERPRINT')
 demand(receipt['result']==calls[0]['result']=={'generation':1,'head_digest':'HEAD-B','authority_config':'C1'},'RECEIPT_RESULT')
 demand(outbox=={'effect_id':st.EID(tid,'publish','wal-control-target'),'transition_id':tid,'kind':'publish','target':'wal-control-target','payload':'wal-control-payload','generation':1,'authority_config':'C1'},'OUTBOX_BYTES')
 return {'status':'PASS','scope':'HEALTHY_SELECTED_NONZERO_MEMBER_PAUSED_COPY_BEFORE_ORIGINAL_READ_TIMEOUT','entry_index':target['index'],'entry_term':target['term'],'internal_request_id':target['request']['header']['ID'],'wal_saved_commit_index':obs['commit_index'],'captured_last_entry_index':captured_last,'prepause_api_applied_index':prestatus['raftAppliedIndex'],'final_api_applied_index':final['raftAppliedIndex'],'target_covered_by_wal_saved_commit_marker':target['index']<=obs['commit_index'],'node_id':obs['node_id'],'cluster_id':obs['cluster_id'],'shared_write_revision':revision,'adapter_txn_count':1,'exact_retry':'READ_ONLY_UNCHANGED_METADATA','controlling_pass':186,'classification':'NONCLAIM','promotion':False,'freeze':False,'live_pre_timeout_pending_entry':'UNESTABLISHED','copy_to_observed_timeout_margin_ns':te[1]['monotonic_ns']-boundary['end_monotonic_ns'],'selected_member_index':index,'selected_member_id':member['member_id'],'stopped_task_count':len(boundary['tasks_before']),'pause_duration_ns':continued['monotonic_ns']-stop['monotonic_ns'],'original_gateway_trace_sequence':'TimeoutError -> ordinary ConnectionError translation','pending_transaction_submitted':False}
def check(root,observer_path,negatives=True):
 demand(load(root/'EVIDENCE_MANIFEST.json')=={k:v for k,v in inventory(root).items() if k!='EVIDENCE_MANIFEST.json'},'OBSERVATION_INVENTORY')
 demand(load(root/'SNAPSHOT_MANIFEST.json')==inventory(root/'snapshot'),'SNAPSHOT_INVENTORY')
 demand(set(inventory(root/'snapshot'))=={'member/wal/0000000000000000-0000000000000000.wal'},'BOUNDED_SNAPSHOT_FILES')
 d=model(root,load(observer_path));result=validate(d);tests=[]
 if negatives:
  for name in ['request_put_value','member_identity','commit_beyond_capture','missing_target_entry','retry_metadata','nonempty_compare_range','missing_compare_range','late_copy','changed_source_hash','wrong_trace_thread','missing_stop_confirmation','changed_task_state','wrong_trace_request','prepause_applied_mismatch','final_index_regression','wrong_trace_source','wrong_trace_bytecode','selected_index','selected_pid','selected_directory','selected_member_id','selected_endpoint']:
   v=copy.deepcopy(d)
   if name=='request_put_value':
    e=next(e for e in v['observer']['entries'] if e['index']==result['entry_index']);e['request']['txn']['success'][0]['requestPut']['value']=base64.b64encode(b'altered').decode()
   elif name=='member_identity':v['observer']['node_id']='1'
   elif name=='commit_beyond_capture':v['observer']['commit_index']=v['before_pause_status'][0]['Status']['raftIndex']+1
   elif name=='missing_target_entry':v['observer']['entries']=[e for e in v['observer']['entries'] if e['index']!=result['entry_index']]
   elif name=='retry_metadata':v['final_outbox']['kvs'][0]['version']+=1
   elif name=='nonempty_compare_range':next(e for e in v['observer']['entries'] if e['index']==result['entry_index'])['request']['txn']['compare'][0]['rangeEnd']='YWJj'
   elif name=='missing_compare_range':del next(e for e in v['observer']['entries'] if e['index']==result['entry_index'])['request']['txn']['compare'][0]['rangeEnd']
   elif name=='late_copy':v['SNAPSHOT_BOUNDARY']['end_monotonic_ns']=v['TRACE']['events'][1]['monotonic_ns']+1
   elif name=='changed_source_hash':v['SNAPSHOT_BOUNDARY']['source_sha256_after']='0'*64
   elif name=='wrong_trace_thread':v['TRACE']['events'][1]['thread_id']+=1
   elif name=='missing_stop_confirmation':v['PROCESS_EVENTS']=[e for e in v['PROCESS_EVENTS'] if e['action']!='stop_confirmed']
   elif name=='changed_task_state':v['SNAPSHOT_BOUNDARY']['tasks_after'][next(iter(v['SNAPSHOT_BOUNDARY']['tasks_after']))]='S'
   elif name=='wrong_trace_request':v['TRACE']['events'][1]['request_sha256']='0'*64
   elif name=='prepause_applied_mismatch':v['before_pause_status'][0]['Status']['raftAppliedIndex']-=1
   elif name=='final_index_regression':v['final_status'][0]['Status']['raftIndex']=v['final_status'][0]['Status']['raftAppliedIndex']=v['before_pause_status'][0]['Status']['raftIndex']-1
   elif name=='wrong_trace_source':v['TRACE']['source_sha256_before']=v['TRACE']['source_sha256_after']='0'*64
   elif name=='wrong_trace_bytecode':v['TRACE']['bytecode_sha256']='0'*64
   elif name=='selected_index':v['SELECTED_MEMBER']['index']=0
   elif name=='selected_pid':v['SELECTED_MEMBER']['pid']+=1
   elif name=='selected_directory':v['SELECTED_MEMBER']['directory']='/wrong/member'
   elif name=='selected_member_id':v['SELECTED_MEMBER']['member_id']='1'
   elif name=='selected_endpoint':v['SELECTED_MEMBER']['endpoint']='http://127.0.0.1:1'
   digest=hashlib.sha256(canonical(v).encode()).hexdigest()
   try:validate(v)
   except Exception as e:tests.append({'mutation':name,'recomputed_model_sha256':digest,'rejected':True,'reason':str(e)})
   else:raise RuntimeError('NEGATIVE_ACCEPTED_'+name)
 result['rehashed_model_negative_controls']=tests;return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('observations');ap.add_argument('observer_json');ap.add_argument('--output',required=True);a=ap.parse_args()
 try:r=check(Path(a.observations),Path(a.observer_json));code=0
 except Exception as e:r={'status':'REJECTED','error':type(e).__name__+': '+str(e),'controlling_pass':186,'classification':'NONCLAIM'};code=2
 save(Path(a.output),r);print(json.dumps(r));return code
if __name__=='__main__':raise SystemExit(main())

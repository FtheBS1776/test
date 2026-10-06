"""Independent offline binding of a bounded post-stop initial-segment control."""
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
  demand(c['result']=='EQUAL' and c.get('rangeEnd','')=='','COMPARE_OPERATION')
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
 names=['HTTP_EXCHANGES','CALLS','KEYS','FIXTURE_BINDING','SNAPSHOT_BOUNDARY','PROCESS_EVENTS','ENVELOPE'];d={n:load(root/(n+'.json')) for n in names};d['observer']=observed;d['SERVER_LOG']=[json.loads(line) for line in (root/'SERVER_0_START_0.txt').read_text().splitlines()]
 for n in ['parent_head','committed_head','committed_receipt','committed_execution','committed_outbox','final_head','final_receipt','final_execution','final_outbox','final_status','baseline_status']:
  r=load(root/(n+'.json'));demand(r['returncode']==0,'COMMAND_FAILED');d[n]=json.loads(r['stdout']);d[n+'_timing']={'start':r['start_monotonic_ns'],'end':r['end_monotonic_ns']}
 return d
def validate(d):
 obs=d['observer'];f=d['FIXTURE_BINDING'];final=d['final_status'][0]['Status'];base=d['baseline_status'][0]['Status']
 demand(obs['schema']=='WAL_CONTROL_V1' and obs['scope']=='POST_STOP_INITIAL_SEGMENT_COMMITTED_CONTROL','OBSERVER_SCOPE')
 demand(obs['cluster_id']==f['cluster_id']==str(final['header']['cluster_id'])==str(base['header']['cluster_id']),'CLUSTER_BINDING')
 demand(obs['node_id']==f['member_id']==str(final['header']['member_id'])==str(base['header']['member_id']),'MEMBER_BINDING')
 demand(obs['vote']==obs['node_id'] and final['leader']==int(obs['node_id']),'ONE_MEMBER_LEADER')
 demand(obs['term']==final['raftTerm']==final['header']['raft_term'],'TERM_BINDING')
 demand(obs['commit_index']==final['raftIndex']==final['raftAppliedIndex'],'FINAL_COMMIT_COVERAGE')
 entries=obs['entries'];demand([e['index'] for e in entries]==list(range(1,obs['commit_index']+1)),'CONTIGUOUS_COMPLETE_ENTRIES')
 for e in entries:
  demand(e['term']>0 and e['term']<=obs['term'] and hashlib.sha256(b64(e['data_b64'])).hexdigest()==e['sha256'],'ENTRY_RAW_BINDING')
 exits=[e for e in d['PROCESS_EVENTS'] if e['action']=='exit'];signals=[e for e in d['PROCESS_EVENTS'] if e['action']=='SIGTERM'];boundary=d['SNAPSHOT_BOUNDARY']
 demand(len(exits)==len(signals)==1 and exits[0]['returncode'] in (0,-15) and not any(e['action'] in ('cleanup_forced','SIGKILL') for e in d['PROCESS_EVENTS']),'CLEAN_EXIT')
 log=d['SERVER_LOG'];received=[i for i,v in enumerate(log) if v.get('msg')=='received signal; shutting down' and v.get('signal')=='terminated'];closed=[i for i,v in enumerate(log) if v.get('msg')=='closed etcd server' and v.get('data-dir')==boundary['source']]
 demand(len(received)==len(closed)==1 and received[0]<closed[0],'COMPLETED_SHUTDOWN_HANDLER')
 demand(d['final_status_timing']['end']<signals[0]['monotonic_ns']<exits[0]['monotonic_ns']<=boundary['start_monotonic_ns']<=boundary['end_monotonic_ns'],'POST_STOP_CHRONOLOGY')
 demand(boundary['mode']=='POST_CLEAN_PROCESS_EXIT' and boundary['raft_snapshot_count']==0,'CAPTURE_BOUNDARY')
 calls=d['CALLS'];ex=d['HTTP_EXCHANGES'];demand([c['label'] for c in calls]==['activation','exact_retry'] and all(c['outcome']=='OK' for c in calls) and calls[0]['result']==calls[1]['result'],'ADAPTER_RESULTS')
 demand(all(e['transport_error'] is None and e['response_b64'] is not None and e['authorization_present'] is False for e in ex),'HTTP_CONTROL_ERROR')
 txns=[(i,e) for i,e in enumerate(ex) if e['path']=='/v3/kv/txn'];demand(len(txns)==1,'ONE_ADAPTER_TXN')
 xi,exchange=txns[0];demand(calls[0]['exchange_start']<=xi<calls[0]['exchange_end'] and all(e['path']=='/v3/kv/range' for e in ex[calls[1]['exchange_start']:calls[1]['exchange_end']]),'RETRY_READ_ONLY')
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
 demand(len(candidates)==1,'EXACT_ENTRY_UNIQUE');target=candidates[0];demand(target['index']<=obs['commit_index'],'TARGET_COMMIT_SCOPE')
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
 return {'status':'PASS','scope':obs['scope'],'entry_index':target['index'],'entry_term':target['term'],'internal_request_id':target['request']['header']['ID'],'commit_index':obs['commit_index'],'node_id':obs['node_id'],'cluster_id':obs['cluster_id'],'shared_write_revision':revision,'adapter_txn_count':1,'exact_retry':'READ_ONLY_UNCHANGED_METADATA','controlling_pass':186,'classification':'NONCLAIM','promotion':False,'freeze':False,'live_pre_timeout_entry':'UNESTABLISHED'}
def check(root,observer_path,negatives=True):
 demand(load(root/'EVIDENCE_MANIFEST.json')=={k:v for k,v in inventory(root).items() if k!='EVIDENCE_MANIFEST.json'},'OBSERVATION_INVENTORY')
 demand(load(root/'SNAPSHOT_MANIFEST.json')==inventory(root/'snapshot'),'SNAPSHOT_INVENTORY')
 demand(set(inventory(root/'snapshot'))=={'member/wal/0000000000000000-0000000000000000.wal'},'BOUNDED_SNAPSHOT_FILES')
 d=model(root,load(observer_path));result=validate(d);tests=[]
 if negatives:
  for name in ['request_put_value','member_identity','commit_coverage','missing_target_entry','retry_metadata']:
   v=copy.deepcopy(d)
   if name=='request_put_value':
    e=next(e for e in v['observer']['entries'] if e['index']==result['entry_index']);e['request']['txn']['success'][0]['requestPut']['value']=base64.b64encode(b'altered').decode()
   elif name=='member_identity':v['observer']['node_id']='1'
   elif name=='commit_coverage':v['observer']['commit_index']-=1
   elif name=='missing_target_entry':v['observer']['entries']=[e for e in v['observer']['entries'] if e['index']!=result['entry_index']]
   elif name=='retry_metadata':v['final_outbox']['kvs'][0]['version']+=1
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

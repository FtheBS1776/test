"""Offline verification of task, authority records, destination and interruption chronology."""
import argparse,base64,copy,hashlib,json,sqlite3
from pathlib import Path
from owned_etcd import demand,save,sha
from report_worker import render
from execution_identity_reference import ExecutionEnvelope,SignedEnvelope,IssuerAuthorization,ExecutionIdentityVerifier
import stateful_subject as st
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def b64(s):return base64.b64decode(s,validate=True)
def model(out):
 d={'plan':load(out/'task/TASK.json'),'binding':load(out/'PLAN_BINDING.json'),'candidate':(out/'task/CANDIDATE.md').read_text(),'report':(out/'REPORT.md').read_text(),'input':(ROOT/'VERIFIED_INPUT.json').read_bytes().decode(),'negative':load(out/'MISMATCH_NEGATIVE.json'),'events':load(out/'PROCESS_EVENTS.json')}
 for label in ['first','resume','repeat']:
  d[label]={'process':load(out/(label+'_PROCESS.json')),'status':load(out/'task'/(label+'_STATUS.json')),'trace':load(out/'task'/(label+'_TRACE.json')),'sink_process':load(out/'task'/(label+'_SINK_PROCESS.json')),'sink':load(out/(label+'_SINK_SNAPSHOT.json')),'exchanges':load(out/'task'/(label+'_EXCHANGES.json')),'keys':{k:json.loads(load(out/(label+'_'+k+'.json'))['stdout']) for k in ['head','receipt','execution','outbox']}}
 return d

def validate(d):
 p=d['plan'];payload=d['candidate'];raw=d['input'].encode();h=hashlib.sha256(payload.encode()).hexdigest();tid=p['task_id'];eid=st.EID(tid,'publish','genie-report-inbox')
 demand(payload.encode()==render(raw) and d['report']==payload+'\n','REPORT_TRANSFORMATION')
 demand(p['input_sha256']==hashlib.sha256(raw).hexdigest()==p['envelope']['input_digest'] and h==p['result_sha256']==p['envelope']['result_digest'],'INPUT_RESULT_BINDING')
 auth=IssuerAuthorization(**{**p['issuer'],'public_key':bytes.fromhex(p['issuer']['public_key'])});env=ExecutionEnvelope(**p['envelope']);verified=ExecutionIdentityVerifier((auth,)).verify(SignedEnvelope(env,bytes.fromhex(p['signature'])));demand(verified==env,'FIXTURE_SIGNATURE')
 demand(env.execution_id==tid+'-execution' and env.subject_digest==p['programs']['report_worker.py'],'WORKER_EXECUTION_BINDING')
 for n,digest in p['programs'].items():demand(sha(ROOT/n)==digest,'PROGRAM_BINDING_'+n)
 effect={'effect_id':eid,'transition_id':tid,'kind':'publish','target':'genie-report-inbox','payload':payload,'generation':1,'authority_config':'C1'};body=json.dumps(effect,sort_keys=True,separators=(',',':'),ensure_ascii=False)
 wanted={'integrity':'ok','reports':[[eid,'genie-report-inbox',body,h]],'applications':[[eid,body]]}
 for label in ['first','resume','repeat']:
  c=d[label];demand(c['sink']==wanted,'EXACT_ONE_APPLICATION_'+label);demand(c['process']['start_monotonic_ns']<c['process']['end_monotonic_ns'],'PROCESS_INTERVAL')
  demand(c['status']['label']==label,'PROCESS_LABEL')
  trace=c['trace'];demand([t['event'] for t in trace[:3]]==['authority_result','governed_intent_read','delivery_process_returned'],'TRACE_EVENT_ORDER')
  demand(trace[0]['outcome']=='OK' and trace[0]['result']=={'generation':1,'head_digest':h,'authority_config':'C1'},'AUTHORITY_RESULT')
  demand(trace[1]['effect_id']==eid and trace[1]['payload_sha256']==h and trace[2]['worker_stdout_used_for_completion'] is False,'DELIVERY_BINDING')
  demand(c['process']['start_monotonic_ns']<=trace[0]['monotonic_ns']<=trace[1]['monotonic_ns']<=c['sink_process']['start_monotonic_ns']<=c['sink_process']['end_monotonic_ns']<=trace[2]['monotonic_ns']<=c['process']['end_monotonic_ns'],'INTENT_BEFORE_DELIVERY')
  ex=c['exchanges'];demand(all(e['authorization_present'] is False and e['transport_error'] is None and e['response_b64'] is not None for e in ex),'COMPLETE_FIXTURE_EXCHANGES')
  demand(all(json.loads(b64(e['request_b64'])).get('serializable') is False for e in ex if e['path']=='/v3/kv/range'),'LINEARIZABLE_READS')
  for k in ['head','receipt','execution','outbox']:demand(c['keys'][k]['kvs']==d['first']['keys'][k]['kvs'],'NO_AUTHORITY_RECORD_MUTATION_'+k)
 first=d['first'];demand(first['process']['returncode']==75 and first['sink_process']['returncode']==73 and first['sink_process']['stdout']=='' and first['status']['status']=='INTERRUPTED_BEFORE_ACK' and len(first['trace'])==3,'LOST_ACK_INTERRUPTION')
 for label in ['resume','repeat']:
  c=d[label];demand(c['process']['returncode']==c['sink_process']['returncode']==0 and json.loads(c['sink_process']['stdout'])=={'delivery':'DUPLICATE'},'DUPLICATE_DELIVERY')
  demand(c['status']['status']=='COMPLETE' and c['status']['completion_basis']=='FRESH_EXACT_DESTINATION_READBACK' and c['status']['effect_id']==eid and c['status']['payload_sha256']==h,'COMPLETION_SCOPE')
  demand(len(c['trace'])==4 and c['trace'][3]['event']=='destination_readback' and c['trace'][3]['disposition']=='CONFIRMED' and c['trace'][2]['monotonic_ns']<=c['trace'][3]['monotonic_ns']<=c['process']['end_monotonic_ns'],'READBACK_AFTER_DELIVERY')
  demand(all(e['path']=='/v3/kv/range' for e in c['exchanges']),'RESUME_AUTHORITY_READ_ONLY')
 demand(len({d[x]['status']['process_id'] for x in ['first','resume','repeat']})==3,'FRESH_PROCESS_IDS')
 demand(first['process']['end_monotonic_ns']<d['resume']['process']['start_monotonic_ns'] and d['resume']['process']['end_monotonic_ns']<d['repeat']['process']['start_monotonic_ns'],'SEPARATE_PROCESS_INTERVALS')
 txns=[e for x in ['first','resume','repeat'] for e in d[x]['exchanges'] if e['path']=='/v3/kv/txn'];demand(len(txns)==1,'ONE_AUTHORITY_TXN')
 request=json.loads(b64(txns[0]['request_b64']));reply=json.loads(b64(txns[0]['response_b64']));demand(reply['succeeded'] is True and len(request['success'])==4,'FOUR_ATOMIC_WRITES')
 revision=int(reply['header']['revision']);values={}
 for k,put in zip(['head','receipt','execution','outbox'],request['success']):
  rows=first['keys'][k]['kvs'];demand(len(rows)==1,'ONE_KEY_'+k);kv=rows[0]
  demand(kv['key']==put['requestPut']['key'] and kv['value']==put['requestPut']['value'] and int(kv['mod_revision'])==revision and int(kv['version'])==(2 if k=='head' else 1),'ATOMIC_BYTES_VERSION_'+k)
  if k!='head':demand(int(kv['create_revision'])==revision,'SINGLE_CREATE_'+k)
  values[k]=json.loads(b64(kv['value']))
 demand(values['outbox']==effect,'EXACT_GOVERNED_EFFECT')
 fp=st.FP(0,'TASK-READY',h,tid,'C1',(('publish','genie-report-inbox',payload),));envfp=hashlib.sha256(env.canonical()).hexdigest()
 demand(values['receipt']=={'transition_id':tid,'fingerprint':fp,'execution_id':env.execution_id,'envelope_fingerprint':envfp,'result':{'generation':1,'head_digest':h,'authority_config':'C1'}},'EXACT_RECEIPT')
 demand(values['execution']=={'execution_id':env.execution_id,'envelope_fingerprint':envfp,'transition_id':tid},'EXECUTION_BINDING')
 demand(values['head']['generation']==1 and values['head']['head_digest']==h,'ONE_HEAD_ADVANCE')
 demand(d['negative']['returncode']==2 and d['negative']['snapshot_after']==wanted,'MISMATCH_REJECT_UNCHANGED')
 starts=[e for e in d['events'] if e['action']=='start'];exits=[e for e in d['events'] if e['action']=='exit'];demand(len(starts)==len(exits)==1 and starts[0]['pid']==exits[0]['pid'] and exits[0]['returncode'] in (0,-15),'PROVIDER_CLEANUP')
 demand(not any(e['action'] in ('SIGKILL','cleanup_forced') for e in d['events']),'NO_FORCED_PROVIDER_CLEANUP')
 return {'status':'PASS','task':'verified-experiment-report','coordinator_processes':3,'authority_transactions':1,'sink_delivery_attempts':3,'sink_applications':1,'lost_ack_exit':73,'interrupted_coordinator_exit':75,'report_sha256':h,'atomic_revision':revision,'runtime_llm_calls':0,'classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False}

def check(out):
 expected=load(out/'EVIDENCE_MANIFEST.json');actual={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='EVIDENCE_MANIFEST.json'};demand(expected==actual,'EVIDENCE_INVENTORY')
 d=model(out);demand(sha(out/'task/TASK.json')==d['binding']['task_sha256'],'TASK_BYTES')
 result=validate(d)
 # Observe final database directly without trusting saved JSON or worker stdout.
 from report_sink import observe
 effect=json.loads(d['repeat']['sink']['reports'][0][2]);demand(observe(out/'task/report_inbox.sqlite',effect)=='CONFIRMED','ACTUAL_DESTINATION_READBACK')
 mutations={'duplicate_application':lambda v:v['repeat']['sink']['applications'].append(v['repeat']['sink']['applications'][0]),'wrong_payload':lambda v:v['plan'].__setitem__('result_sha256','0'*64),'fake_completion_before_ack':lambda v:v['first']['status'].__setitem__('status','COMPLETE'),'wrong_execution':lambda v:v['plan']['envelope'].__setitem__('execution_id','different'),'changed_outbox_metadata':lambda v:v['repeat']['keys']['outbox']['kvs'][0].__setitem__('version',2),'missing_readback':lambda v:v['resume']['trace'].pop(),'failed_destination':lambda v:v['resume']['sink'].__setitem__('reports',[]),'authority_repeated':lambda v:v['resume']['exchanges'].append(next(x for x in v['first']['exchanges'] if x['path']=='/v3/kv/txn'))}
 negatives=[]
 for name,fn in mutations.items():
  v=copy.deepcopy(d);fn(v)
  try:validate(v)
  except Exception as e:negatives.append({'mutation':name,'rejected':True,'reason':type(e).__name__+': '+str(e)})
  else:raise RuntimeError('MUTATION_ACCEPTED_'+name)
 result['negative_controls']=negatives;return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('observations');ap.add_argument('--output',required=True);a=ap.parse_args()
 try:r=check(Path(a.observations));code=0
 except Exception as e:r={'status':'INDETERMINATE_OR_REJECTED','error':type(e).__name__+': '+str(e),'classification':'NONCLAIM'};code=2
 save(Path(a.output),r);print(json.dumps(r));return code
if __name__=='__main__':raise SystemExit(main())

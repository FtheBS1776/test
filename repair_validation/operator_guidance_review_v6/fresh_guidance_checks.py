"""Fresh bounded fake-only observations of documented driver guidance. No mains/children."""
import copy, hashlib, inspect, io, json, pathlib, platform, sys
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=HERE/'input/GENIE_OPERATOR_GUIDANCE_REVIEW_INPUT_v6_20261018/source'
sys.path.insert(0,str(SOURCE));sys.dont_write_bytecode=True
from shared_interfaces import session_driver as driver
from run_queue import run_policy as q
EVIDENCE=HERE/'fresh_stores';EVIDENCE.mkdir()
quotes={role:{'max_micro_usd':1,'quote_ref':'fresh-review-fake-'+role} for role in ('author','repair','reviewer')}
records=[]
def setup(name,approved=quotes,attempts=1):
 folder=EVIDENCE/name;folder.mkdir();root=folder/'owned';root.mkdir();queue=folder/'queue.sqlite'
 run='fresh-'+name
 q.initialize(queue,{'run_id':run,'max_tasks':1,'max_model_calls':attempts,'effect_scope':'owned-local-report-inbox','cost_policy':{'mode':'ENABLE_LIMITED','limit_micro_usd':8,'authorization_ref':'FAKE_ONLY_NO_EXTERNAL_ENTRY','quotes':copy.deepcopy(approved)}})
 q.enqueue(queue,{'task_id':'document-task','goal':'Fresh fake-only guidance check','input_sha256':hashlib.sha256(name.encode()).hexdigest(),'max_attempts':attempts})
 return queue, {'check':{'queue':str(queue),'run_id':run,'owned_root':str(root)}}
def worker(a):
 return {'token':a['token'],'outcome':'OBSERVED_ACCEPTED','agent':'fresh-fake-author','evidence':{'fake_only':True},'text':'Fresh deterministic data for attempt '+str(a['token']['attempt'])}
def review(a):
 return {'token':a['token'],'candidate_hash':a['candidate_sha256'],'decision':'ACCEPT','reason':'Fresh deterministic fake-only review'}
def saved(queue):
 state=q.status(queue)
 with q.b.transaction(queue,False) as db:
  actions=[{'binding':json.loads(b),'max_micro_usd':m} for b,m in db.execute('SELECT binding,max_micro_usd FROM cost_actions ORDER BY rowid')]
 return {'status':state,'cost_actions':actions}
def retain(name,result,queue,**extra):
 entry={'case':name,'result':result,'saved':saved(queue),**extra};records.append(entry);print(json.dumps(entry,sort_keys=True),flush=True)

assert str(inspect.signature(driver.drive_run))=='(runs, run_name, worker, reviewer, max_actions=64, notify=None, costs=None)'
assert str(inspect.signature(driver.serve_run))=='(runs, run_name, input_stream=None, output_stream=None, max_actions=64, costs=None)'
assert driver.LINE_LIMIT==160000
print(json.dumps({'environment':platform.platform(),'python':sys.version,'signatures':'PASS','pins':'unchanged; transitive source loaders enabled'}),flush=True)

queue,runs=setup('omitted-costs');progress=[]
r=driver.drive_run(runs,'check',worker,review,notify=progress.append)
assert r['action']=='HOLD' and r['reason']=='COST_BOUND_UNKNOWN_OR_INVALID'
assert r['counts']['worker_hooks']==r['counts']['reviewer_hooks']==0
assert progress[0]['action']['action']=='INVOKE_WORKER' and saved(queue)['cost_actions']==[]
retain('omitted-costs',r,queue,progress=progress)

queue,runs=setup('approved-zero',approved={role:{'max_micro_usd':0,'quote_ref':'fresh-zero-'+role} for role in ('author','reviewer')})
zero={role:{'max_micro_usd':0,'quote_ref':'fresh-zero-'+role} for role in ('author','reviewer')}
r=driver.drive_run(runs,'check',worker,review,costs=zero)
assert r['action']=='STOP' and r['reason']=='ALL_TASKS_COMPLETE'
assert r['counts']['worker_hooks']==r['counts']['reviewer_hooks']==1
assert len(saved(queue)['cost_actions'])==2 and q.status(queue)['reserved_model_calls']==1
retain('approved-zero',r,queue)

queue,runs=setup('asserted-zero')
r=driver.drive_run(runs,'check',worker,review,costs={'author':{'max_micro_usd':0,'quote_ref':'unapproved-free-claim'}})
assert r['reason']=='COST_QUOTE_NOT_APPROVED' and r['counts']['worker_hooks']==0
retain('asserted-zero',r,queue)

queue,runs=setup('review-needs-own-admission');author_only={'author':quotes['author']}
r=driver.drive_run(runs,'check',worker,review,costs=author_only)
assert r['reason']=='COST_BOUND_UNKNOWN_OR_INVALID' and r['counts']['worker_hooks']==1 and r['counts']['reviewer_hooks']==0
assert len(saved(queue)['cost_actions'])==1 and q.status(queue)['reserved_model_calls']==1
second=driver.drive_run(runs,'check',worker,review,costs=quotes)
assert second['action']=='RECONCILE_REVIEW' and second['counts']['worker_hooks']==second['counts']['reviewer_hooks']==0
retain('review-needs-own-admission',r,queue,reentry=second)

queue,runs=setup('uncertain-hook')
def uncertain(a):raise RuntimeError('Fresh fake failure after admission')
r=driver.drive_run(runs,'check',uncertain,review,costs=quotes)
assert r['action']=='UNKNOWN' and r['counts']['worker_hooks']==1
assert len(saved(queue)['cost_actions'])==1 and q.status(queue)['cost_admission']['reserved_micro_usd']==1
second=driver.drive_run(runs,'check',worker,review,costs=quotes)
assert second['action']=='RECONCILE_WORKER' and second['counts']['worker_hooks']==second['counts']['reviewer_hooks']==0
retain('uncertain-hook',r,queue,reentry=second)

queue,runs=setup('bounded-repair',attempts=2)
def repair_then_accept(a):
 reply=review(a)
 if a['token']['attempt']==1:reply['decision']='REPAIR';reply['reason']='Fresh fake bounded repair'
 return reply
r=driver.drive_run(runs,'check',worker,repair_then_accept,costs=quotes)
assert r['action']=='STOP' and r['reason']=='ALL_TASKS_COMPLETE'
assert r['counts']['worker_hooks']==r['counts']['reviewer_hooks']==2
state=saved(queue)
assert len(state['cost_actions'])==4 and q.status(queue)['reserved_model_calls']==2
assert [a['binding']['role'] for a in state['cost_actions']]==['author','reviewer','repair','reviewer']
retain('bounded-repair',r,queue)

queue,runs=setup('stop-at-progress')
def stop_notify(message):
 if message['action']['action']=='INVOKE_WORKER':q.stop(queue,'HOST_ENDED')
r=driver.drive_run(runs,'check',worker,review,costs=quotes,notify=stop_notify)
assert r['action']=='STOP' and r['counts']['worker_hooks']==r['counts']['reviewer_hooks']==0
assert saved(queue)['cost_actions']==[]
retain('stop-at-progress',r,queue)

queue,runs=setup('stream-omitted-costs');output=io.BytesIO()
r=driver.serve_run(runs,'check',input_stream=io.BytesIO(b''),output_stream=output)
messages=[json.loads(line) for line in output.getvalue().splitlines()]
assert [m['kind'] for m in messages]==['progress','terminal'] and r['reason']=='COST_BOUND_UNKNOWN_OR_INVALID'
retain('stream-omitted-costs',r,queue,messages=messages)
print(json.dumps({'status':'PASS','fresh_scenarios':len(records),'external_model_or_tool_actions':0,'subject_mains':0,'child_processes':0}),flush=True)

import concurrent.futures,json,sqlite3,tempfile
from pathlib import Path
import run_policy as q
b=q.b

def main():
 checks=[]
 def reserve(path,req):return q.reserve(path,req,'test')
 def complete(path,ledger,sink):return q.complete(path,ledger,sink,'test')
 def reject(name,fn):
  try:fn()
  except (ValueError,sqlite3.Error,OSError):checks.append({'check':name,'rejected':True});return
  raise AssertionError(name)
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);queue=root/'queue';policy={'run_id':'test','max_tasks':2,'max_model_calls':1,'effect_scope':'owned-local-report-inbox'}
  reject('bool_budget',lambda:q.initialize(root/'bool',{**policy,'max_model_calls':True}));assert not (root/'bool').exists()
  incomplete=root/'incomplete';incomplete.touch();assert q.inspect(incomplete)['status']=='UNKNOWN';reject('incomplete_queue_preserved',lambda:q.initialize(incomplete,policy));assert incomplete.stat().st_size==0
  q.initialize(queue,policy);assert q.inspect(queue)['status']=='SCHEMA_PRESENT';checks.append({'check':'explicit_queue_schema_inspection','passed':True});p={'task_id':'one','goal':'First authorized task','input_sha256':'a'*64,'max_attempts':2};p2={**p,'task_id':'two','goal':'Second independent task'};q.enqueue(queue,p);q.enqueue(queue,p2);assert q.enqueue(queue,p)=='DUPLICATE';reject('plan_alias',lambda:q.enqueue(queue,{**p,'input_sha256':'b'*64}));reject('task_limit',lambda:q.enqueue(queue,{**p,'task_id':'three'}));assert q.next_task(queue)['task_id']=='one'
  req={'task_id':'one','goal':p['goal'],'input_sha256':p['input_sha256'],'attempt':1,'feedback':None}
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rs=list(pool.map(lambda _:reserve(queue,req),range(4)))
  assert sum(r['action']=='RESERVE_ONCE' for r in rs)==1 and q.status(queue)['reserved_model_calls']==1;checks.append({'check':'concurrent_reservation_one_charge','passed':True})
  reject('changed_duplicate_request',lambda:reserve(queue,{**req,'feedback':'changed'}));reject('unregistered_task',lambda:reserve(queue,{**req,'task_id':'missing'}));reject('wrong_input',lambda:reserve(queue,{**req,'input_sha256':'b'*64}))
  reject('wrong_run_reservation',lambda:q.reserve(queue,req,'other-run'))
  q.hold(queue,'one','UNKNOWN_DISPATCH');assert q.next_task(queue)=={'action':'STOP','reason':'CALL_BUDGET_EXHAUSTED'};assert reserve(queue,req)['action']=='RECONCILE_RESERVATION';checks.append({'check':'uncertain_call_charged_no_refund_or_redispatch','passed':True});reject('stopped_new_enqueue',lambda:q.enqueue(queue,{**p,'task_id':'three'}));assert q.stop(queue,'HOST_ENDED')['reason']=='CALL_BUDGET_EXHAUSTED'
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);queue=root/'queue';q.initialize(queue,{**policy,'max_model_calls':3});q.enqueue(queue,p);q.enqueue(queue,p2);q.next_task(queue);q.hold(queue,'one','SCOPED_DEPENDENCY_HOLD');assert q.next_task(queue)['task_id']=='two';checks.append({'check':'scoped_hold_does_not_block_independent_task','passed':True})
  req={**req,'task_id':'two','goal':p2['goal']};reserve(queue,req)
  ledger=root/'task';sink=root/'sink';b.initialize(ledger);b.create(ledger,p2);b.request(ledger);b.bind(ledger,1,'worker',p2['task_id'],p2['input_sha256']);b.submit(ledger,1,'worker','accepted output',p2['task_id'],p2['input_sha256']);b.review(ledger,1,b.digest('accepted output'),'ACCEPT','Checked',p2['task_id'],p2['input_sha256'])
  assert complete(queue,ledger,sink)['status']=='UNKNOWN';assert q.status(queue)['entries'][1]['state']=='ACTIVE';checks.append({'check':'acceptance_without_destination_not_complete','passed':True});b.report_sink.initialize(sink);b.deliver(ledger,sink)
  reject('wrong_run_completion',lambda:q.complete(queue,ledger,sink,'other-run'))
  with b.transaction(ledger) as cx:
   saved=cx.execute('SELECT request FROM attempts WHERE n=1').fetchone()[0];cx.execute('UPDATE attempts SET request=? WHERE n=1',(b.canon({**json.loads(saved),'feedback':'different feedback'}),))
  reject('completion_wrong_reserved_feedback',lambda:complete(queue,ledger,sink))
  with b.transaction(ledger) as cx:cx.execute('UPDATE attempts SET request=? WHERE n=1',(saved,))
  assert complete(queue,ledger,sink)['status']=='COMPLETE';assert complete(queue,ledger,sink)['status']=='DUPLICATE';checks.append({'check':'fresh_readback_completes_only_matching_task','passed':True});sink.unlink();assert complete(queue,ledger,sink)['status']=='UNKNOWN';checks.append({'check':'cached_completion_requires_fresh_destination','passed':True});assert q.next_task(queue)=={'action':'STOP','reason':'ONLY_HELD_TASKS'}
 with tempfile.TemporaryDirectory() as tmp:
  queue=Path(tmp)/'q';q.initialize(queue,policy);q.enqueue(queue,p);q.next_task(queue);reserve(queue,{'task_id':'one','goal':p['goal'],'input_sha256':p['input_sha256'],'attempt':1,'feedback':None});assert reserve(queue,{'task_id':'one','goal':p['goal'],'input_sha256':p['input_sha256'],'attempt':2,'feedback':'repair'})['action']=='STOP';assert q.next_task(queue)['action']=='RECONCILE_TASK';checks.append({'check':'exhausted_budget_still_allows_existing_task_reconciliation','passed':True})
 print(json.dumps({'status':'PASS','count':len(checks),'checks':checks},indent=2))
if __name__=='__main__':main()

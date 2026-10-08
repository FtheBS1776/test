import concurrent.futures,json,sqlite3,tempfile
from pathlib import Path
import journal as j
b=j.b

def main():
 checks=[]
 def reject(name,fn):
  try:fn()
  except (ValueError,sqlite3.Error):checks.append({'check':name,'rejected':True});return
  raise AssertionError(name)
 with tempfile.TemporaryDirectory() as tmp:
  db=Path(tmp)/'task';b.initialize(db);j.provision(db);plan={'task_id':'journal-test','goal':'Check invocation record','input_sha256':'a'*64,'max_attempts':2};b.create(db,plan);b.request(db);args={'n':1,'task_id':plan['task_id'],'input_sha256':plan['input_sha256']}
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rs=list(pool.map(lambda _:j.begin(db,**args),range(4)))
  assert sum(r['action']=='INVOKE_ONCE' for r in rs)==1;checks.append({'check':'concurrent_start_only_one_invoke','passed':True});call=rs[0]['call_id']
  assert j.status(db)['host_outcome']=='UNKNOWN';assert j.begin(db,**args)['action']=='RECONCILE_HOST';checks.append({'check':'started_not_launch_proof_or_redispatch','passed':True})
  reject('wrong_task_start',lambda:j.begin(db,**{**args,'task_id':'other'}))
  reject('wrong_call_result',lambda:j.observe(db,**args,call_id='wrong',outcome='OBSERVED_ACCEPTED',agent='a',evidence={'tool':'accepted'}))
  reject('wrong_input_result',lambda:j.observe(db,**{**args,'input_sha256':'b'*64},call_id=call,outcome='OBSERVED_ACCEPTED',agent='a',evidence={'tool':'accepted'}))
  event={**args,'call_id':call,'outcome':'UNKNOWN','agent':None,'evidence':{'reason':'tool reply lost'}};assert j.observe(db,**event)=='RECORDED';assert j.observe(db,**event)=='DUPLICATE';assert j.begin(db,**args)['action']=='RECONCILE_HOST';checks.append({'check':'unknown_receipt_persists_no_retry_permission','passed':True})
  event.update(outcome='OBSERVED_ACCEPTED',agent='existing-agent',evidence={'host_history':'observed accepted call'});j.observe(db,**event);assert b.status(db)['agent']=='existing-agent' and j.status(db)['host_outcome']=='OBSERVED_ACCEPTED';checks.append({'check':'observation_and_binding_atomic','passed':True})
  with b.transaction(db) as cx:
   saved=cx.execute('SELECT event_hash,body FROM host_observations WHERE call_id=? AND body LIKE ?',(call,'%OBSERVED_ACCEPTED%')).fetchone();cx.execute('UPDATE host_observations SET body=? WHERE call_id=? AND event_hash=?',(saved[1]+' ',call,saved[0]))
  assert j.status(db)['host_outcome']=='UNKNOWN';checks.append({'check':'corrupted_observation_hash_status_unknown','passed':True})
  with b.transaction(db) as cx:cx.execute('UPDATE host_observations SET body=? WHERE call_id=? AND event_hash=?',(saved[1],call,saved[0]))
  reject('replace_observed_agent',lambda:j.observe(db,**{**event,'agent':'other'}))
  reject('downgrade_confirmed_to_unknown',lambda:j.observe(db,**{**event,'outcome':'UNKNOWN','agent':None}))
  old_unknown={**event,'outcome':'UNKNOWN','agent':None,'evidence':{'reason':'tool reply lost'}};assert j.observe(db,**old_unknown)=='DUPLICATE';assert j.status(db)['host_outcome']=='OBSERVED_ACCEPTED';checks.append({'check':'old_unknown_duplicate_no_downgrade','passed':True})
  b.submit(db,1,'existing-agent','candidate',plan['task_id'],plan['input_sha256']);assert j.observe(db,**event)=='DUPLICATE';checks.append({'check':'exact_observation_replay_after_submit','passed':True});b.review(db,1,b.digest('candidate'),'REPAIR','Add missing checks',plan['task_id'],plan['input_sha256']);b.request(db)
  reject('new_stale_result_to_next_attempt',lambda:j.observe(db,**{**event,'evidence':{'new':'stale observation'}}))
  assert j.observe(db,**event)=='DUPLICATE';checks.append({'check':'historical_exact_replay_read_only','passed':True})
  nextargs={**args,'n':2};nextcall=j.begin(db,**nextargs);assert nextcall['call_id']!=call;checks.append({'check':'distinct_attempt_distinct_call','passed':True})
  with b.transaction(db) as cx:cx.execute('UPDATE host_calls SET request=? WHERE attempt=2',(b.canon({'task_id':'corrupted'}),))
  assert j.status(db)['host_outcome']=='UNKNOWN' and j.status(db)['reason']=='HOST_RECORD_INCONSISTENT';checks.append({'check':'corrupted_request_status_unknown','passed':True})
  reject('old_call_on_current_attempt',lambda:j.observe(db,**nextargs,call_id=call,outcome='OBSERVED_ACCEPTED',agent='existing-agent',evidence={'host':'accepted'}))
 print(json.dumps({'status':'PASS','count':len(checks),'checks':checks},indent=2))
if __name__=='__main__':main()

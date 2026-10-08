"""Targeted identity, uncertainty and replay checks; no provider/model invocation."""
import concurrent.futures,json,sqlite3,subprocess,sys,tempfile,shutil
from pathlib import Path
import bridge as b

def main():
 checks=[]
 def bind(db,n,agent):return b.bind(db,n,agent,task_id="bridge-test",input_sha256="a"*64)
 def submit(db,n,agent,text):return b.submit(db,n,agent,text,task_id="bridge-test",input_sha256="a"*64)
 def review(db,n,h,decision,reason):return b.review(db,n,h,decision,reason,task_id="bridge-test",input_sha256="a"*64)
 def reject(name,fn):
  try:fn()
  except (ValueError,sqlite3.Error,OSError):checks.append({'check':name,'rejected':True});return
  raise AssertionError(name)
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);db=root/'tasks.sqlite';sink=root/'sink.sqlite';plan={'task_id':'bridge-test','goal':'Write bounded operator memo','input_sha256':'a'*64,'max_attempts':2}
  reject('missing_ledger_no_provision',lambda:b.create(root/'missing',plan));assert not (root/'missing').exists()
  unfinished=root/'unfinished.sqlite';unfinished.touch();assert b.inspect(unfinished)['status']=='UNKNOWN';reject('incomplete_provisioning_preserved',lambda:b.initialize(unfinished));assert unfinished.stat().st_size==0
  clone=root/'clone';shutil.copytree(Path(b.__file__).parent,clone,ignore=shutil.ignore_patterns('trial','model_output','__pycache__'));dep=clone/'reused/report_sink.py';dep.write_text(dep.read_text()+'\n# changed dependency\n');child=subprocess.run([sys.executable,'-B',str(clone/'bridge.py'),str(db),'inspect'],capture_output=True,text=True);assert child.returncode!=0 and 'REUSED_SOURCE_BINDING' in child.stderr;checks.append({'check':'changed_reused_dependency_rejected','passed':True})
  b.initialize(db);assert b.inspect(db)['status']=='SCHEMA_PRESENT';b.create(db,plan);assert b.create(db,plan)=='DUPLICATE';reject('task_alias',lambda:b.create(db,{**plan,'input_sha256':'b'*64}))
  req=b.request(db);assert req['action']=='DISPATCH_ONCE';assert b.request(db)['action']=='RECONCILE_WORKER' and b.status(db)['dispatch_uncertain'];checks.append({'check':'dispatch_replay_no_blind_redispatch','passed':True})
  reject('candidate_before_agent_binding',lambda:submit(db,1,'agent','memo'))
  reject('cross_task_binding',lambda:b.bind(db,1,'agent',task_id='other',input_sha256='a'*64))
  bind(db,1,'agent');reject('cross_task_candidate',lambda:b.submit(db,1,'agent','memo',task_id='other',input_sha256='a'*64));reject('wrong_input_candidate',lambda:b.submit(db,1,'agent','memo',task_id='bridge-test',input_sha256='b'*64));reject('agent_alias',lambda:bind(db,1,'other'))
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(lambda _:submit(db,1,'agent','memo'),range(4)))
  assert out.count('SUBMITTED')==1 and out.count('DUPLICATE')==3;checks.append({'check':'concurrent_same_candidate_one_result','passed':True})
  reject('candidate_alias',lambda:submit(db,1,'agent','changed'))
  reject('cross_task_review',lambda:b.review(db,1,b.digest('memo'),'ACCEPT','checks passed',task_id='other',input_sha256='a'*64));reject('wrong_input_review',lambda:b.review(db,1,b.digest('memo'),'ACCEPT','checks passed',task_id='bridge-test',input_sha256='b'*64))
  reject('review_wrong_hash',lambda:review(db,1,'b'*64,'ACCEPT','checks passed'))
  reject('unaccepted_delivery',lambda:b.deliver(db,sink))
  review(db,1,b.digest('memo'),'REPAIR','Missing restart limitations');r=b.request(db);assert r['request']['feedback']=='Missing restart limitations'
  reject('stale_candidate',lambda:submit(db,1,'agent','memo'));reject('stale_review',lambda:review(db,1,b.digest('memo'),'ACCEPT','checks passed'))
  bind(db,2,'repair-agent');submit(db,2,'repair-agent','repaired memo');review(db,2,b.digest('repaired memo'),'ACCEPT','Bounded review passed')
  reject('review_alias',lambda:review(db,2,b.digest('repaired memo'),'REPAIR','Different decision'))
  b.report_sink.initialize(sink)
  proc=subprocess.run([sys.executable,'-B',str(Path(b.__file__)),str(db),'deliver','--sink',str(sink),'--crash','after_commit'],capture_output=True)
  assert proc.returncode==73 and b.status(db)['state']=='ACCEPTED';checks.append({'check':'lost_ack_preserves_pending','passed':True})
  proc=subprocess.run([sys.executable,'-B',str(Path(b.__file__)),str(db),'deliver','--sink',str(sink)],capture_output=True,text=True);assert proc.returncode==0;result=json.loads(proc.stdout);assert result=={'delivery':'DUPLICATE','completion':'CONFIRMED'}
  assert b.status(db,sink)['completion']=='CONFIRMED';checks.append({'check':'fresh_process_resume_one_destination_application','passed':True})
  with sqlite3.connect(sink) as cx:assert cx.execute('SELECT count(*) FROM applications').fetchone()[0]==1
  sink.unlink();assert b.status(db,sink)['completion']=='UNKNOWN';checks.append({'check':'cached_completion_missing_destination_unknown','passed':True})
  reject('missing_sink_not_recreated',lambda:b.deliver(db,sink));assert not sink.exists()
  with b.transaction(db) as cx:cx.execute("UPDATE attempts SET review=? WHERE n=2",(b.canon({'decision':'ACCEPT','candidate_sha256':'b'*64,'attempt':2}),))
  reject('damaged_review_binding',lambda:b.status(db,sink))
 # repair bound
 with tempfile.TemporaryDirectory() as temp:
  db=Path(temp)/'tasks';b.initialize(db);b.create(db,{**plan,'max_attempts':1});b.request(db);bind(db,1,'a');submit(db,1,'a','bad');review(db,1,b.digest('bad'),'REPAIR','Needs repair');assert b.request(db)['action']=='HOLD';checks.append({'check':'bounded_repair_no_infinite_loop','passed':True})
 print(json.dumps({'status':'PASS','checks':checks,'count':len(checks)},indent=2))
if __name__=='__main__':main()

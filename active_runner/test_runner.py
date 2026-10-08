import copy, json, sqlite3, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
import runner as r
q,j,b=r.q,r.j,r.b
class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.queue=self.root/'queue.sqlite';self.work=self.root/'work';self.work.mkdir();self.run='runner-test'
  self.plan={'task_id':'task','goal':'useful task','input_sha256':'a'*64,'max_attempts':2}
  q.initialize(self.queue,{'run_id':self.run,'max_tasks':2,'max_model_calls':2,'effect_scope':'owned-local-report-inbox'});q.enqueue(self.queue,self.plan)
 def tearDown(self):self.tmp.cleanup()
 def step(self):return r.step(self.queue,self.run,self.work)
 def dispatch(self):
  out=self.step();self.assertEqual(out['action'],'INVOKE_WORKER');return out['token']
 def cb(self,t,op,**kw):return r.callback(self.queue,self.run,self.work,op,t,**kw)
 def observe(self,t):return self.cb(t,'observe',outcome='OBSERVED_ACCEPTED',agent='worker',evidence={'host':'actual controller fixture'})
 def candidate(self,t):self.observe(t);self.cb(t,'submit',agent='worker',text='useful report');return self.step()
 def accepted(self,t):
  out=self.candidate(t);self.cb(t,'review',candidate_hash=out['candidate_sha256'],decision='ACCEPT',reason='checked')
 def files(self):return r.paths(self.work,self.run,self.plan['task_id'])
 def test_full_flow_and_stop(self):
  t=self.dispatch();self.accepted(t);self.assertEqual(self.step()['action'],'TASK_COMPLETE');self.assertEqual(self.step()['reason'],'ALL_TASKS_COMPLETE');self.assertEqual(q.status(self.queue)['reserved_model_calls'],1)
  _,_,sink=self.files()
  with b.transaction(sink,False) as db:self.assertEqual(db.execute('select count(*) from applications').fetchone()[0],1)
 def test_repeated_step_never_launches(self):
  self.dispatch();self.assertEqual(self.step()['action'],'RECONCILE_WORKER');self.assertEqual(q.status(self.queue)['reserved_model_calls'],1)
 def test_wrong_run_before_mutation(self):
  before=self.queue.read_bytes()
  with self.assertRaises(ValueError):r.step(self.queue,'wrong',self.work)
  self.assertEqual(before,self.queue.read_bytes())
 def test_each_token_binding(self):
  t=self.dispatch()
  for key in r.TOKEN_KEYS:
   x=copy.deepcopy(t);x[key]=9 if key=='attempt' else 'wrong'
   with self.subTest(key=key),self.assertRaises(ValueError):self.observe(x)
 def test_boolean_attempt_rejected(self):
  t=self.dispatch();t['attempt']=True
  with self.assertRaises(ValueError):self.observe(t)
 def test_extra_token_field_rejected(self):
  t=self.dispatch();t['source_path']='anything'
  with self.assertRaises(ValueError):self.observe(t)
 def test_submit_before_observation_rejected(self):
  t=self.dispatch()
  with self.assertRaises(ValueError):self.cb(t,'submit',agent='worker',text='report')
 def test_unknown_observation_no_launch(self):
  t=self.dispatch();self.cb(t,'observe',outcome='UNKNOWN',agent=None,evidence={'timeout':True});self.assertEqual(self.step()['action'],'RECONCILE_WORKER')
  with self.assertRaises(ValueError):self.cb(t,'submit',agent='worker',text='report')
 def test_wrong_agent_rejected(self):
  t=self.dispatch();self.observe(t)
  with self.assertRaises(ValueError):self.cb(t,'submit',agent='wrong',text='report')
 def test_exact_observation_replay_after_candidate(self):
  t=self.dispatch();self.candidate(t);self.assertEqual(self.observe(t),'DUPLICATE')
 def test_candidate_is_not_accepted(self):
  t=self.dispatch();out=self.candidate(t);self.assertEqual(out['action'],'REVIEW_CANDIDATE')
  _,_,sink=self.files()
  with b.transaction(sink,False) as db:self.assertEqual(db.execute('select count(*) from applications').fetchone()[0],0)
 def test_review_hash_rejected(self):
  t=self.dispatch();self.candidate(t)
  with self.assertRaises(ValueError):self.cb(t,'review',candidate_hash='b'*64,decision='ACCEPT',reason='wrong')
 def test_repair_new_attempt_old_callback_rejected(self):
  t=self.dispatch();out=self.candidate(t);self.cb(t,'review',candidate_hash=out['candidate_sha256'],decision='REPAIR',reason='improve');new=self.dispatch();self.assertEqual(new['attempt'],2)
  with self.assertRaises(ValueError):self.observe(t)
 def test_stopped_waiting_never_launches(self):
  self.dispatch();q.stop(self.queue,'HOST_ENDED');out=self.step();self.assertEqual(out['action'],'RECONCILE_WORKER');self.assertFalse(out['allow_new_invocation'])
 def test_stopped_accepted_does_not_deliver(self):
  t=self.dispatch();self.accepted(t);q.stop(self.queue,'AUTHORITY_BOUNDARY');self.assertEqual(self.step()['action'],'RECONCILE_DESTINATION')
  _,_,sink=self.files()
  with b.transaction(sink,False) as db:self.assertEqual(db.execute('select count(*) from applications').fetchone()[0],0)
 def test_stopped_existing_delivery_can_complete(self):
  t=self.dispatch();self.accepted(t);_,ledger,sink=self.files();b.deliver(ledger,sink);q.stop(self.queue,'HOST_ENDED');self.assertEqual(self.step()['action'],'TASK_COMPLETE');self.assertEqual(self.step()['reason'],'HOST_ENDED')
 def test_request_reserve_gap_preserved(self):
  t=self.dispatch();_,ledger,_=self.files()
  with b.transaction(self.queue) as db:db.execute('delete from reservations')
  self.assertEqual(self.step()['action'],'RECONCILE_SETUP');self.assertEqual(q.status(self.queue)['reserved_model_calls'],0)
  with self.assertRaises(ValueError):self.observe(t)
 def test_reserve_journal_gap_preserved(self):
  self.dispatch();_,ledger,_=self.files()
  with b.transaction(ledger) as db:db.execute('delete from host_calls')
  self.assertEqual(self.step()['action'],'RECONCILE_SETUP');self.assertEqual(q.status(self.queue)['reserved_model_calls'],1)
 def test_incomplete_directory_not_overwritten(self):
  folder,ledger,_=self.files();folder.mkdir(parents=True);ledger.write_bytes(b'incomplete');out=self.step();self.assertEqual(out['action'],'UNKNOWN');self.assertEqual(ledger.read_bytes(),b'incomplete')
 def test_incomplete_sink_not_overwritten(self):
  self.dispatch();_,_,sink=self.files();sink.write_bytes(b'incomplete');out=self.step();self.assertEqual(out['action'],'UNKNOWN');self.assertEqual(sink.read_bytes(),b'incomplete')
 def test_corrupt_host_observation_blocks_review(self):
  t=self.dispatch();self.candidate(t);_,ledger,_=self.files()
  with b.transaction(ledger) as db:db.execute("update host_observations set body='{}'")
  self.assertEqual(self.step()['action'],'UNKNOWN')
 def test_changed_reservation_blocks_callback(self):
  t=self.dispatch()
  with b.transaction(self.queue) as db:db.execute("update reservations set request='{}'")
  with self.assertRaises(ValueError):self.observe(t)
 def test_corrupt_candidate_blocks_review(self):
  t=self.dispatch();self.candidate(t);_,ledger,_=self.files()
  with b.transaction(ledger) as db:db.execute("update attempts set candidate='changed'")
  self.assertEqual(self.step()['action'],'UNKNOWN')
 def test_missing_sink_blocks_current_completion(self):
  t=self.dispatch();self.accepted(t);_,ledger,sink=self.files();b.deliver(ledger,sink);sink.unlink();self.assertEqual(self.step()['action'],'UNKNOWN');self.assertEqual(q.status(self.queue)['entries'][0]['state'],'ACTIVE')
 def test_budget_exhausted_repair_explicit_stop(self):
  with b.transaction(self.queue) as db:
   p,_,_=q.control(db);p['max_model_calls']=1;db.execute('update run set policy=?',(b.canon(p),))
  t=self.dispatch();out=self.candidate(t);self.cb(t,'review',candidate_hash=out['candidate_sha256'],decision='REPAIR',reason='improve')
  self.assertEqual(self.step()['reason'],'CALL_BUDGET_EXHAUSTED');self.assertEqual(q.status(self.queue)['state'],'STOPPED');self.assertEqual(self.step()['action'],'RECONCILE_SETUP')
 def test_stopped_unprovisioned_task_no_directory(self):
  q.next_task(self.queue);q.stop(self.queue,'HOST_ENDED');self.assertEqual(self.step()['action'],'RECONCILE_SETUP');self.assertFalse(self.files()[0].exists())
 def test_terminal_callback_rejected_documented(self):
  t=self.dispatch();self.accepted(t);self.step()
  with self.assertRaises(ValueError):self.observe(t)
 def test_corrupt_waiting_host_requires_inspection(self):
  t=self.dispatch();self.observe(t);_,ledger,_=self.files()
  with b.transaction(ledger) as db:db.execute("update host_observations set event_hash='corrupt'")
  out=self.step();self.assertEqual(out['action'],'UNKNOWN');self.assertTrue(out['preserve'])
 def test_actual_request_before_reserve_interruption(self):
  with patch.object(q,'reserve',side_effect=OSError('interrupted before reserve')):self.assertEqual(self.step()['action'],'UNKNOWN')
  out=self.step();self.assertEqual(out['action'],'RECONCILE_SETUP');self.assertEqual(out['reason'],'RESERVATION_MISSING_RECONCILE_SETUP');self.assertEqual(q.status(self.queue)['reserved_model_calls'],0)
 def test_actual_reserve_before_journal_interruption(self):
  with patch.object(j,'begin',side_effect=OSError('interrupted before journal')):self.assertEqual(self.step()['action'],'UNKNOWN')
  out=self.step();self.assertEqual(out['action'],'RECONCILE_SETUP');self.assertEqual(out['reason'],'HOST_CALL_MISSING_RECONCILE_SETUP');self.assertEqual(q.status(self.queue)['reserved_model_calls'],1)
 def test_same_request_other_run_token_rejects(self):
  t=self.dispatch();other=self.root/'other.sqlite';other_run='another-run'
  q.initialize(other,{'run_id':other_run,'max_tasks':1,'max_model_calls':2,'effect_scope':'owned-local-report-inbox'});q.enqueue(other,self.plan)
  other_token=r.step(other,other_run,self.work)['token'];self.assertEqual(t['slot_id'],other_token['slot_id']);self.assertEqual(t['call_id'],other_token['call_id'])
  with self.assertRaises(ValueError):r.callback(other,other_run,self.work,'observe',t,outcome='OBSERVED_ACCEPTED',agent='worker',evidence={'test':True})
 def test_exact_candidate_review_replays(self):
  t=self.dispatch();out=self.candidate(t);self.assertEqual(self.cb(t,'submit',agent='worker',text='useful report'),'DUPLICATE')
  fields={'candidate_hash':out['candidate_sha256'],'decision':'ACCEPT','reason':'checked'};self.cb(t,'review',**fields);self.assertEqual(self.cb(t,'review',**fields),'DUPLICATE')
if __name__=='__main__':unittest.main()

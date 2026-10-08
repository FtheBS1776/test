import hashlib,json,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import runner as r
import run_status as s
q,j,b=r.q,r.j,r.b
class StatusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.work=self.root/'work';self.work.mkdir();self.queue=self.root/'queue.sqlite';self.run='status-test'
  self.plan={'task_id':'task','goal':'read-only status','input_sha256':'a'*64,'max_attempts':2}
  q.initialize(self.queue,{'run_id':self.run,'max_tasks':1,'max_model_calls':2,'effect_scope':'owned-local-report-inbox'});q.enqueue(self.queue,self.plan)
 def tearDown(self):self.tmp.cleanup()
 def report(self):return s.report(self.queue,self.run,self.work)
 def task(self):return self.report()['tasks'][0]
 def dispatch(self):return r.step(self.queue,self.run,self.work)['token']
 def cb(self,t,op,**kw):return r.callback(self.queue,self.run,self.work,op,t,**kw)
 def accepted(self):
  t=self.dispatch();self.cb(t,'observe',outcome='OBSERVED_ACCEPTED',agent='worker',evidence={'fixture':True});self.cb(t,'submit',agent='worker',text='PRIVATE_SENTINEL_PAYLOAD');self.cb(t,'review',candidate_hash=b.digest('PRIVATE_SENTINEL_PAYLOAD'),decision='ACCEPT',reason='fixture check');return t
 def files(self):return r.paths(self.work,self.run,self.plan['task_id'])
 def hashes(self):return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
 def test_ready_missing_task_unknown_no_creation(self):
  before=self.hashes();out=self.task();self.assertEqual(out['workflow']['status'],'UNKNOWN');self.assertEqual(before,self.hashes())
 def test_waiting_host_unknown(self):
  self.dispatch();out=self.task();self.assertEqual(out['workflow']['state'],'WAITING_WORKER');self.assertEqual(out['journal']['host_outcome'],'UNKNOWN');self.assertEqual(out['fresh_sink']['status'],'UNKNOWN')
 def test_accepted_not_delivered_unknown(self):self.accepted();self.assertEqual(self.task()['fresh_sink']['status'],'UNKNOWN')
 def test_complete_fresh_readback_separate(self):
  self.accepted();r.step(self.queue,self.run,self.work);r.step(self.queue,self.run,self.work);out=self.report();self.assertEqual(out['queue_history']['state'],'STOPPED');self.assertEqual(out['tasks'][0]['queue_entry_history'],'COMPLETE');self.assertEqual(out['tasks'][0]['fresh_sink']['status'],'CONFIRMED')
 def test_missing_sink_after_complete_no_false_completion(self):
  self.accepted();r.step(self.queue,self.run,self.work);_,_,sink=self.files();sink.unlink();out=self.task();self.assertEqual(out['queue_entry_history'],'COMPLETE');self.assertEqual(out['fresh_sink']['status'],'UNKNOWN');self.assertFalse(sink.exists())
 def test_changed_sink_mismatch_preserves_history(self):
  self.accepted();r.step(self.queue,self.run,self.work);_,_,sink=self.files()
  with b.transaction(sink) as db:db.execute("update reports set payload_sha256='wrong'")
  before=self.hashes();out=self.task();self.assertEqual(out['fresh_sink']['status'],'MISMATCH');self.assertEqual(out['queue_entry_history'],'COMPLETE');self.assertEqual(before,self.hashes())
 def test_corrupt_journal_unknown(self):
  t=self.dispatch();self.cb(t,'observe',outcome='OBSERVED_ACCEPTED',agent='worker',evidence={'fixture':True});_,ledger,_=self.files()
  with b.transaction(ledger) as db:db.execute("update host_observations set event_hash='wrong'")
  self.assertEqual(self.task()['journal']['status'],'UNKNOWN')
 def test_partial_ledger_preserved(self):
  self.dispatch();_,ledger,_=self.files();ledger.write_bytes(b'partial');before=self.hashes();self.assertEqual(self.task()['workflow']['status'],'UNKNOWN');self.assertEqual(before,self.hashes())
 def test_wrong_run_no_task_paths(self):
  before=self.hashes()
  with patch.object(r,'paths',side_effect=AssertionError('no task inspection')),self.assertRaises(ValueError):s.report(self.queue,'wrong',self.work)
  self.assertEqual(before,self.hashes())
 def test_no_payload_disclosure(self):
  self.accepted();out=json.dumps(self.report());self.assertNotIn('PRIVATE_SENTINEL_PAYLOAD',out);self.assertNotIn('candidate',out)
 def test_readonly_transaction_rejects_writes(self):
  with s.readonly(self.queue) as db:
   with self.assertRaises(sqlite3.OperationalError):db.execute("update run set state='STOPPED'")
 def test_diagnostic_avoids_rw_helpers(self):
  self.accepted();before=self.hashes()
  with patch.object(b,'transaction',side_effect=AssertionError('rw helper forbidden')):self.assertEqual(self.report()['status'],'PASS')
  self.assertEqual(before,self.hashes())
 def test_cli_json_wrong_run_exit(self):
  p=subprocess.run([sys.executable,'-B',str(Path(s.__file__)),str(self.queue),'wrong',str(self.work)],capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout)['reason'],'RUN_CONTEXT_BINDING')
 def test_cli_valid_readonly_json(self):
  self.accepted();before=self.hashes();p=subprocess.run([sys.executable,'-B',str(Path(s.__file__)),str(self.queue),self.run,str(self.work)],capture_output=True,text=True);self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['status'],'PASS');self.assertEqual(before,self.hashes())
if __name__=='__main__':unittest.main()

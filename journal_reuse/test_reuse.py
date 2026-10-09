import ast,hashlib,json,sqlite3,sys,tempfile,types,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'active_runner'))
import runner as r
import run_status as s
j,b=r.j,r.b
BASE=Path(__file__).resolve().parent/'baseline'
def legacy(name, original):
 mod=types.ModuleType('legacy_'+name);mod.__file__=str(original)
 raw=(BASE/name).read_text();exec(compile(raw,str(BASE/name),'exec'),mod.__dict__);return mod
old_s=legacy('run_status.py',Path(s.__file__))
old_j=legacy('journal.py',Path(j.__file__))
class ReuseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'task.sqlite';self.plan={'task_id':'reuse-test','goal':'Check original diagnostics','input_sha256':'a'*64,'max_attempts':2}
  b.initialize(self.path);j.provision(self.path);b.create(self.path,self.plan);b.request(self.path);self.call=j.begin(self.path,1,self.plan['task_id'],self.plan['input_sha256'])['call_id']
 def tearDown(self):self.tmp.cleanup()
 def observe(self,outcome='OBSERVED_ACCEPTED'):
  j.observe(self.path,1,self.plan['task_id'],self.plan['input_sha256'],self.call,outcome,'worker' if outcome=='OBSERVED_ACCEPTED' else None,{'fixture':True})
 def compare(self):
  with s.readonly(self.path) as db:
   task,plan,state,n=b.read(db);plan=json.loads(plan)
   a=old_s.journal_readback(db,b,task,plan,state,n);c=s.journal_readback(db,r,task,plan,state,n)
   self.assertEqual(a,c)
  return c
 def request(self, mutate):
  with b.transaction(self.path) as db:
   req=json.loads(db.execute('select request from attempts where n=1').fetchone()[0]);req=mutate(req);body=b.canon(req);call=b.digest(b.canon({'kind':'host-invoke-v1','request':req}))
   db.execute('update attempts set request=? where n=1',(body,));db.execute('update host_calls set request=?,call_id=? where attempt=1',(body,call));self.call=call
 def event(self,mutate,rehash=True):
  with b.transaction(self.path) as db:
   event=json.loads(db.execute('select body from host_observations').fetchone()[0]);event=mutate(event);body=b.canon(event);sha=b.digest(body) if rehash else 'wrong';db.execute('update host_observations set body=?,event_hash=?',(body,sha))
 def test_body_ast_identical(self):
  old=next(x for x in ast.parse((BASE/'journal.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='status').body[0].body
  new=next(x for x in ast.parse(Path(j.__file__).read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='status_db').body[1:]
  self.assertEqual(ast.dump(ast.Module(body=old,type_ignores=[])),ast.dump(ast.Module(body=new,type_ignores=[])))
 def test_no_events_same(self):self.assertEqual(self.compare()['status'],'OBSERVED')
 def test_unknown_event_same(self):self.observe('UNKNOWN');self.assertEqual(self.compare()['host_outcome'],'UNKNOWN')
 def test_accepted_same(self):self.observe();self.assertEqual(self.compare()['host_outcome'],'OBSERVED_ACCEPTED')
 def test_no_call_same(self):
  with b.transaction(self.path) as db:db.execute('delete from host_calls')
  self.assertEqual(self.compare()['reason'],'NO_RECORDED_HOST_CALL')
 def test_schema_before_no_call_same(self):
  with b.transaction(self.path) as db:db.execute('delete from host_calls');db.execute('drop table host_observations')
  self.assertTrue(self.compare()['preserve'])
 def test_changed_goal_retained(self):
  self.request(lambda req:{**req,'goal':'changed'});self.assertEqual(self.compare()['status'],'UNKNOWN');self.assertEqual(j.status(self.path)['host_outcome'],'UNKNOWN')
 def test_missing_goal_retained(self):
  self.request(lambda req:{k:v for k,v in req.items() if k!='goal'});self.assertTrue(self.compare()['preserve'])
 def test_request_bool_retained(self):self.request(lambda req:{**req,'attempt':True});self.assertTrue(self.compare()['preserve'])
 def test_request_float_retained(self):self.request(lambda req:{**req,'attempt':1.0});self.assertTrue(self.compare()['preserve'])
 def test_event_bool_retained(self):self.observe();self.event(lambda e:{**e,'attempt':True});self.assertTrue(self.compare()['preserve'])
 def test_event_float_retained(self):self.observe('UNKNOWN');self.event(lambda e:{**e,'attempt':1.0});self.assertTrue(self.compare()['preserve'])
 def test_request_list_contained(self):self.request(lambda req:[]);self.assertTrue(self.compare()['preserve'])
 def test_request_null_contained(self):self.request(lambda req:None);self.assertTrue(self.compare()['preserve'])
 def test_event_list_contained(self):self.observe();self.event(lambda e:[]);self.assertTrue(self.compare()['preserve'])
 def test_event_null_contained(self):self.observe();self.event(lambda e:None);self.assertTrue(self.compare()['preserve'])
 def test_hash_corruption_same_reset(self):
  self.observe();self.event(lambda e:e,False);out=self.compare();self.assertEqual((out['call_id'],out['agent'],out['observation_count']),(None,None,0))
 def test_agent_mismatch_same(self):
  self.observe()
  with b.transaction(self.path) as db:db.execute("update attempts set agent='other'")
  self.assertTrue(self.compare()['preserve'])
 def test_missing_attempt_same(self):
  with b.transaction(self.path) as db:db.execute('delete from attempts')
  self.assertTrue(self.compare()['preserve'])
 def test_old_wrapper_result_equal(self):
  self.observe();self.assertEqual(old_j.status(self.path),j.status(self.path))
 def test_old_wrapper_malformed_exception_equal(self):
  self.request(lambda req:[])
  with self.assertRaises(AttributeError):old_j.status(self.path)
  with self.assertRaises(AttributeError):j.status(self.path)
 def test_caller_ro_transaction_stays_open(self):
  self.observe();before=self.path.read_bytes()
  with s.readonly(self.path) as db:
   with patch.object(b,'transaction',side_effect=AssertionError('connection reopen forbidden')):
    self.assertEqual(j.status_db(db)['host_outcome'],'OBSERVED_ACCEPTED');self.assertTrue(db.in_transaction);self.assertEqual(db.execute('select count(*) from task').fetchone()[0],1)
    with self.assertRaises(sqlite3.OperationalError):db.execute("update attempts set agent='other'")
  self.assertEqual(before,self.path.read_bytes())
 def test_diagnostic_uses_shared_validator(self):
  with patch.object(j,'status_db',wraps=j.status_db) as shared:self.compare();self.assertEqual(shared.call_count,1)
 def test_independent_sink_evidence_survives_journal_corruption(self):
  owned=Path(self.tmp.name)/'owned';owned.mkdir();run='reuse-run';folder,ledger,sink=r.paths(owned,run,self.plan['task_id']);folder.mkdir(parents=True);self.path.rename(ledger);self.path=ledger;b.report_sink.initialize(sink)
  self.observe();b.submit(ledger,1,'worker','private report',self.plan['task_id'],self.plan['input_sha256']);b.review(ledger,1,b.digest('private report'),'ACCEPT','fixture',self.plan['task_id'],self.plan['input_sha256']);b.deliver(ledger,sink);self.event(lambda e:e,False)
  before={str(p):p.read_bytes() for p in (ledger,sink)}
  a=old_s.task_report(r,owned,run,self.plan['task_id'],b.canon(self.plan),'COMPLETE');c=s.task_report(r,owned,run,self.plan['task_id'],b.canon(self.plan),'COMPLETE');self.assertEqual(a,c);self.assertEqual(c['journal']['status'],'UNKNOWN');self.assertEqual(c['fresh_sink']['status'],'CONFIRMED');self.assertEqual(c['workflow']['state'],'DELIVERED');self.assertEqual(before,{str(p):p.read_bytes() for p in (ledger,sink)})
 def test_changed_runner_source_pin_rejects(self):
  active=Path(self.tmp.name)/'active_runner';active.mkdir();(active/'run_status.py').write_bytes(Path(s.__file__).read_bytes());(active/'runner.py').write_bytes(Path(r.__file__).read_bytes()+b'\n')
  result=subprocess.run([sys.executable,'-B',str(active/'run_status.py'),str(self.path),'wrong','missing-root'],capture_output=True,text=True);self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['status'],'REJECT')
if __name__=='__main__':unittest.main()

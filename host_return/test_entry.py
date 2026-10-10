"""Focused entry checks only. NO MODEL CALL; accepted core fixtures not rerun."""
import contextlib,importlib.util,io,json,pathlib,tempfile,types,unittest
from unittest.mock import Mock,patch
ROOT=pathlib.Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('entry',ROOT/'shared_interfaces/candidate/work_host.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=pathlib.Path(self.tmp.name)/'registry.json';self.path.write_text(json.dumps({'a':{'queue':'existing.sqlite','run_id':'existing-run','owned_root':'work'}}));self.cli=m._load('cli.py');self.calls=Mock(return_value={'action':'STOP','reason':'ALL_TASKS_COMPLETE'});self.driver=types.SimpleNamespace(serve_run=self.calls);self.args=['--registry',str(self.path),'--run','a'];self.output=io.StringIO()
 def main(self,args=None):
  with patch.object(m,'_load',side_effect=lambda n:self.cli if n=='cli.py' else self.driver),contextlib.redirect_stdout(self.output):return m.main(self.args if args is None else args)
 def test_one_serve_call_normalized_registry_and_bound(self):
  self.assertEqual(self.main(self.args+['--max-actions','7']),0);self.calls.assert_called_once();args,kw=self.calls.call_args;self.assertEqual(args[0]['a']['queue'],str(self.path.parent/'existing.sqlite'));self.assertEqual(args[1],'a');self.assertEqual(kw,{'max_actions':7})
 def test_unknown_returns_nonzero_without_output_replay(self):
  self.calls.return_value={'action':'UNKNOWN','preserve':True,'allow_new_invocation':False};self.assertEqual(self.main(),3);self.calls.assert_called_once();self.assertEqual(self.output.getvalue(),'')
 def test_stop_other_reason_is_not_success(self):
  self.calls.return_value={'action':'STOP','reason':'HOST_ENDED'};self.assertEqual(self.main(),4);self.calls.assert_called_once()
 def test_hold_reconcile_reject_exit_distinctions(self):
  for action,code in [('HOLD',4),('RECONCILE_REVIEW',4),('REJECT',2)]:
   self.calls.reset_mock();self.calls.return_value={'action':action};self.assertEqual(self.main(),code);self.calls.assert_called_once()
 def test_postentry_exception_unknown_no_retry(self):
  self.calls.side_effect=RuntimeError('secret');self.assertEqual(self.main(),3);self.calls.assert_called_once();result=json.loads(self.output.getvalue())['result'];self.assertEqual(result['action'],'UNKNOWN');self.assertTrue(result['preserve']);self.assertFalse(result['allow_new_invocation']);self.assertNotIn('secret',self.output.getvalue())
 def test_invalid_registry_rejects_before_serve(self):
  self.path.write_text('{"a":NaN}');self.assertEqual(self.main(),2);self.calls.assert_not_called();self.assertEqual(json.loads(self.output.getvalue())['result']['action'],'REJECT')
 def test_unknown_alias_rejects_before_serve(self):
  self.assertEqual(self.main(['--registry',str(self.path),'--run','absent']),2);self.calls.assert_not_called()
 def test_bad_arguments_preentry(self):
  for extra in [['--max-actions','0'],['--max-actions','129'],['--max-actions','True'],['--run','a'],['--reg','x']]:
   self.assertEqual(self.main(self.args+extra),2);self.calls.assert_not_called()
 def test_source_pin_failure_preentry(self):
  with patch.object(m.Path,'read_bytes',return_value=b'bad'),contextlib.redirect_stdout(self.output):self.assertEqual(m.main(self.args),2)
  self.assertEqual(json.loads(self.output.getvalue())['result']['action'],'REJECT')
if __name__=='__main__':unittest.main(verbosity=2)

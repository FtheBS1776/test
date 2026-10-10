import copy, hashlib, importlib.util, json, pathlib, tempfile, types, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("control_candidate",ROOT/"shared_interfaces/candidate/run_control.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.q=self.root/"q.sqlite";self.work=self.root/"work";self.work.mkdir()
  from shared_interfaces.status_tool import _load_core
  self.runner=_load_core().load_runner();self.policy={"run_id":"test-control-new","max_tasks":1,"max_model_calls":1,"effect_scope":"owned-local-report-inbox"};self.plan={"task_id":"task-new","goal":"check new interface action forwarding","input_sha256":"a"*64,"max_attempts":1}
  self.runner.q.initialize(self.q,self.policy);self.runner.q.enqueue(self.q,self.plan)
  self.registry={"a":{"queue":str(self.q),"run_id":self.policy["run_id"],"owned_root":str(self.work)}};self.host=m.GenieRunController(self.registry)
 def invoke(self):return self.host.call("advance_run",{"run_name":"a"})
 def replacement(self,step):
  facade=m._load_facade();return patch.object(m,"_load_facade",return_value=facade),patch.object(facade,"_load_core",return_value=types.SimpleNamespace(load_runner=lambda:types.SimpleNamespace(step=step,context=self.runner.context)))
 def test_invalid_arguments_before_core(self):
  with patch.object(m,"_load_facade",side_effect=AssertionError("loaded")):
   for value in [None,[],{}, {"run_name":1},{"run_name":"a","queue":"x"}]:self.assertEqual(self.host.call("advance_run",value)["status"],"REJECT")
 def test_unknown_alias_before_core(self):
  with patch.object(m,"_load_facade",side_effect=AssertionError("loaded")):self.assertEqual(self.host.call("advance_run",{"run_name":"absent"})["status"],"REJECT")
 def test_unsupported_tool(self):
  for name in ["submit","review","observe","get_run_status",None]:self.assertEqual(self.host.call(name,{"run_name":"a"})["status"],"REJECT")
 def test_metadata_mutating_detached(self):
  one=self.host.tools();self.assertEqual(len(one),1);self.assertEqual(one[0]["name"],"advance_run");self.assertFalse(one[0]["annotations"]["readOnlyHint"]);self.assertFalse(one[0]["annotations"]["idempotentHint"]);one[0]["name"]="bad";self.assertEqual(self.host.tools()[0]["name"],"advance_run");self.assertNotIn(str(self.root),json.dumps(self.host.tools()))
 def test_registry_detached(self):
  self.registry["a"]["queue"]="absent";self.registry.clear();self.assertEqual(self.invoke()["action"],"INVOKE_WORKER")
 def test_source_mismatch_before_step(self):
  with patch.object(m.Path,"read_bytes",return_value=b"bad"):self.assertEqual(self.invoke()["status"],"REJECT")
  self.assertEqual(list(self.work.iterdir()),[])
 def test_fresh_then_reconcile(self):
  first=self.invoke();self.assertEqual(first["action"],"INVOKE_WORKER");second=self.invoke();self.assertEqual(second["action"],"RECONCILE_WORKER");self.assertFalse(second["allow_new_invocation"]);self.assertEqual(first["token"],second["token"])
  with self.runner.b.transaction(self.q,False) as db:self.assertEqual(db.execute("SELECT count(*) FROM reservations").fetchone()[0],1)
 def test_commit_then_exception(self):
  def step(*args):self.runner.step(*args);raise RuntimeError("secret /private/path")
  p1,p2=self.replacement(step)
  with p1,p2:out=self.invoke()
  self.assertEqual(out["action"],"UNKNOWN");self.assertTrue(out["preserve"]);self.assertFalse(out["allow_new_invocation"]);self.assertNotIn("secret",json.dumps(out))
  with self.runner.b.transaction(self.q,False) as db:self.assertEqual(db.execute("SELECT count(*) FROM reservations").fetchone()[0],1)
  self.assertEqual(self.invoke()["action"],"RECONCILE_WORKER")
 def test_malformed_poststep(self):
  for value in [None,[],{}, {"action":"IMAGINARY"},{"action":"INVOKE_WORKER"},{"action":"REVIEW_CANDIDATE"}]:
   count=[]
   def step(*a):count.append(1);return value
   p1,p2=self.replacement(step)
   with p1,p2:out=self.invoke()
   self.assertEqual(count,[1]);self.assertEqual(out["action"],"UNKNOWN");self.assertFalse(out["allow_new_invocation"])
 def test_core_actions_verbatim_once(self):
  for action in ["STOP","HOLD","UNKNOWN","RECONCILE_SETUP","RECONCILE_HOST"]:
   value={"action":action,"reason":"fixed","allow_new_invocation":False};count=[]
   def step(*a):count.append(a);return value
   p1,p2=self.replacement(step)
   with p1,p2:out=self.invoke()
   self.assertEqual(out,value);self.assertEqual(len(count),1)
 def test_stopped_run_no_dispatch(self):
  self.runner.q.stop(self.q,"AUTHORITY_BOUNDARY");out=self.invoke();self.assertEqual(out["action"],"STOP");self.assertEqual(out["reason"],"AUTHORITY_BOUNDARY");self.assertEqual(list(self.work.iterdir()),[])
 def test_wrong_run_no_new_invocation(self):
  h=m.GenieRunController({"a":{**self.registry["a"],"run_id":"other"}});out=h.call("advance_run",{"run_name":"a"});self.assertEqual(out["status"],"REJECT");self.assertEqual(out["reason"],"CORE_LOAD_OR_CONTEXT_FAILURE");self.assertEqual(list(self.work.iterdir()),[])
 def test_readonly_catalog_unchanged(self):
  from shared_interfaces.status_tool import GenieStatusTools
  self.assertEqual([v["name"] for v in GenieStatusTools(self.registry).tools()],["get_run_status","get_task_result"])
if __name__=="__main__":unittest.main(verbosity=2)

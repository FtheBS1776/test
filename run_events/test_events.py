import copy,hashlib,importlib.util,json,pathlib,tempfile,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("events_candidate",ROOT/"shared_interfaces/candidate/run_events.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.q=self.root/"q.sqlite";self.work=self.root/"work";self.work.mkdir()
  from shared_interfaces.status_tool import _load_core
  from shared_interfaces.run_control import GenieRunController
  self.runner=_load_core().load_runner();policy={"run_id":"events-test-new","max_tasks":1,"max_model_calls":2,"effect_scope":"owned-local-report-inbox"};plan={"task_id":"new-task","goal":"new callback-interface boundary checks","input_sha256":"b"*64,"max_attempts":2}
  self.runner.q.initialize(self.q,policy);self.runner.q.enqueue(self.q,plan);self.reg={"a":{"queue":str(self.q),"run_id":policy["run_id"],"owned_root":str(self.work)}};self.dispatch=GenieRunController(self.reg).call("advance_run",{"run_name":"a"});self.token=self.dispatch["token"];self.host=m.GenieRunEvents(self.reg)
 def args(self,op="observe",payload=None):
  if payload is None:payload={"outcome":"OBSERVED_ACCEPTED","agent":"worker-a","evidence":{"observed":"actual"}}
  return {"run_name":"a","operation":op,"supplied":copy.deepcopy(self.token),"payload":copy.deepcopy(payload)}
 def invoke(self,args):return self.host.call("apply_run_event",args)
 def mock_callback(self,callback):
  control=m._load_control();facade=control._load_facade();runner=types.SimpleNamespace(context=self.runner.context,callback=callback)
  return patch.object(m,"_load_control",return_value=control),patch.object(control,"_load_facade",return_value=facade),patch.object(facade,"_load_core",return_value=types.SimpleNamespace(load_runner=lambda:runner))
 def test_exact_top_fields(self):
  for value in [None,[],{}, {**self.args(),"path":"secret"},{**self.args(),"operation":"advance_run"}]:self.assertEqual(self.invoke(value)["status"],"REJECT")
 def test_alias_and_unsupported(self):
  self.assertEqual(self.invoke({**self.args(),"run_name":"absent"})["status"],"REJECT");self.assertEqual(self.host.call("advance_run",self.args())["status"],"REJECT")
 def test_token_exact_types_and_context(self):
  for key,value in [("attempt",True),("attempt",0),("run_id","other"),("input_sha256","F"*64),("task_id"," task ")]:
   args=self.args();args["supplied"][key]=value;self.assertEqual(self.invoke(args)["status"],"REJECT")
 def test_observation_schema(self):
  for value in [{"outcome":"UNKNOWN","agent":"worker-a","evidence":{"x":1}},{"outcome":"OBSERVED_ACCEPTED","agent":None,"evidence":{"x":1}},{"outcome":"OBSERVED_ACCEPTED","agent":"worker-a","evidence":{}},{"outcome":"bad","agent":None,"evidence":{"x":1}}]:self.assertEqual(self.invoke(self.args(payload=value))["status"],"REJECT")
 def test_invalid_json_data(self):
  cyc={};cyc["x"]=cyc
  for ev in [{1:"key"},{"x":float("nan")},{"x":"\ud800"},{"x":(1,2)},cyc]:self.assertEqual(self.invoke(self.args(payload={"outcome":"UNKNOWN","agent":None,"evidence":ev}))["status"],"REJECT")
 def test_payload_bounds(self):
  for text in [" ","x"*12001,"\ud800"]:self.assertEqual(self.invoke(self.args("submit",{"agent":"worker-a","text":text}))["status"],"REJECT")
  self.assertEqual(self.invoke(self.args(payload={"outcome":"UNKNOWN","agent":None,"evidence":{"x":"z"*16000}}))["status"],"REJECT")
 def test_utf8_exact_bounds(self):
  cases=[("submit",{"agent":"worker-a","text":"😀"*3000},"SUBMITTED"),("observe",{"outcome":"UNKNOWN","agent":None,"evidence":{"x":"z"*15992}},"RECORDED")]
  for op,payload,result in cases:
   p1,p2,p3=self.mock_callback(lambda *a,**kw:result)
   with p1,p2,p3:out=self.invoke(self.args(op,payload))
   self.assertEqual(out["status"],"APPLIED")
  self.assertEqual(self.invoke(self.args("submit",{"agent":"worker-a","text":"😀"*3001}))["status"],"REJECT")
 def test_review_schema(self):
  for payload in [{"candidate_hash":"a"*63,"decision":"ACCEPT","reason":"valid"},{"candidate_hash":"a"*64,"decision":"PROMOTE","reason":"valid"},{"candidate_hash":"a"*64,"decision":"ACCEPT","reason":" ","extra":1}]:self.assertEqual(self.invoke(self.args("review",payload))["status"],"REJECT")
 def test_detached_payload_and_once(self):
  args=self.args();calls=[]
  def callback(*a,**kw):
   args["payload"]["evidence"]["observed"]="changed";args["supplied"]["attempt"]=3;calls.append((a,kw));return "RECORDED"
  p1,p2,p3=self.mock_callback(callback)
  with p1,p2,p3:out=self.invoke(args)
  self.assertEqual(out,{"status":"APPLIED","operation":"observe","result":"RECORDED"});self.assertEqual(len(calls),1);self.assertEqual(calls[0][1]["evidence"]["observed"],"actual");self.assertEqual(calls[0][0][4]["attempt"],1)
 def test_postcommit_exception(self):
  def callback(*a,**kw):self.runner.callback(*a,**kw);raise RuntimeError("secret path")
  p1,p2,p3=self.mock_callback(callback)
  with p1,p2,p3:out=self.invoke(self.args())
  self.assertEqual(out["status"],"UNKNOWN");self.assertTrue(out["preserve"]);self.assertFalse(out["allow_new_invocation"]);self.assertNotIn("secret",json.dumps(out))
  _,ledger,_=self.runner.paths(self.work,self.token["run_id"],self.token["task_id"])
  with self.runner.b.transaction(ledger,False) as db:self.assertEqual(db.execute("SELECT count(*) FROM host_observations").fetchone()[0],1)
 def test_unexpected_results(self):
  for result in [None,{},"ACCEPT","SUBMITTED"]:
   p1,p2,p3=self.mock_callback(lambda *a,**kw:result)
   with p1,p2,p3:out=self.invoke(self.args())
   self.assertEqual(out["status"],"UNKNOWN");self.assertFalse(out["allow_new_invocation"])
 def test_source_failure_pre_callback(self):
  with patch.object(m.Path,"read_bytes",return_value=b"bad"):out=self.invoke(self.args())
  self.assertEqual(out["status"],"REJECT")
 def test_real_new_task_lifecycle(self):
  self.assertEqual(self.invoke(self.args())["result"],"RECORDED");text="new callback-interface test data"
  self.assertEqual(self.invoke(self.args("submit",{"agent":"worker-a","text":text}))["result"],"SUBMITTED")
  review=self.args("review",{"candidate_hash":hashlib.sha256(text.encode()).hexdigest(),"decision":"ACCEPT","reason":"EXACT_TEST_DATA"});self.assertEqual(self.invoke(review)["result"],"ACCEPT")
  from shared_interfaces.run_control import GenieRunController
  self.assertEqual(GenieRunController(self.reg).call("advance_run",{"run_name":"a"})["action"],"TASK_COMPLETE")
 def test_crossed_token_rejected_by_core_no_new_effect(self):
  args=self.args();args["supplied"]["call_id"]="c"*64;out=self.invoke(args);self.assertEqual(out["status"],"UNKNOWN");self.assertFalse(out["allow_new_invocation"])
  _,ledger,_=self.runner.paths(self.work,self.token["run_id"],self.token["task_id"])
  with self.runner.b.transaction(ledger,False) as db:self.assertEqual(db.execute("SELECT count(*) FROM host_observations").fetchone()[0],0)
 def test_metadata_separate(self):
  a=self.host.tools();self.assertEqual(len(a),1);self.assertEqual(a[0]["name"],"apply_run_event");self.assertFalse(a[0]["annotations"]["readOnlyHint"]);self.assertFalse(a[0]["annotations"]["idempotentHint"]);a[0]["name"]="bad";self.assertEqual(self.host.tools()[0]["name"],"apply_run_event")
  from shared_interfaces.status_tool import GenieStatusTools
  self.assertEqual([x["name"] for x in GenieStatusTools(self.reg).tools()],["get_run_status","get_task_result"])
if __name__=="__main__":unittest.main(verbosity=2)

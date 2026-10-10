import contextlib, hashlib, importlib.util, io, json, os, pathlib, subprocess, sys, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("cli_candidate",ROOT/"shared_interfaces/candidate/cli.py")
cli=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cli)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=pathlib.Path(self.tmp.name);self.reg=self.base/"registry.json"
  self.record={"a":{"queue":"q.sqlite","run_id":"run-a","owned_root":"owned"}}
  self.reg.write_text(json.dumps(self.record))
 def call(self,args):
  out=io.StringIO()
  with contextlib.redirect_stdout(out):
   try: code=cli.main(args)
   except SystemExit as e:code=e.code
  return code,out.getvalue()
 def test_help_no_reads(self):
  with patch.object(cli,"_load_facade",side_effect=AssertionError("source read")),patch.object(cli,"_read_registry",side_effect=AssertionError("registry read")):
   code,text=self.call(["--help"]);self.assertEqual(code,0);self.assertIn("status",text)
 def test_tools_no_registry_or_core(self):
  with patch.object(cli,"_read_registry",side_effect=AssertionError("registry read")):
   code,text=self.call(["tools"]);self.assertEqual(code,0);self.assertEqual([x["name"] for x in json.loads(text)],["get_run_status","get_task_result"])
 def test_invalid_argument_no_load(self):
  with patch.object(cli,"_load_facade",side_effect=AssertionError("loaded")):
   code,text=self.call(["status","--registry","/private/token","--run","a","--extra","secret"]);self.assertEqual(code,2);self.assertNotIn("secret",text);self.assertNotIn("/private",text)
 def test_relative_paths(self):
  value=cli._read_registry(self.reg);self.assertEqual(value["a"]["queue"],str(self.base/"q.sqlite"));self.assertEqual(value["a"]["owned_root"],str(self.base/"owned"))
 def test_symlink_target_anchor(self):
  other=self.base/"other";other.mkdir();link=other/"link.json";link.symlink_to(self.reg)
  self.assertEqual(cli._read_registry(link),cli._read_registry(self.reg))
 def test_duplicate_keys(self):
  for raw in ['{"a":{},"a":{}}','{"a":{"queue":"q","queue":"z","run_id":"r","owned_root":"x"}}']:
   self.reg.write_text(raw)
   with self.assertRaises(Exception):cli._read_registry(self.reg)
 def test_bad_config_variants(self):
  for raw in ['[]','{"a":NaN}','{"a":{"queue":"","run_id":"r","owned_root":"o"}}','{"a":{"queue":3,"run_id":"r","owned_root":"o"}}','{"a":{"queue":"q","run_id":"r","owned_root":"o","extra":1}}']:
   self.reg.write_text(raw)
   with self.assertRaises(Exception):cli._read_registry(self.reg)
 def test_utf8_and_cap(self):
  for raw in [b"\xff",b" "*65537]:
   self.reg.write_bytes(raw)
   with self.assertRaises(Exception):cli._read_registry(self.reg)
  raw=json.dumps(self.record).encode();self.reg.write_bytes(raw+b" "*(65536-len(raw)));self.assertIn("a",cli._read_registry(self.reg))
 def test_fifo_rejects(self):
  fifo=self.base/"fifo";os.mkfifo(fifo)
  with self.assertRaises(Exception):cli._read_registry(fifo)
 def test_missing_config_sanitized(self):
  code,text=self.call(["status","--registry",str(self.base/"private_missing"),"--run","a"]);self.assertEqual(code,2);self.assertNotIn(str(self.base),text);self.assertEqual(json.loads(text)["status"],"REJECT")
 def test_source_mismatch(self):
  with patch.object(cli.pathlib.Path if hasattr(cli,"pathlib") else cli.Path,"read_bytes",return_value=b"bad"):
   code,text=self.call(["tools"]);self.assertEqual(code,2);self.assertEqual(json.loads(text)["status"],"REJECT")
 def test_actual_status_and_result(self):
  actual={"done":{"queue":str(ROOT/"result_interface/trial/queue.sqlite"),"run_id":"genie-task-result-interface-run-20261010","owned_root":str(ROOT/"result_interface/trial/work")}};self.reg.write_text(json.dumps(actual))
  from shared_interfaces.status_tool import GenieStatusTools
  host=GenieStatusTools(actual)
  for command,tool,extra,args in [("status","get_run_status",[],{"run_name":"done"}),("result","get_task_result",["--task","genie-task-result-interface-20261010"],{"run_name":"done","task_id":"genie-task-result-interface-20261010"})]:
   code,text=self.call([command,"--registry",str(self.reg),"--run","done"]+extra);self.assertEqual(code,0);self.assertEqual(json.loads(text),host.call(tool,args))
 def test_unknown_alias(self):
  code,text=self.call(["status","--registry",str(self.reg),"--run","absent"]);self.assertEqual(code,2);self.assertEqual(json.loads(text)["reason"],"UNKNOWN_RUN")
 def test_status_pass_with_unknown_sink_exit_zero(self):
  fake={"status":"PASS","tasks":[{"fresh_sink":{"status":"UNKNOWN"}}]}
  facade=cli._load_facade()
  with patch.object(cli,"_load_facade",return_value=facade),patch.object(facade.GenieStatusTools,"call",return_value=fake):
   code,text=self.call(["status","--registry",str(self.reg),"--run","a"]);self.assertEqual(code,0);self.assertEqual(json.loads(text),fake)
 def test_result_unknown_mismatch_exit_three(self):
  facade=cli._load_facade()
  for status in ["UNKNOWN","MISMATCH"]:
   fake={"status":status,"reason":"TASK_RESULT_UNAVAILABLE"}
   with patch.object(cli,"_load_facade",return_value=facade),patch.object(facade.GenieStatusTools,"call",return_value=fake):
    code,text=self.call(["result","--registry",str(self.reg),"--run","a","--task","t"]);self.assertEqual(code,3);self.assertEqual(json.loads(text),fake)
 def test_data_not_executed(self):
  facade=cli._load_facade();fake={"status":"CONFIRMED","result_text":"$(touch /tmp/never)\n\x1b[31m", "content_role":"UNTRUSTED_ACCEPTED_TASK_DATA"}
  with patch.object(cli,"_load_facade",return_value=facade),patch.object(facade.GenieStatusTools,"call",return_value=fake):
   code,text=self.call(["result","--registry",str(self.reg),"--run","a","--task","t"]);self.assertEqual(code,0);self.assertEqual(json.loads(text),fake);self.assertNotIn("\x1b",text)
if __name__=="__main__":unittest.main(verbosity=2)

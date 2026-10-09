"""Controller-owned frozen acceptance checks; only statically reviewed candidates load."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
SCOPE='TEST_LOG_SUMMARY_ONLY'
def expected(status,count):return {'status':status,'count':count,'evidence_scope':SCOPE}
def cases():
 out=[]
 def add(name,fmt,text,status,count):out.append((name,fmt,text,expected(status,count)))
 add('unittest_pass','unittest','...\nRan 3 tests in 0.001s\n\nOK\n','PASS',3)
 add('unittest_single','unittest','Ran 1 test in 0.1s\nOK','PASS',1)
 add('unittest_zero_ok','unittest','Ran 0 tests in 0.000s\nOK','NO_COVERAGE',0)
 add('unittest_zero_message','unittest','Ran 0 tests in 0.000s\nNO TESTS RAN','NO_COVERAGE',0)
 add('unittest_all_skipped','unittest','Ran 3 tests in 0.1s\nOK (skipped=3)','NO_COVERAGE',0)
 add('unittest_some_skipped','unittest','Ran 3 tests in 0.1s\nOK (skipped=1)','PASS',2)
 add('unittest_fail','unittest','Ran 3 tests in 0.1s\nFAILED (failures=1)','FAIL',3)
 add('unittest_errors_skipped','unittest','Ran 3 tests in 0.1s\nFAILED (errors=1, skipped=1)','FAIL',2)
 add('unittest_both_fail','unittest','Ran 3 tests in 0.1s\nFAILED (failures=1, errors=1)','FAIL',3)
 bad=[('missing','OK'),('truncated','Ran 3 tests in 0.1s'),('substring_ok','trace says OK\nRan 3 tests in 0.1s\nFAILED (failures=1)\ntrailing'),('duplicate_summary','Ran 1 test in 0.1s\nRan 1 test in 0.1s\nOK'),('duplicate_marker','OK\nRan 1 test in 0.1s\nOK'),('duplicate_failure_key','Ran 3 tests in 0.1s\nFAILED (failures=1, failures=1)'),('impossible_failure_sum','Ran 2 tests in 0.1s\nFAILED (failures=2, errors=1)'),('too_many_skips','Ran 1 test in 0.1s\nOK (skipped=2)'),('contradictory_zero_failure','Ran 0 tests in 0.1s\nFAILED (failures=1)'),('contradictory_nonzero_no_tests','Ran 1 test in 0.1s\nNO TESTS RAN'),('zero_failure_counts','Ran 3 tests in 0.1s\nFAILED (errors=0)'),('unknown_marker','Ran 3 tests in 0.1s\nSUCCESS'),('negative_duration','Ran 3 tests in -0.1s\nOK')]
 for name,text in bad:add('unittest_'+name,'unittest',text,'REJECT',None)
 positive={'status':'PASS','count':2,'checks':[{'check':'a','passed':True},{'check':'b','rejected':True}]}
 add('json_pass','json',json.dumps(positive),'PASS',2)
 fail={'status':'FAIL','count':1,'checks':[{'check':'a','passed':False}]};add('json_fail','json',json.dumps(fail),'FAIL',1)
 for status in ('PASS','FAIL'):add('json_zero_'+status,'json',json.dumps({'status':status,'count':0,'checks':[]}),'NO_COVERAGE',0)
 malformed=[]
 def badjson(name,obj):malformed.append((name,json.dumps(obj)))
 badjson('bool_count',{**positive,'count':True});badjson('float_count',{**positive,'count':2.0});badjson('mismatched_count',{**positive,'count':1});badjson('false_declared_pass',{'status':'PASS','count':1,'checks':[{'check':'a','passed':False}]});badjson('true_declared_fail',{'status':'FAIL','count':1,'checks':[{'check':'a','passed':True}]});badjson('integer_flag',{'status':'PASS','count':1,'checks':[{'check':'a','passed':1}]});badjson('extra_fields',{**positive,'extra':True});badjson('empty_check_name',{'status':'PASS','count':1,'checks':[{'check':'','passed':True}]});badjson('unstripped_name',{'status':'PASS','count':1,'checks':[{'check':' a','passed':True}]});badjson('two_flags',{'status':'PASS','count':1,'checks':[{'check':'a','passed':True,'rejected':True}]});badjson('nonobject',[])
 malformed += [('duplicate_top','{"status":"FAIL","status":"PASS","count":0,"checks":[]}'),('duplicate_nested','{"status":"PASS","count":1,"checks":[{"check":"a","passed":false,"passed":true}]}'),('truncated','{"status":')]
 for name,text in malformed:add('json_'+name,'json',text,'REJECT',None)
 add('invalid_format','other','anything','REJECT',None);add('invalid_api_input','unittest',None,'REJECT',None)
 for name,fmt,status,count in [('zero_discovery.txt','unittest','NO_COVERAGE',0),('runner_status.txt','unittest','PASS',46),('direct_checks.json','json','PASS',17)]:add('actual_'+name,fmt,(Path(__file__).resolve().parents[1]/'input'/name).read_text(),status,count)
 return out

def run(path):
 spec=importlib.util.spec_from_file_location('candidate',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 results=[]
 for name,fmt,text,want in cases():
  try:got=mod.summarize(text,fmt);passed=type(got) is dict and got==want and (got['count'] is None or type(got['count']) is int);error=None
  except Exception as e:got=None;passed=False;error=type(e).__name__
  results.append({'name':name,'passed':passed,'expected':want,'actual':got,'error':error})
 with tempfile.TemporaryDirectory() as temp:
  directory=Path(temp)
  for label,raw,fmt,status,count,code in [('valid',b'Ran 2 tests in 0.01s\nOK\n','unittest','PASS',2,0),('zero',b'Ran 0 tests in 0.0s\nNO TESTS RAN\n','unittest','NO_COVERAGE',0,1),('failure',b'Ran 1 test in 0.0s\nFAILED (errors=1)\n','unittest','FAIL',1,1),('invalid_utf8',b'\xff','json','REJECT',None,2),('too_large',b'x'*(1024*1024+1),'unittest','REJECT',None,2)]:
   file=directory/(label+'.txt');file.write_bytes(raw);before=file.read_bytes();p=subprocess.run([sys.executable,'-B',str(path),str(file),'--format',fmt],capture_output=True,text=True,timeout=5)
   try:actual=json.loads(p.stdout)
   except ValueError:actual=None
   results.append({'name':'cli_'+label,'passed':p.returncode==code and actual==expected(status,count) and file.read_bytes()==before,'exit':p.returncode,'actual':actual,'expected':expected(status,count),'input_unchanged':file.read_bytes()==before})
  missing=directory/'missing';p=subprocess.run([sys.executable,'-B',str(path),str(missing),'--format','json'],capture_output=True,text=True,timeout=5)
  try:actual=json.loads(p.stdout)
  except ValueError:actual=None
  results.append({'name':'cli_missing','passed':p.returncode==2 and actual==expected('REJECT',None) and not missing.exists(),'exit':p.returncode,'actual':actual})
 return {'candidate_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'checks':len(results),'passed':sum(x['passed'] for x in results),'all_passed':all(x['passed'] for x in results),'results':results,'scope':'controller-owned finite task contract; no authenticity/execution proof from input logs'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('candidate');ap.add_argument('output');a=ap.parse_args();result=run(Path(a.candidate).resolve());Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='results'}));raise SystemExit(0 if result['all_passed'] else 1)

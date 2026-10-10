"""Root-owned current-host trial bridge; no model API, service or task creation."""
import importlib.util,json,pathlib,sys
HOME=pathlib.Path(__file__).resolve().parents[2]
source=HOME/'shared_interfaces/session_driver.py'
s=importlib.util.spec_from_file_location('accepted_driver',source);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
TRIAL=HOME/'session_driver/trial'
registry={'actual':{'queue':str(TRIAL/'queue.sqlite'),'run_id':'genie-session-driver-run-20261010','owned_root':str(TRIAL/'work')}}
class Writer:
 def write(self,raw):
  with (TRIAL/'STDOUT.jsonl').open('ab') as log:log.write(raw)
  return sys.stdout.buffer.write(raw)
 def flush(self):sys.stdout.buffer.flush()
class Reader:
 def readline(self,n):
  raw=sys.stdin.buffer.readline(n)
  with (TRIAL/'STDIN.jsonl').open('ab') as log:log.write(raw)
  return raw
result=m.serve_run(registry,'actual',Reader(),Writer(),max_actions=16)
(TRIAL/'DRIVER_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')

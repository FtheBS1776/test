"""Root-owned narrow current-host bridge, no model API or retry."""
import hashlib,importlib.util,json,pathlib,sys
HOME=pathlib.Path(__file__).resolve().parents[2];TRIAL=HOME/'host_return/trial'
def load(name,pin):
 path=HOME/'shared_interfaces'/name;raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 s=importlib.util.spec_from_file_location('trial_'+name[:-3],path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('session_driver.py','89b0fd1ef48d5460dada5cc59b25072a10ec9b5c7049af25eabbb2d4464bf9d9');cli=load('cli.py','c0a35e699cc4ad2fd2e176fd8ab951fbab7f57f56c783230925d078b38ff8af4')
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
result=m.serve_run(cli._read_registry(TRIAL/'REGISTRY.json'),'actual',Reader(),Writer(),max_actions=16)
(TRIAL/'DRIVER_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
sys.exit(0 if result.get('action')=='STOP' and result.get('reason')=='ALL_TASKS_COMPLETE' else 3)

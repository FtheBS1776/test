"""Owned child pause/copy and source-bound per-thread observation only."""
import contextlib,hashlib,json,os,shutil,signal,stat,sys,threading,time
from pathlib import Path
from owned_etcd import demand,save,sha
from etcd_lifecycle_adapter import Gateway,_canonical
def tasks(pid):
 result={}
 for path in sorted(Path('/proc')/str(pid)/'task' for _ in [0]):
  for task in sorted(path.iterdir()):
   lines=(task/'status').read_text().splitlines();state=next(s.split()[1] for s in lines if s.startswith('State:'));result[task.name]=state
 demand(bool(result),'NO_OWNED_TASKS');return result
@contextlib.contextmanager
def stopped_child(c,out):
 p=c.processes[0];demand(p.poll() is None,'OWNED_CHILD_NOT_LIVE');sent=False
 try:
  c.event(action='SIGSTOP',member_index=0,pid=p.pid);p.send_signal(signal.SIGSTOP);sent=True;deadline=time.monotonic()+.75
  while True:
   pid,status=os.waitpid(p.pid,os.WNOHANG|os.WUNTRACED)
   if pid:
    demand(pid==p.pid and os.WIFSTOPPED(status) and os.WSTOPSIG(status)==signal.SIGSTOP,'STOP_STATUS_MISMATCH');break
   demand(time.monotonic()<deadline,'STOP_CONFIRM_TIMEOUT');time.sleep(.005)
  before=tasks(p.pid);demand(set(before.values())=={'T'},'TASK_NOT_STOPPED');c.event(action='stop_confirmed',member_index=0,pid=p.pid,wait_status=status,stop_signal=int(signal.SIGSTOP),tasks=before)
  yield p.pid,before
 finally:
  if sent:
   p.send_signal(signal.SIGCONT);c.event(action='SIGCONT',member_index=0,pid=p.pid);deadline=time.monotonic()+.75
   while True:
    pid,status=os.waitpid(p.pid,os.WNOHANG|os.WCONTINUED)
    if pid:demand(pid==p.pid and os.WIFCONTINUED(status),'RESUME_STATUS_MISMATCH');break
    demand(time.monotonic()<deadline,'RESUME_CONFIRM_TIMEOUT');time.sleep(.005)
   c.event(action='resume_confirmed',member_index=0,pid=p.pid,wait_status=status)
def copy_paused(c,out,pid,before):
 start=time.monotonic_ns();data=c.work/'m0';files=sorted((data/'member/wal').iterdir());wals=[p for p in files if p.suffix=='.wal'];demand(len(wals)==1 and wals[0].name=='0000000000000000-0000000000000000.wal','INITIAL_WAL_REQUIRED');demand(all(p.is_file() and p.suffix in ('.wal','.tmp') for p in files),'UNEXPECTED_WAL_FILES');demand(not list((data/'member/snap').glob('*.snap')),'RAFT_SNAPSHOT_UNSUPPORTED');source=wals[0];st1=source.lstat();demand(stat.S_ISREG(st1.st_mode) and not source.is_symlink(),'REGULAR_OWNED_WAL_REQUIRED');first=sha(source)
 snapshot=out/'snapshot';(snapshot/'member/wal').mkdir(parents=True);(snapshot/'member/snap').mkdir();target=snapshot/'member/wal'/source.name;shutil.copyfile(source,target);copied=sha(target);last=sha(source);st2=source.lstat();after=tasks(pid);end=time.monotonic_ns();identity=lambda s:{'device':s.st_dev,'inode':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'mode':s.st_mode};demand(identity(st1)==identity(st2) and first==last==copied and before==after and set(after.values())=={'T'},'PAUSED_COPY_UNSTABLE')
 record={'mode':'OWNED_STOP_CONFIRMED_STABLE_BYTE_COPY','source_data_directory':str(data),'pid':pid,'start_monotonic_ns':start,'end_monotonic_ns':end,'source_identity_before':identity(st1),'source_identity_after':identity(st2),'source_sha256_before':first,'source_sha256_after':last,'copy_sha256':copied,'tasks_before':before,'tasks_after':after,'raft_snapshot_count':0,'source_wal_directory_names':[p.name for p in files],'excluded_temporary_files':[p.name for p in files if p.suffix=='.tmp'],'authority_input':False,'durability_claim':False};save(out/'SNAPSHOT_BOUNDARY.json',record);save(out/'SNAPSHOT_MANIFEST.json',{str(target.relative_to(snapshot)):copied});return record
class GatewayExceptionTrace:
 def __init__(self):
  self.post=Gateway.post;self.code=self.post.__code__;self.source=Path(self.code.co_filename);self.events=[];self.errors=[];self.started=threading.Event();self.thread_id=None;self.previous=None;self.restore_ok=False
 def tracer(self,frame,event,arg):
  if frame.f_code is not self.code:return None
  try:
   frame.f_trace_lines=False
   if event not in ('call','exception','return'):return self.tracer
   if len(self.events)>=32:self.errors.append('TRACE_OVERFLOW');return self.tracer
   row={'event':event,'monotonic_ns':time.monotonic_ns(),'thread_id':threading.get_ident(),'code_identity_match':frame.f_code is self.code,'path':frame.f_locals['path'],'request_sha256':hashlib.sha256(_canonical(frame.f_locals['value'])).hexdigest(),'endpoint':frame.f_locals['self'].endpoint}
   if event=='exception':row['exception_type']=arg[0].__name__;row['exact_timeout_type']=arg[0] is TimeoutError;row['exact_connection_error_type']=arg[0] is ConnectionError
   self.events.append(row)
   if event=='call':self.started.set()
  except Exception as e:self.errors.append(type(e).__name__)
  return self.tracer
 def __enter__(self):
  self.thread_id=threading.get_ident();self.previous=sys.gettrace();demand(self.previous is None,'PREEXISTING_TRACE');self.source_hash_before=sha(self.source);sys.settrace(self.tracer);return self
 def __exit__(self,*exc):
  sys.settrace(self.previous);self.restore_ok=sys.gettrace() is self.previous;self.source_hash_after=sha(self.source)
 def record(self):
  return {'scope':'ORIGINAL_GATEWAY_POST_EXCEPTION_OBSERVATION; instrumented execution','thread_id':self.thread_id,'source_filename':str(self.source),'source_sha256_before':self.source_hash_before,'source_sha256_after':self.source_hash_after,'bytecode_sha256':hashlib.sha256(self.code.co_code).hexdigest(),'post_method_unchanged':Gateway.post is self.post,'previous_trace_absent':self.previous is None,'restore_ok':self.restore_ok,'events':self.events,'errors':self.errors,'exception_values_or_headers_retained':False}

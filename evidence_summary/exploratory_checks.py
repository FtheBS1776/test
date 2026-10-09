"""Reviewer-prompted checks outside unchanged frozen suite; trusted Linux scope."""
import contextlib,hashlib,importlib.util,io,json,os,shutil,subprocess,tempfile
from pathlib import Path
CANDIDATE=Path(__file__).parent/'output/report_logs_1.py'
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run():
 m=load(CANDIDATE,'exploratory_reviewed');checks=[]
 def check(name,fn):
  try:fn();checks.append({'check':name,'passed':True})
  except Exception as e:checks.append({'check':name,'passed':False,'error':type(e).__name__+': '+str(e)})
 with tempfile.TemporaryDirectory() as directory:
  d=Path(directory);source=d/'source.txt';raw=b'Ran 1 test in 0.1s\nOK\n';source.write_bytes(raw)
  def invalid():
   opens=[]
   def failopen(*a,**k):opens.append(a);raise AssertionError('unexpected open')
   m.open=failopen
   try:
    try:m.build_report([{'path':str(source),'format':'unittest'},{'path':'unused','format':'invalid'}])
    except ValueError:pass
    else:raise AssertionError('accepted')
    assert not opens
   finally:del m.open
  check('invalid_final_spec_before_any_open',invalid)
  def fifo():
   p=d/'fifo';os.mkfifo(p);target=d/'fifo.json'
   proc=subprocess.run(['python3.12','-B',str(CANDIDATE),'--output',str(target),'--input','unittest',str(p)],capture_output=True,text=True,timeout=5)
   assert proc.returncode==0
   e=json.loads(target.read_text())['entries'][0];assert e['read_status']=='UNREADABLE' and e['sha256'] is None and e['summary']['status']=='REJECT'
  check('linux_fifo_without_writer_rejects',fifo)
  def snapshot():
   summarize=m._load_summarize();old=m._load_summarize
   def after_capture(text,fmt):source.write_bytes(b'changed after capture');return summarize(text,fmt)
   m._load_summarize=lambda:after_capture
   try:e=m.build_report([{'path':str(source),'format':'unittest'}])['entries'][0]
   finally:m._load_summarize=old
   assert e['sha256']==hashlib.sha256(raw).hexdigest() and e['bytes']==len(raw) and e['summary']['status']=='PASS'
   assert source.read_bytes()!=raw;source.write_bytes(raw)
  check('hash_binds_capture_not_later_path',snapshot)
  def dependency():
   root=d/'copy';(root/'evidence_summary').mkdir(parents=True);(root/'comparison_pilot').mkdir()
   copied=root/'evidence_summary/report_logs.py';shutil.copyfile(CANDIDATE,copied)
   dep=root/'comparison_pilot/validation_summary.py';shutil.copyfile(Path(__file__).resolve().parents[1]/'comparison_pilot/validation_summary.py',dep)
   n=load(copied,'snapshot_dependency');ordinary=open
   class SwapOnClose:
    def __init__(self,f):self.f=f
    def __enter__(self):return self.f
    def __exit__(self,*a):self.f.close();dep.write_bytes(b'raise RuntimeError("unverified replacement executed")\n')
   def wrapped(path,*a,**k):
    f=ordinary(path,*a,**k);return SwapOnClose(f) if Path(path)==dep else f
   n.open=wrapped;summarize=n._load_summarize();assert summarize(raw.decode(),'unittest')['status']=='PASS'
  check('dependency_import_uses_verified_captured_bytes',dependency)
  def dangling():
   target=d/'dangling';target.symlink_to(d/'absent');stdout=io.StringIO()
   with contextlib.redirect_stdout(stdout):code=m.main(['--output',str(target),'--input','unittest',str(source)])
   assert code==2 and target.is_symlink() and not (d/'absent').exists() and json.loads(stdout.getvalue())['status']=='REJECT'
  check('dangling_output_symlink_preserved',dangling)
  def output_failure(kind):
   target=d/(kind+'.json');ordinary=open
   class Fault:
    def __init__(self,f):self.f=f
    def __enter__(self):return self
    def write(self,text):
     if kind=='partial':self.f.write(text[:7]);self.f.flush();raise OSError('injected write failure')
     return self.f.write(text)
    def __exit__(self,*a):
     self.f.close()
     if kind=='close':raise OSError('injected close failure')
   def wrapped(path,*a,**k):
    f=ordinary(path,*a,**k);return Fault(f) if Path(path)==target else f
   m.open=wrapped;stdout=io.StringIO()
   try:
    with contextlib.redirect_stdout(stdout):code=m.main(['--output',str(target),'--input','unittest',str(source)])
   finally:del m.open
   assert code==2 and json.loads(stdout.getvalue())['status']=='REJECT' and target.is_file()
   if kind=='partial':assert len(target.read_bytes())==7
   else:assert json.loads(target.read_text())['status']=='REPORT_BUILT'
  for kind in ['partial','close']:check('output_'+kind+'_failure_preserves_file',lambda kind=kind:output_failure(kind))
 return {'candidate_sha256':hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),'checks':checks,'count':len(checks),'all_passed':all(c['passed'] for c in checks),'scope':'reviewer-prompted supplementary checks; frozen suite unchanged; injected errors, not crash/power-loss assurance'}
if __name__=='__main__':
 r=run();(Path(__file__).parent/'EXPLORATORY_RESULTS.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}));raise SystemExit(0 if r['all_passed'] else 1)

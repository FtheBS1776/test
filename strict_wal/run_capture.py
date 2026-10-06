"""Bounded hosted strict observer build/fixtures, no provider execution."""
import argparse,hashlib,json,os,pathlib,shutil,signal,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def run(out,name,argv,timeout):
 process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:stdout,stderr=process.communicate(timeout=timeout);code=process.returncode
 except subprocess.TimeoutExpired:
  try:os.killpg(process.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:stdout,stderr=process.communicate(timeout=3)
  except subprocess.TimeoutExpired:
   try:os.killpg(process.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   stdout,stderr=process.communicate(timeout=3)
  code=124
 (out/(name+'.stdout')).write_bytes(stdout);(out/(name+'.stderr')).write_bytes(stderr);save(out/(name+'.command.json'),{'argv':argv,'returncode':code,'timeout_seconds':timeout});return code
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--upstream',required=True);ap.add_argument('--expected-source-manifest',required=True);a=ap.parse_args();out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);state={'state':'INDETERMINATE','controlling_pass':186,'classification':'NONCLAIM','promotion':False,'freeze':False,'provider_executed':False}
 try:
  data=(ROOT/'SOURCE_MANIFEST.json').read_bytes()
  if hashlib.sha256(data).hexdigest()!=a.expected_source_manifest:raise RuntimeError('SOURCE_MANIFEST_MISMATCH')
  manifest=json.loads(data)
  for n,h in manifest.items():
   if len(pathlib.PurePosixPath(n).parts)!=1 or hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise RuntimeError('SOURCE_MISMATCH_'+n)
  source=out/'SOURCE';source.mkdir()
  for n in list(manifest)+['SOURCE_MANIFEST.json']:shutil.copyfile(ROOT/n,source/n)
  state['source_manifest_sha256']=a.expected_source_manifest;workflow=pathlib.Path(os.environ['GITHUB_WORKSPACE'])/'.github/workflows/etcd-strict-wal.yml';shutil.copyfile(workflow,out/'EXECUTED_WORKFLOW.yml');state['workflow_sha256']=hashlib.sha256(workflow.read_bytes()).hexdigest()
  save(out/'JOB_CONTEXT.json',{k:os.environ.get(k) for k in ['GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_EVENT_NAME','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','RUNNER_ENVIRONMENT','ImageVersion']})
  stages=[('BUILD',[sys.executable,'-B',str(ROOT/'build_observer.py'),'--upstream',a.upstream,'--output',str(out/'build')],420),('FIXTURES',[sys.executable,'-B',str(ROOT/'run_fixtures.py'),'--observer',str(out/'build/wal-observer'),'--output',str(out/'fixtures')],60)]
  for name,argv,timeout in stages:
   state[name.lower()+'_exit_code']=run(out,name,argv,timeout)
   if state[name.lower()+'_exit_code']!=0:raise RuntimeError(name+'_FAILED')
  state['state']='CAPTURE_COMPLETE_PENDING_ADJUDICATION'
 except Exception as e:state['error']=type(e).__name__+': '+str(e)
 finally:save(out/'CAPTURE_STATUS.json',state);save(out/'CAPTURE_MANIFEST.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='CAPTURE_MANIFEST.json'})
 print(json.dumps(state));return 0 if state['state']=='CAPTURE_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

"""Bounded execution/capture wrapper; capture completeness is not adjudication."""
import argparse,hashlib,json,os,pathlib,shutil,signal,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def run(out,name,argv,timeout):
    process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        stdout,stderr=process.communicate(timeout=timeout);code=process.returncode
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:stdout,stderr=process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=process.communicate(timeout=3)
        code=124
    (out/(name+'.stdout')).write_bytes(stdout);(out/(name+'.stderr')).write_bytes(stderr)
    save(out/(name+'.command.json'),{'argv':argv,'returncode':code,'timeout_seconds':timeout});return code
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--expected-source-manifest',required=True);a=ap.parse_args()
    out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    state={'state':'INDETERMINATE','controlling_pass':186,'promotion':False,'freeze':False}
    try:
        data=(ROOT/'SOURCE_MANIFEST.json').read_bytes()
        if hashlib.sha256(data).hexdigest()!=a.expected_source_manifest:raise RuntimeError('SOURCE_MANIFEST_MISMATCH')
        manifest=json.loads(data)
        for name,h in manifest.items():
            path=pathlib.PurePosixPath(name)
            if path.is_absolute() or len(path.parts)!=1 or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise RuntimeError('SOURCE_MISMATCH_'+name)
        source=out/'SOURCE';source.mkdir()
        for name in list(manifest)+['SOURCE_MANIFEST.json']:shutil.copyfile(ROOT/name,source/name)
        state['source_manifest_sha256']=a.expected_source_manifest
        workflow=pathlib.Path(os.environ['GITHUB_WORKSPACE'])/'.github/workflows/etcd-adapter-currentness.yml'
        shutil.copyfile(workflow,out/'EXECUTED_WORKFLOW.yml')
        state['workflow_sha256']=hashlib.sha256(workflow.read_bytes()).hexdigest()
        context={k:os.environ.get(k) for k in ['GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_EVENT_NAME','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA','RUNNER_ENVIRONMENT','ImageVersion']}
        save(out/'JOB_CONTEXT.json',context)
        state['prepare_exit_code']=run(out,'PREPARE',[sys.executable,'-B',str(ROOT/'prepare_runtime.py')],65)
        if state['prepare_exit_code']!=0:raise RuntimeError('RUNTIME_PREPARATION_FAILED')
        state['driver_exit_code']=run(out,'DRIVER',[sys.executable,'-B',str(ROOT/'run_adapter.py'),'--output',str(out/'observations')],120)
        if state['driver_exit_code']!=0:raise RuntimeError('OBSERVATIONS_INCOMPLETE')
        state['offline_verifier_exit_code']=run(out,'OFFLINE_VERIFY',[sys.executable,'-B',str(ROOT/'verify_observations.py'),str(out/'observations')],15)
        if state['offline_verifier_exit_code']!=0:raise RuntimeError('OFFLINE_VERIFIER_REJECTED')
        state['state']='CAPTURE_COMPLETE_PENDING_ADJUDICATION'
    except Exception as e:state['error']=type(e).__name__+': '+str(e)
    finally:
        save(out/'CAPTURE_STATUS.json',state)
        save(out/'CAPTURE_MANIFEST.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='CAPTURE_MANIFEST.json'})
    print(json.dumps(state));return 0 if state['state']=='CAPTURE_COMPLETE_PENDING_ADJUDICATION' else 2
if __name__=='__main__':raise SystemExit(main())

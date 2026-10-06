"""Build observer only against pinned upstream; never rebuild the provider."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
from owned_etcd import demand,save,sha
COMMIT='a0614505aff9b8ff469e9c59c2d979a5936d13f4'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--upstream',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();up=Path(a.upstream).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
 env=dict(os.environ,GOWORK='off',GOTOOLCHAIN='local',GOFLAGS='-mod=readonly',GO111MODULE='on',CGO_ENABLED='0',GOOS='linux',GOARCH='amd64',GOPROXY='https://proxy.golang.org,direct',GOSUMDB='sum.golang.org')
 def run(label,args,cwd=up):
  r=subprocess.run(args,cwd=cwd,env=env,capture_output=True,timeout=300);(out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr);save(out/(label+'.command.json'),{'argv':args,'cwd':str(cwd),'returncode':r.returncode});demand(r.returncode==0,label+'_FAILED');return r.stdout
 demand(run('UPSTREAM_COMMIT',['git','rev-parse','HEAD']).decode().strip()==COMMIT,'UPSTREAM_COMMIT_MISMATCH');demand(run('INITIAL_STATUS',['git','status','--porcelain'])==b'','UPSTREAM_NOT_CLEAN')
 initial={str(p.relative_to(up)):sha(p) for pat in ('go.mod','go.sum') for p in up.rglob(pat) if p.is_file()};save(out/'UPSTREAM_MODULE_MANIFEST.json',initial)
 for n in initial:
  target=out/'UPSTREAM_MODULES'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(up/n,target)
 refs=json.loads((root/'SOURCE_RETRIEVAL_INDEX.json').read_text())
 for r in refs:demand(sha(up/r['path'])==r['sha256'],'REVIEW_SOURCE_MISMATCH_'+r['path'])
 program=up/'server/wal_control_observer';program.mkdir(exist_ok=False);shutil.copyfile(root/'observer.go',program/'main.go')
 go=shutil.which('go');demand(go is not None,'NO_GO_TOOLCHAIN');save(out/'TOOLCHAIN_BINARY.json',{'path':go,'sha256':sha(Path(go)),'observer_source_sha256':sha(root/'observer.go'),'upstream_commit':COMMIT,'provider_build':'NONE'})
 run('GO_VERSION',[go,'version']);run('GO_ENV',[go,'env','-json','GOVERSION','GOTOOLCHAIN','GOWORK','GOFLAGS','GOOS','GOARCH','CGO_ENABLED','GOPROXY','GOSUMDB','GOROOT'])
 run('BUILD',[go,'build','-trimpath','-buildvcs=false','-o',str(out/'wal-observer'),'./wal_control_observer'],up/'server')
 run('BUILD_INFO',[go,'version','-m',str(out/'wal-observer')]);run('MODULE_GRAPH',[go,'mod','graph'],up/'server');run('MODULE_LIST',[go,'list','-m','-json','all'],up/'server');run('MODULE_VERIFY',[go,'mod','verify'],up/'server')
 demand(initial=={n:sha(up/n) for n in initial},'MODULE_FILES_CHANGED');demand(run('TRACKED_DIFF',['git','diff','--exit-code'])==b'','TRACKED_SOURCE_CHANGED')
 final=run('FINAL_STATUS',['git','status','--porcelain']).decode().strip();demand(final=='?? server/wal_control_observer/','UNEXPECTED_UPSTREAM_MUTATION')
 save(out/'BUILD_IDENTITY.json',{'status':'BUILT_PENDING_CONTROL','upstream_commit':COMMIT,'observer_source_sha256':sha(root/'observer.go'),'executable_sha256':sha(out/'wal-observer'),'module_files_changed':False,'provider_rebuilt':False,'tracked_upstream_changed':False,'shared_decoder_ancestry':True,'controlling_pass':186,'classification':'NONCLAIM'})
 return 0
if __name__=='__main__':raise SystemExit(main())

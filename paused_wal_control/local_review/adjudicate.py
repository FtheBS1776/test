"""Offline adjudication using reviewed local code; never imports returned Python."""
import hashlib,json,os,stat,subprocess,sys,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R))
from verify_paused_review import check,inventory
from owned_etcd import demand,save,sha

def main():
 archive=R/sys.argv[1];meta=json.loads((R/'provider/PROVIDER_RECORDS.json').read_text());artifact=meta['artifact'];out=R/'evidence/github_attempt_01'
 demand(sha(archive)==artifact['digest'].split(':',1)[-1],'ARTIFACT_PROVIDER_DIGEST')
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();demand(len(names)==len(set(names)) and len(names)<1000 and sum(i.file_size for i in z.infolist())<200000000,'ZIP_BOUNDS')
  for i in z.infolist():
   p=Path(i.filename);demand(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and not stat.S_ISLNK(i.external_attr>>16),'ZIP_PATH')
  demand(z.testzip() is None,'ZIP_CRC')
  if not out.exists():out.mkdir(parents=True);z.extractall(out)
  else:
   demand(set(names)==set(inventory(out)),'EXTRACTED_ZIP_NAMES')
   for name in names:demand((out/name).read_bytes()==z.read(name),'EXTRACTED_ZIP_BYTES_'+name)
 demand(json.loads((out/'CAPTURE_MANIFEST.json').read_text())=={k:v for k,v in inventory(out).items() if k!='CAPTURE_MANIFEST.json'},'CAPTURE_INVENTORY')
 manifest=json.loads((R/'SOURCE_MANIFEST.json').read_text())
 for n,h in manifest.items():demand(sha(out/'SOURCE'/n)==sha(R/n)==h,'EXACT_REVIEWED_SOURCE_'+n)
 demand((out/'SOURCE/SOURCE_MANIFEST.json').read_bytes()==(R/'SOURCE_MANIFEST.json').read_bytes(),'MANIFEST_BYTES')
 demand((out/'EXECUTED_WORKFLOW.yml').read_bytes()==(R/'WORKFLOW_TEMPLATE.yml').read_bytes(),'WORKFLOW_BYTES')
 context=json.loads((out/'JOB_CONTEXT.json').read_text());run=meta['run']
 for k,v in {'GITHUB_SHA':run['head_sha'],'GITHUB_RUN_ID':str(run['id']),'GITHUB_RUN_ATTEMPT':str(run['attempt']),'GITHUB_REPOSITORY':'FtheBS1776/test','GITHUB_REPOSITORY_ID':'1395395411','RUNNER_ENVIRONMENT':'github-hosted','GITHUB_EVENT_NAME':'push'}.items():demand(context[k]==v,'CONTEXT_'+k)
 demand(context['GITHUB_WORKFLOW_SHA']==run['head_sha'] and context['GITHUB_WORKFLOW_REF']=='FtheBS1776/test/.github/workflows/etcd-paused-wal.yml@refs/heads/nonclaim/etcd-paused-wal-20261006','WORKFLOW_CONTEXT')
 bindings=json.loads((R/'GIT_BLOB_VERIFICATION.json').read_text());demand(bindings['status']=='PASS' and len(bindings['bindings'])==22,'PUBLISHED_SOURCE_BLOBS')
 build=out/'build';identity=json.loads((build/'BUILD_IDENTITY.json').read_text());demand(identity['upstream_commit']=='a0614505aff9b8ff469e9c59c2d979a5936d13f4' and identity['provider_rebuilt'] is False and identity['tracked_upstream_changed'] is False and identity['module_files_changed'] is False,'BUILD_SCOPE')
 demand(identity['observer_source_sha256']==sha(R/'observer.go') and identity['executable_sha256']==sha(build/'wal-observer'),'OBSERVER_BUILD_BINDING')
 prior=json.loads((R.parent/'strict_wal/INDEPENDENT_VERIFICATION.json').read_text());modulechecks=[]
 modulemap=json.loads((build/'UPSTREAM_MODULE_MANIFEST.json').read_text());demand(len(modulemap)==24,'MODULE_COUNT')
 for b in prior['module_git_blob_bindings']:
  data=(build/'UPSTREAM_MODULES'/b['path']).read_bytes();h=hashlib.sha256(data).hexdigest();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();demand(h==modulemap[b['path']]==b['sha256'] and blob==b['git_blob_sha1'],'UPSTREAM_GIT_BLOB_'+b['path']);modulechecks.append(b)
 cap=json.loads((out/'CAPTURE_STATUS.json').read_text());demand(cap['state']=='INDETERMINATE' and cap['verify_exit_code']==2 and all(cap[x+'_exit_code']==0 for x in ['prepare','build','control','observer']) and run['conclusion']=='failure','CAPTURE_STAGE_STATUS')
 observation=out/'observations';demand(json.loads((observation/'STATUS.json').read_text())['status']=='OBSERVATIONS_COMPLETE_PENDING_ADJUDICATION','DRIVER_STATUS')
 inputbinding=json.loads((out/'OBSERVER_INPUT_BINDING.json').read_text());demand(inputbinding['unchanged'] is True and inputbinding['before']==inputbinding['after']==inventory(observation/'snapshot'),'OBSERVER_WHOLE_CALL_INPUT')
 original=json.loads((out/'PAUSED_VERIFICATION.json').read_text());demand(original['status']=='REJECTED' and original['error']=='RuntimeError: FINAL_COMMIT_COVERAGE','ORIGINAL_REJECTION_PRESERVED')
 result=check(observation,out/'OBSERVER.stdout')
 local=R/'evidence/local_adjudication_01';local.mkdir(parents=True,exist_ok=False);binary=build/'wal-observer';binary.chmod(0o700);snapshot=observation/'snapshot';before=inventory(snapshot)
 runobs=subprocess.run([str(binary),str(snapshot)],capture_output=True,timeout=15,env={'PATH':'/usr/bin:/bin','LANG':'C','HOME':str(local)})
 (local/'OBSERVER.stdout').write_bytes(runobs.stdout);(local/'OBSERVER.stderr').write_bytes(runobs.stderr)
 demand(runobs.returncode==0 and inventory(snapshot)==before and runobs.stdout==(out/'OBSERVER.stdout').read_bytes(),'LOCAL_OBSERVER_EQUAL_IMMUTABLE')
 demand(check(observation,local/'OBSERVER.stdout')==result,'LOCAL_REEXECUTION_ADJUDICATION_EQUAL')
 save(local/'RESULT.json',result)
 summary={'verification':'PASS_BOUNDED_HEALTHY_PAUSED_CONTROL','classification':'NONCLAIM','controlling_pass':186,'promotion':False,'freeze':False,'run_id':run['id'],'attempt':run['attempt'],'commit':run['head_sha'],'artifact_id':artifact['id'],'artifact_sha256':sha(archive),'capture_files':len(inventory(out)),'published_git_blobs':22,'source_files':len(manifest),'upstream_module_files':len(modulechecks),'observer_executable_sha256':identity['executable_sha256'],'observer_source_sha256':identity['observer_source_sha256'],'original_github_verdict':'FAILURE; FINAL_COMMIT_COVERAGE','corrected_offline_verdict':'PASS; immutable original observations','reviewed_checker_sha256':sha(R/'verify_paused_review.py'),'local_observer_reexecution':'BYTE_IDENTICAL_OUTPUT_AND_UNCHANGED_INPUT','healthy_control':result,'local_attempt_01':'REJECTED_PID_NAMESPACE_MISMATCH; resumed and cleaned up','live_pending_entry':'UNESTABLISHED','independently_administered_production_provider_evidence':False,'main_unchanged':True}
 save(R/'INDEPENDENT_VERIFICATION.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()

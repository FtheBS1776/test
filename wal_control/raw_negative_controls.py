"""Damage owned copied WAL bytes only; preserve originals and failed reads."""
import argparse,json,shutil,subprocess,tempfile,hashlib
from pathlib import Path
from owned_etcd import demand,save,sha
from verify_control import model,validate
def main():
 ap=argparse.ArgumentParser();ap.add_argument('observations');ap.add_argument('observer');ap.add_argument('output');a=ap.parse_args();root=Path(a.observations).resolve();exe=Path(a.observer).resolve();out=Path(a.output).resolve();out.mkdir(exist_ok=False);original=root/'snapshot/member/wal/0000000000000000-0000000000000000.wal';original_sha=sha(original);results=[]
 for name in ['crc_corruption','prefix_only']:
  case=out/name;(case/'snapshot/member/wal').mkdir(parents=True);(case/'snapshot/member/snap').mkdir();p=case/'snapshot/member/wal'/original.name
  if name=='crc_corruption':
   shutil.copyfile(original,p)
   with p.open('r+b') as f:f.seek(8);old=f.read(1);demand(len(old)==1,'MUTATION_OFFSET');f.seek(8);f.write(bytes([old[0]^1]))
   recipe={'byte_offset':8,'xor':1,'original_byte':old.hex()}
  else:p.write_bytes(original.read_bytes()[:64]);recipe={'retained_prefix_bytes':64}
  save(case/'RECOMPUTED_SNAPSHOT_MANIFEST.json',{str(p.relative_to(case/'snapshot')):sha(p)})
  r=subprocess.run([str(exe),str(case/'snapshot')],capture_output=True,timeout=15);(case/'OBSERVER.stdout').write_bytes(r.stdout);(case/'OBSERVER.stderr').write_bytes(r.stderr)
  if r.returncode!=0:reason='OBSERVER_REJECTED'
  else:
   try:validate(model(root,json.loads(r.stdout)))
   except Exception as e:reason='BINDING_REJECTED: '+str(e)
   else:raise RuntimeError('DAMAGED_WAL_ACCEPTED_'+name)
  result={'mutation':name,'recipe':recipe,'recomputed_sha256':sha(p),'original_sha256':original_sha,'returncode':r.returncode,'rejected':True,'reason':reason};save(case/'RESULT.json',result);results.append(result)
 demand(sha(original)==original_sha,'ORIGINAL_SNAPSHOT_CHANGED');save(out/'RESULTS.json',results);print(json.dumps(results));return 0
if __name__=='__main__':raise SystemExit(main())

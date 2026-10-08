"""Controller adversarial tests, independent of candidate implementation details."""
import hashlib,json,os,stat,subprocess,sys,tempfile,warnings,zipfile
from pathlib import Path

def main():
 candidate=Path(sys.argv[1]).resolve();saved=Path(sys.argv[2]).resolve();checks=[]
 def sha(raw):return hashlib.sha256(raw).hexdigest()
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)
  def run(name,path,expected=None,accept=False):
   raw=path.read_bytes() if path.exists() else b'';expected=sha(raw) if expected is None else expected
   p=subprocess.run([sys.executable,'-B',str(candidate),str(path),'--expected-sha256',expected],capture_output=True,text=True)
   try:body=json.loads(p.stdout)
   except Exception:raise AssertionError((name,'NOT_JSON',p.returncode,p.stdout,p.stderr))
   assert not p.stderr,(name,'STDERR',p.stderr)
   assert (p.returncode==0)==accept,(name,p.returncode,body)
   assert body['status']==('PASS' if accept else 'REJECT'),(name,body)
   if accept:assert body['outer_sha256']==sha(raw) and body['evidence_scope']=='INTEGRITY_ONLY'
   checks.append({'check':name,'passed':True,'status':body['status']})
   return body
  def archive(name,members=None,manifest=None,duplicate=None):
   members={'payload.txt':b'DATA'} if members is None else members
   if manifest is None:manifest={n:{'sha256':sha(v),'size':len(v)} for n,v in members.items()}
   p=root/(name+'.zip')
   with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    with zipfile.ZipFile(p,'w',zipfile.ZIP_STORED) as z:
     for n,v in members.items():z.writestr(n,v)
     z.writestr('MANIFEST.json',json.dumps(manifest) if not isinstance(manifest,str) else manifest)
     if duplicate:z.writestr(*duplicate)
   return p
  valid=archive('valid');result=run('valid_basic',valid,accept=True);assert result['payload_files']==1
  saved_hash=sha(saved.read_bytes());run('real_saved_checkpoint',saved,saved_hash,True);assert sha(saved.read_bytes())==saved_hash
  run('outer_mismatch',valid,'0'*64);run('expected_hash_not_hex',valid,'z'*64)
  run('wrong_payload_hash',archive('bad_hash',manifest={'payload.txt':{'sha256':'0'*64,'size':4}}))
  run('wrong_size',archive('bad_size',manifest={'payload.txt':{'sha256':sha(b'DATA'),'size':3}}))
  run('bool_size',archive('bool_size',manifest={'payload.txt':{'sha256':sha(b'DATA'),'size':True}}))
  run('duplicate_member',archive('duplicate',duplicate=('payload.txt',b'DATA')))
  run('duplicate_manifest',archive('duplicate_manifest',duplicate=('MANIFEST.json',b'{}')))
  run('json_duplicate_key',archive('duplicate_json',manifest='{"payload.txt":{"sha256":"'+sha(b'DATA')+'","size":4,"size":4}}'))
  run('extra_manifest_key',archive('extra_meta',manifest={'payload.txt':{'sha256':sha(b'DATA'),'size':4,'trusted':True}}))
  run('unlisted_payload',archive('unlisted',manifest={}))
  run('missing_member',archive('missing',manifest={'missing':{'sha256':sha(b'DATA'),'size':4}}))
  for i,n in enumerate(['../escape','/absolute','a\\b','a//b','a/./b','C:drive','dir/']):run('unsafe_name_'+str(i),archive('unsafe'+str(i),members={n:b'DATA'}))
  p=root/'symlink.zip'
  with zipfile.ZipFile(p,'w') as z:
   info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'DATA');z.writestr('MANIFEST.json',json.dumps({'link':{'sha256':sha(b'DATA'),'size':4}}))
  run('symlink_rejected',p)
  p=archive('crc');raw=p.read_bytes();assert b'DATA' in raw;p.write_bytes(raw.replace(b'DATA',b'DAXA',1));run('crc_mismatch',p)
  p=root/'no_manifest.zip'
  with zipfile.ZipFile(p,'w') as z:z.writestr('p',b'DATA')
  run('missing_manifest',p)
  p=root/'bad_zip';p.write_bytes(b'not a zip');run('malformed_zip',p);run('missing_file',root/'missing.zip','0'*64)
  p=root/'too_many.zip'
  with zipfile.ZipFile(p,'w') as z:
   for n in range(4097):z.writestr(str(n),b'')
  run('member_count_bound',p)
  # Compressed fixture declared above member limit: reject before decompression.
  p=root/'large.zip'
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('large',b'0'*(24*1024*1024+1));z.writestr('MANIFEST.json',b'{}')
  run('member_uncompressed_bound',p)
  p=root/'manifest_large.zip'
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('MANIFEST.json',b' '*(1024*1024+1))
  run('manifest_bound',p)
  p=root/'total_large.zip'
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
   piece=b'0'*(22*1024*1024)
   for n in range(3):z.writestr(str(n),piece)
   z.writestr('MANIFEST.json',b'{}')
  run('total_uncompressed_bound',p)
 print(json.dumps({'status':'PASS','checks':checks,'count':len(checks),'candidate_sha256':sha(candidate.read_bytes()),'saved_checkpoint_unchanged':True},indent=2))
if __name__=='__main__':main()

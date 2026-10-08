import hashlib,json,subprocess,sys,tempfile,zipfile
from pathlib import Path

def main():
 code=Path(sys.argv[1]).resolve();checks=[]
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)
  def archive(name,members):
   p=root/(name+'.zip');m={n:{'sha256':hashlib.sha256(v).hexdigest(),'size':len(v)} for n,v in members.items()}
   with zipfile.ZipFile(p,'w') as z:
    for n,v in members.items():z.writestr(n,v)
    z.writestr('MANIFEST.json',json.dumps(m))
   return p
  def run(name,old,new,expect=None,hashold=None,hashnew=None):
   oh=hashold or hashlib.sha256(old.read_bytes()).hexdigest();nh=hashnew or hashlib.sha256(new.read_bytes()).hexdigest();p=subprocess.run([sys.executable,'-B',str(code),str(old),str(new),'--old-sha256',oh,'--new-sha256',nh],capture_output=True,text=True);assert not p.stderr,(name,p.stderr);result=json.loads(p.stdout)
   if expect is None:assert p.returncode!=0 and result['status']=='REJECT',(name,result)
   else:
    assert p.returncode==0 and result['status']=='PASS' and result['evidence_scope']=='INTEGRITY_COMPARISON_ONLY',(name,result)
    for field,want in expect.items():assert result[field]==want,(name,field,result[field],want)
   checks.append({'check':name,'passed':True,'status':result['status']});return result
  old=archive('old',{'same':b'A','changed':b'old','removed':b'gone'});new=archive('new',{'same':b'A','changed':b'new','added':b'fresh'})
  run('exact_diff',old,new,{'added':['added'],'removed':['removed'],'changed':['changed'],'unchanged':['same']});run('same_archive',old,old,{'added':[],'removed':[],'changed':[],'unchanged':['changed','removed','same']});run('reverse_diff',new,old,{'added':['removed'],'removed':['added'],'changed':['changed'],'unchanged':['same']})
  run('old_anchor_mismatch',old,new,hashold='0'*64);run('new_anchor_mismatch',old,new,hashnew='0'*64);run('malformed_hash',old,new,hashold='x')
  bad=root/'bad.zip';bad.write_bytes(b'badzip');run('invalid_new',old,bad);run('invalid_old',bad,new)
  corrupt=archive('corrupt',{'p':b'DATA'});raw=corrupt.read_bytes();corrupt.write_bytes(raw.replace(b'DATA',b'DAXA',1));run('crc_damage_not_reported_as_diff',old,corrupt)
  unsafe=archive('unsafe',{'../escape':b'a'});run('unsafe_not_reported_as_diff',old,unsafe)
  empt=archive('empty',{});run('empty_to_full',empt,new,{'added':['added','changed','same'],'removed':[],'changed':[],'unchanged':[]})
  # Actual saved packages: useful change inventory, with pinned anchors supplied outside archives.
  a=Path('GENIE_PERSISTED_WORKER_BRIDGE_20261008_NONCLAIM.zip').resolve();b=Path('GENIE_HOST_JOURNAL_AND_CHECKPOINT_TOOL_20261008_NONCLAIM.zip').resolve();before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)]
  result=run('actual_saved_checkpoints',a,b,{},hashold='8cc10a58413f44e755787ff81f5cf9591f1ee991b6300a003b92fd890967fb77',hashnew='5d7171daf6ffe2a658cbf2770833f3c43b4e6fb8a847ac4fae42057f5fbd653a');assert result['changed'] or result['added'] or result['removed'];assert before==[hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)]
 print(json.dumps({'status':'PASS','checks':checks,'count':len(checks),'code_sha256':hashlib.sha256(code.read_bytes()).hexdigest(),'actual_comparison':result,'saved_inputs_unchanged':True},indent=2))
if __name__=='__main__':main()

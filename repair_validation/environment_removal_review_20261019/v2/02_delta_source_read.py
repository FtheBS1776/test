from pathlib import Path
import zipfile,hashlib,difflib
base=Path('/workspace/scratch/27265db857a2')
v1=base/'GENIE_ENVIRONMENT_REMOVAL_REVIEW_INPUT_20261019.zip'
v2=base/'GENIE_ENVIRONMENT_REMOVAL_REVIEW_INPUT_v2_20261019.zip'
assert hashlib.sha256(v1.read_bytes()).hexdigest()=='7f7518ac03fa3f3d65da9d89ec91b4699bef3dd37d57a7012952505158ac862f'
assert hashlib.sha256(v2.read_bytes()).hexdigest()=='9f16004f5eb29bb6860db51aecd7c65500d1977cbc03b532be862a4cf955e9f4'
with zipfile.ZipFile(v1) as a,zipfile.ZipFile(v2) as b:
 for name in ('README_FIRST.md','REVIEW_CONTRACT.md','test_environment_removal.ps1','HOST_ENVIRONMENT_CORRECTION_20261019.md'):
  old=a.read(v1.stem+'/'+name);new=b.read(v2.stem+'/'+name)
  print('DELTA',name,'BYTE_IDENTICAL',old==new,'OLD_LENGTH',len(old),'NEW_LENGTH',len(new),'NEW_SHA256',hashlib.sha256(new).hexdigest())
  if old!=new:
   print(''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile='v1/'+name,tofile='v2/'+name)),end='')
 for name in ('HOST_ENVIRONMENT_CORRECTION_20261019.md','test_environment_removal.ps1'):
  print('\nNUMBERED_V2_SOURCE',name)
  for num,line in enumerate(b.read(v2.stem+'/'+name).decode().splitlines(),1):print(f'{num:04d} {line}')

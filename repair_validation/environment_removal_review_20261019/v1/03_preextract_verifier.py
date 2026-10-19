import pathlib,zipfile,hashlib,json,stat
p=pathlib.Path('/workspace/scratch/27265db857a2/GENIE_ENVIRONMENT_REMOVAL_REVIEW_INPUT_20261019.zip'); prefix=p.stem+'/'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='7f7518ac03fa3f3d65da9d89ec91b4699bef3dd37d57a7012952505158ac862f'
with zipfile.ZipFile(p) as z:
 infos=z.infolist(); names=[i.filename for i in infos]; assert len(names)==len(set(names))
 for i in infos:
  n=i.filename; mode=i.external_attr>>16
  assert n and not n.startswith('/') and '\\' not in n and '\x00' not in n and ':' not in n and all(x not in ('','.','..') for x in n.split('/'))
  assert not i.is_dir() and stat.S_IFMT(mode) in (0,stat.S_IFREG) and not i.flag_bits&1
  z.read(i)
 assert z.testzip() is None
 manifest=json.loads(z.read(prefix+'MANIFEST.json'))
 entries=manifest['files']; assert len(entries)==len({e['path'] for e in entries})
 assert set(names)=={prefix+'MANIFEST.json'}|{prefix+e['path'] for e in entries}
 print('OUTER_SHA256_PASS 7f7518ac03fa3f3d65da9d89ec91b4699bef3dd37d57a7012952505158ac862f')
 print('SAFE_UNIQUE_ORDINARY_MEMBERS_PASS 5; CRC_PASS')
 print('EXACT_MANIFEST_SET_PASS 4 declared payload files plus MANIFEST.json')
 for e in entries:
  b=z.read(prefix+e['path']); digest=hashlib.sha256(b).hexdigest(); assert len(b)==e['size'] and digest==e['sha256']
  print('FILE_PASS',e['path'],len(b),digest)
 out=pathlib.Path('/workspace/scratch/27265db857a2/environment_removal_cold_review_20261019')
 out.mkdir(exist_ok=False)
 for i in infos:
  target=out/i.filename; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(z.read(i))
 print('EXTRACTED_TO_NEW_EXCLUSIVE_DIRECTORY',out)
 for name in ('README_FIRST.md','REVIEW_CONTRACT.md'):
  print('\n'+name+' BEGIN\n'+z.read(prefix+name).decode()+'\n'+name+' END')

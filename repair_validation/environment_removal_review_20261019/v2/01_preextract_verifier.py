from pathlib import Path
import zipfile,stat,hashlib,json
p=Path('/workspace/scratch/27265db857a2/GENIE_ENVIRONMENT_REMOVAL_REVIEW_INPUT_v2_20261019.zip')
expected='9f16004f5eb29bb6860db51aecd7c65500d1977cbc03b532be862a4cf955e9f4'
raw=p.read_bytes()
print('INPUT',p)
print('OUTER_LENGTH',len(raw))
print('OUTER_SHA256',hashlib.sha256(raw).hexdigest())
assert hashlib.sha256(raw).hexdigest()==expected
with zipfile.ZipFile(p) as z:
 infos=z.infolist(); names=[i.filename for i in infos]
 assert len(names)==len(set(names))
 for i in infos:
  n=i.filename; mode=i.external_attr>>16
  assert n and not n.startswith('/') and '\\' not in n and '\x00' not in n and ':' not in n and all(t not in ('','.','..') for t in n.split('/'))
  assert not i.is_dir() and stat.S_IFMT(mode) in (0,stat.S_IFREG) and not i.flag_bits&1
  z.read(i)
  print('MEMBER',n,'LENGTH',i.file_size,'MODE',oct(mode),'CRC',hex(i.CRC))
 assert z.testzip() is None
 print('SAFE_UNIQUE_ORDINARY_NO_LINK_MEMBERS_AND_CRC_PASS')
 manifests=[n for n in names if n.endswith('/MANIFEST.json')]
 assert len(manifests)==1
 mn=manifests[0];prefix=mn[:-len('MANIFEST.json')]
 manifest_raw=z.read(mn);m=json.loads(manifest_raw)
 print('MANIFEST_RAW_BEGIN\n'+manifest_raw.decode()+'MANIFEST_RAW_END')
 entries=m['files'];assert len(entries)==len({e['path'] for e in entries})
 assert set(names)=={mn}|{prefix+e['path'] for e in entries}
 print('EXACT_MANIFEST_SET_PASS',len(entries))
 for e in entries:
  b=z.read(prefix+e['path']);d=hashlib.sha256(b).hexdigest()
  assert len(b)==e['size'] and d==e['sha256']
  print('MANIFEST_FILE_PASS',e['path'],len(b),d)
 out=Path('/workspace/scratch/27265db857a2/environment_removal_v2_cold_review_20261019')
 out.mkdir(exist_ok=False)
 for i in infos:
  target=out/i.filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(i))
 print('EXTRACTED_AFTER_ALL_CHECKS_TO_NEW_EXCLUSIVE_DIRECTORY',out)
 for name in ('README_FIRST.md','REVIEW_CONTRACT.md'):
  print('\n'+name+' BEGIN\n'+z.read(prefix+name).decode()+'\n'+name+' END')

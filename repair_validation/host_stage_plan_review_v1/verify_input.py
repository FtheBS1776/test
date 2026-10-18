from pathlib import Path,PurePosixPath
import zipfile,hashlib,stat,json,zlib,unicodedata
p=Path('/workspace/scratch/27265db857a2/GENIE_HOST_STAGE_REVIEW_INPUT_20261018.zip')
expected='84c4549a005746e3829219ea9a8422527bd08ee94d21345f6de5364515c4c698'
assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
with zipfile.ZipFile(p) as z:
 infos=z.infolist(); names=[i.filename for i in infos]
 assert len(names)==len(set(names))==len({unicodedata.normalize('NFC',n).casefold() for n in names})
 prefix='GENIE_HOST_STAGE_REVIEW_INPUT_20261018/'
 for i in infos:
  n=i.filename; q=PurePosixPath(n)
  assert n.startswith(prefix) and not q.is_absolute() and all(c not in ('','..','.') for c in n.split('/'))
  assert '\\' not in n and ':' not in n and not i.is_dir() and not (i.flag_bits&1)
  assert stat.S_ISREG(i.external_attr>>16) and not stat.S_ISLNK(i.external_attr>>16)
  b=z.read(i); assert len(b)==i.file_size and zlib.crc32(b)&0xffffffff==i.CRC
 m=json.loads(z.read(prefix+'MANIFEST.json'))
 paths=[f['path'] for f in m['files']]; assert len(paths)==len(set(paths))
 assert set(names)=={prefix+'MANIFEST.json'}|{prefix+x for x in paths}
 for f in m['files']:
  b=z.read(prefix+f['path']); assert len(b)==f['size'] and hashlib.sha256(b).hexdigest()==f['sha256']
 print('PASS outer SHA256',expected)
 print('PASS safe regular unique paths, including NFC/casefold uniqueness; no symlinks, encrypted entries, or directory entries')
 print('PASS ZIP CRC/lengths for',len(infos),'entries')
 print('PASS manifest exact set and SHA256/lengths for',len(paths),'files (manifest excludes itself)')
 print('manifest SHA256',hashlib.sha256(z.read(prefix+'MANIFEST.json')).hexdigest())

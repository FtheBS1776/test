import zipfile,pathlib,hashlib,json,stat,posixpath
p=pathlib.Path('/workspace/scratch/27265db857a2/GENIE_ENVIRONMENT_REMOVAL_REVIEW_INPUT_20261019.zip')
with zipfile.ZipFile(p) as z:
 infos=z.infolist(); names=[i.filename for i in infos]
 assert len(names)==len(set(names)), 'duplicate members'
 for i in infos:
  n=i.filename; q=pathlib.PurePosixPath(n); mode=i.external_attr>>16
  assert n and not n.startswith('/') and '\\' not in n and '\x00' not in n and all(x not in ('','.','..') for x in n.split('/')) and not q.is_absolute(), n
  assert not i.is_dir() and stat.S_IFMT(mode) in (0,stat.S_IFREG), (n,mode)
  assert not i.flag_bits & 1, 'encrypted'
  assert ':' not in n, n
  z.read(i)
 print('PATHS_UNIQUE_SAFE_ORDINARY true')
 print('CRC_TEST',z.testzip())
 mn=next(n for n in names if n.endswith('/MANIFEST.json'))
 raw=z.read(mn); print('MANIFEST_RAW_BEGIN'); print(raw.decode()); print('MANIFEST_RAW_END')

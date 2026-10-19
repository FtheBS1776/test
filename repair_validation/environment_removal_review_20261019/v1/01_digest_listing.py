import hashlib, pathlib, zipfile, stat
p=pathlib.Path('/workspace/scratch/27265db857a2/GENIE_ENVIRONMENT_REMOVAL_REVIEW_INPUT_20261019.zip')
b=p.read_bytes()
print('INPUT',p)
print('LENGTH',len(b))
print('SHA256',hashlib.sha256(b).hexdigest())
assert hashlib.sha256(b).hexdigest() == '7f7518ac03fa3f3d65da9d89ec91b4699bef3dd37d57a7012952505158ac862f'
with zipfile.ZipFile(p) as z:
 for i in z.infolist():
  print(repr(i.filename), 'length='+str(i.file_size), 'compressed='+str(i.compress_size),'mode='+oct(i.external_attr>>16),'CRC='+hex(i.CRC))

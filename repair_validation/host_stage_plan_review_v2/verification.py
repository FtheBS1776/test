import hashlib, json, stat, zipfile, shutil, sys
from pathlib import Path, PurePosixPath
source=Path('/workspace/scratch/27265db857a2/GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018.zip')
expected='e4e835c1d2581d73c16560b7b8ac6787b1a7bb06ae7dfe401c6e9426cdb6c2f8'
base=Path(__file__).resolve().parent
raw=source.read_bytes()
actual=hashlib.sha256(raw).hexdigest()
print('outer_sha256',actual, 'expected',expected)
assert actual==expected
root='GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018/'
with zipfile.ZipFile(source) as z:
    infos=z.infolist(); names=[i.filename for i in infos]
    assert len(names)==len(set(names))
    assert len(names)==len({n.casefold() for n in names})
    for i in infos:
        n=i.filename; p=PurePosixPath(n); mode=i.external_attr>>16; kind=stat.S_IFMT(mode)
        assert n.startswith(root) and not p.is_absolute() and '..' not in p.parts and '.' not in p.parts
        assert '\\' not in n and ':' not in n and '\x00' not in n and not n.endswith('/')
        assert n==str(p) and kind in (0,stat.S_IFREG), (n,oct(mode))
        assert not i.flag_bits&1
    print('safe_unique_regular_entries',len(infos),'(Unix type bits absent accepted as ordinary data files; no links/special files)')
    assert z.testzip() is None
    print('CRC_ALL_PASS')
    m=json.loads(z.read(root+'MANIFEST.json'))
    rows=m['files']; listed=[r['path'] for r in rows]
    assert len(listed)==len(set(listed))
    assert set(names)=={root+'MANIFEST.json'}|{root+n for n in listed}
    print('EXACT_MANIFEST_FILESET_PASS',len(rows),'payload files + manifest')
    for r in rows:
        data=z.read(root+r['path']); digest=hashlib.sha256(data).hexdigest()
        assert len(data)==r['size'] and digest==r['sha256'],r['path']
        print('FILE_PASS',r['path'],len(data),digest)
    print('ALL_CHECKS_PASSED_BEFORE_EXTRACTION')
    evidence=base/'immutable_input'; evidence.mkdir(exist_ok=False)
    dest=evidence/source.name
    with dest.open('xb') as f:f.write(raw)
    dest.chmod(0o444)
    out=base/'verified_input';out.mkdir(exist_ok=False)
    for i in infos:
        target=out/i.filename;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(z.read(i))
        target.chmod(0o444)
    print('EXTRACTED_INTO_NEW_EXCLUSIVE_DIRECTORY',out)
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
print('SOURCE_UNCHANGED_PASS')

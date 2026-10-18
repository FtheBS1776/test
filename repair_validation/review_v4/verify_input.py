"""Independently verify only the caller-specified archive and extracted copy."""
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

HERE=Path(__file__).resolve().parent
ARCHIVE=HERE.parent/'GENIE_REPAIR_REVIEW_INPUT_v4_20261018.zip'
EXPECTED='acaa546b3aa8abab8947b821c6bbe5c2c9f962e05d02c763929e5ddf4a274b0d'
PREFIX='GENIE_REPAIR_REVIEW_INPUT_v4_20261018/'
issues=[]
digest=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
assert digest==EXPECTED
with zipfile.ZipFile(ARCHIVE) as z:
    infos=z.infolist();names=[i.filename for i in infos]
    for key,items in collections.Counter(names).items():
        if items!=1:issues.append(['duplicate',key])
    folded=[str(PurePosixPath(n)).casefold() for n in names]
    if len(set(folded))!=len(folded):issues.append('normalized/casefold collision')
    for i in infos:
        n=i.filename;p=PurePosixPath(n)
        if p.is_absolute() or '..' in p.parts or '\\' in n or ':' in n or str(p)!=n or not n.startswith(PREFIX):issues.append(['unsafe_path',n])
        if stat.S_ISLNK(i.external_attr>>16):issues.append(['symlink',n])
        assert len(z.read(i))==i.file_size  # includes CRC validation
    assert z.testzip() is None
    manifests=[]
    for name in names:
        if PurePosixPath(name).name!='MANIFEST.json':continue
        raw=z.read(name);m=json.loads(raw);base=PurePosixPath(name).parent
        listed=[]
        for e in m['files']:
            target=str(base/e['path']);data=z.read(target)
            assert len(data)==e['size'] and hashlib.sha256(data).hexdigest()==e['sha256']
            local=HERE/'package'/target
            assert local.read_bytes()==data
            listed.append(target)
        assert len(set(listed))==len(listed)
        assert set(listed)|{name}==set(names)
        manifests.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'verified_file_count':len(listed),'declared_source_commit':m['source_commit'],'declared_source_tree':m['source_tree']})
    result={'archive':str(ARCHIVE),'expected_sha256':EXPECTED,'actual_sha256':digest,'archive_length':ARCHIVE.stat().st_size,'entry_count':len(infos),'total_uncompressed':sum(i.file_size for i in infos),'total_compressed_entries':sum(i.compress_size for i in infos),'maximum_entry_length':max(i.file_size for i in infos),'CRC':'all verified','path_duplicate_symlink_issues':issues,'manifests':manifests,'extracted_payload_byte_identity':'all verified'}
assert not issues
print(json.dumps(result,indent=2))

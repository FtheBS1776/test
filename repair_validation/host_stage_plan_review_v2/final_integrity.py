from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
expected='e4e835c1d2581d73c16560b7b8ac6787b1a7bb06ae7dfe401c6e9426cdb6c2f8'
original=Path('/workspace/scratch/27265db857a2/GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018.zip')
copy=base/'immutable_input'/original.name
for p in (original,copy):
    value=hashlib.sha256(p.read_bytes()).hexdigest();assert value==expected
    print('UNCHANGED_INPUT',p.name,len(p.read_bytes()),value)
root=base/'verified_input/GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018'
m=json.loads((root/'MANIFEST.json').read_bytes())
assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}=={'MANIFEST.json'}|{r['path'] for r in m['files']}
for row in m['files']:
    raw=(root/row['path']).read_bytes()
    assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
print('EXTRACTED_SOURCE_ALL_UNCHANGED',len(m['files']))
for name in ('verification.stderr.txt','static_checks.stderr.txt'):
    assert (base/name).read_bytes()==b''
print('REVIEWER_CHECK_STDERR_EMPTY')

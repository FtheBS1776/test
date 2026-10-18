from pathlib import Path
import hashlib,difflib,json,re
base=Path(__file__).resolve().parent
prior_base=Path('/workspace/scratch/27265db857a2/host_stage_plan_review_v2_yr59s5b4')
source=prior_base/'verified_input/GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018/source'
final=Path('/workspace/scratch/27265db857a2/HOST_STAGE_PLAN_FINAL_20261018.md')
old=source/'desktop_plugin/HOST_STAGE_PLAN_20261018.md'
expected_old='184aa37fb1e1b1df3631402803d3644d5dde0d54875a9549e5155ba1c5d033fe'
expected_final='7b83fce1abdad93ca075944c6872456cdbe38eaf86637875ecb616701edee73e'
raw_old=old.read_bytes();raw_final=final.read_bytes()
for name,raw,expected in (('prior_verified_plan',raw_old,expected_old),('final_standalone_plan',raw_final,expected_final)):
    observed=hashlib.sha256(raw).hexdigest();print('DIGEST',name,len(raw),observed);assert observed==expected
print('BOTH_PLAN_DIGESTS_PASS_BEFORE_COMPARISON')
a=b'with 36 distinct lock members (duplicate identical `pywin32` lines across files count once).'
b=b'with 36 distinct lock members, normalizing distribution names consistently.'
assert raw_old.count(a)==1
assert raw_final==raw_old.replace(a,b)
print('EXACT_SINGLE_BYTE_REPLACEMENT_PASS',repr(a),'=>',repr(b))
text_old=raw_old.decode('utf-8');text_final=raw_final.decode('utf-8')
diff=''.join(difflib.unified_diff(text_old.splitlines(keepends=True),text_final.splitlines(keepends=True),fromfile='prior_verified/HOST_STAGE_PLAN_20261018.md',tofile='final/HOST_STAGE_PLAN_FINAL_20261018.md'))
print(diff)
(base/'plan.diff').write_text(diff)
rows={};locations={}
expected_locks={'plugin_mcp_server/requirements.lock.txt':'32094c3926215c24d84b201fd19469bf4c8c87510e813872c687d755d1b8a9f0','desktop_plugin/windows-build.lock.txt':'77a84f95acd75d3338fee829e0b310ff3358fbdf815a9622450200d08e35e047'}
inputs=base/'inputs';inputs.mkdir(exist_ok=False)
for name,expected in expected_locks.items():
    raw=(source/name).read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest==expected
    print('LOCK_HASH_PASS',name,len(raw),digest)
    dest=inputs/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
    dest.chmod(0o444)
    for no,line in enumerate(raw.decode().splitlines(),1):
        if not line.strip() or line.lstrip().startswith('#'):continue
        m=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)',line);assert m
        key=re.sub(r'[-_.]+','-',m[1]).lower();version=m[2]
        assert key not in rows or rows[key]==version
        rows[key]=version;locations.setdefault(key,[]).append([name,no])
assert len(rows)==36
assert locations['pywin32']==[['desktop_plugin/windows-build.lock.txt',8]]
print('NORMALIZED_LOCK_UNION',len(rows))
print('PYWIN32_LOCATIONS',json.dumps(locations['pywin32']))
print('DUPLICATE_LOCK_MEMBERS',json.dumps({k:v for k,v in locations.items() if len(v)>1},sort_keys=True))
for name,raw in (('HOST_STAGE_PLAN_PRIOR_VERIFIED_20261018.md',raw_old),('HOST_STAGE_PLAN_FINAL_20261018.md',raw_final)):
    dest=inputs/name
    with dest.open('xb') as f:f.write(raw)
    dest.chmod(0o444)
for path,expected in ((Path('/workspace/scratch/27265db857a2/GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018.zip'),'e4e835c1d2581d73c16560b7b8ac6787b1a7bb06ae7dfe401c6e9426cdb6c2f8'),(prior_base.with_suffix('.zip'),'2de4d87ce39a908518a83e14e6cfbbc87a66d92593b24eb5b1933d5037902a41')):
    digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==expected
    print('ORIGINAL_ARCHIVE_UNCHANGED',path.name,digest)
print('EDITORIAL_CHECK_PASS_NO_SUBJECT_EXECUTION')

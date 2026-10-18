"""Reviewer-owned text/AST checks only; never imports subject code."""
import ast, hashlib, json, re, textwrap
from pathlib import Path
base=Path(__file__).resolve().parent
root=base/'verified_input/GENIE_HOST_STAGE_REVIEW_INPUT_v2_20261018/source'
def norm(name):return re.sub(r'[-_.]+','-',name).lower()
locks={}; occurrences={}
for name in ('plugin_mcp_server/requirements.lock.txt','desktop_plugin/windows-build.lock.txt'):
    for no,line in enumerate((root/name).read_text().splitlines(),1):
        if not line.strip() or line.lstrip().startswith('#'):continue
        m=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)',line)
        assert m,(name,no,line)
        key=norm(m[1]);version=m[2]
        assert key not in locks or locks[key]==version
        locks[key]=version;occurrences.setdefault(key,[]).append((name,no))
server=ast.parse((root/'shared_interfaces/mcp_server.py').read_bytes())
constants={n.targets[0].id:ast.literal_eval(n.value) for n in server.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('TRANSPORT_DISTRIBUTIONS','WINDOWS_TRANSPORT_DISTRIBUTIONS')}
action=(root/'.github/actions/genie-windows-package/action.yml').read_text()
chunk=re.search(r'expected.update\((\{.*?\})\)',action,re.S)[1]
closure={norm(k):v for d in (*constants.values(),ast.literal_eval(textwrap.dedent(chunk))) for k,v in d.items()}
assert locks==closure
assert len(locks)==36
print('STATIC_LOCK_UNION_EQUALS_WINDOWS_TRANSPORT_PLUS_ACTION_BUILD_MAPPING_PASS',len(locks))
print(json.dumps(locks,indent=2,sort_keys=True))
print('DUPLICATE_IDENTICAL_LOCK_MEMBERS',json.dumps({k:v for k,v in occurrences.items() if len(v)>1},sort_keys=True))
print('PYWIN32_OCCURRENCES',occurrences['pywin32'])
files=('desktop_plugin/test_frozen.py','desktop_plugin/live_state_windows.py','shared_interfaces/cli.py','standalone_app/owner.py','standalone_app/execution_bridge.py','canonical_state_provisioner/provisioner_windows.py')
for name in files:
    tree=ast.parse((root/name).read_bytes())
    print('TOP_LEVEL_STRUCTURE',name)
    for n in tree.body:
        print(n.lineno,type(n).__name__,ast.get_source_segment((root/name).read_text(),n).splitlines()[0])
for name in ('desktop_plugin/package/plugin.json','desktop_plugin/package/.codex-plugin/plugin.json','desktop_plugin/package/mcp.json','desktop_plugin/package/.mcp.json'):
    raw=(root/name).read_bytes(); obj=json.loads(raw)
    print('SOURCE_CONFIG',name,len(raw),hashlib.sha256(raw).hexdigest(),json.dumps(obj,sort_keys=True))
    if 'version' in obj:assert obj['version']=='0.2.0'
print('STATIC_SOURCE_ONLY_CHECKS_COMPLETED_NO_SUBJECT_IMPORT_OR_EXECUTION')

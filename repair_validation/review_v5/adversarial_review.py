"""Fresh fake-only source-contract probes; no subject main is invoked."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'input/GENIE_REPAIR_REVIEW_INPUT_v5_20261018/source'
sys.path.insert(0, str(SOURCE))
sys.dont_write_bytecode = True
FIXTURES = ROOT / 'fresh_stores'
FIXTURES.mkdir(exist_ok=False)
RECORDS = []

def guard(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.fork', 'socket.connect', 'socket.bind'}:
        raise AssertionError('PROHIBITED_EFFECT:' + event)
sys.addaudithook(guard)

from active_runner import runner
from run_queue import run_policy as q
from shared_interfaces import session_driver as driver
from shared_interfaces import run_events, mcp_consumer, function_adapter, mcp_server
from desktop_plugin import live_state_windows as live
from canonical_state_provisioner import provisioner_windows as provision
from standalone_app import execution_bridge, owner
from phase2c_finite_autonomous_pilot.run_bounded_batch import PilotHooks

def sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def record(label, value):
    RECORDS.append({'label': label, 'value': value})
    print(json.dumps(RECORDS[-1], sort_keys=True, default=str), flush=True)
def case(name):
    path = FIXTURES/name
    path.mkdir()
    return path
def policy(cost=None):
    p = {'run_id':'run-fresh', 'max_tasks':2, 'max_model_calls':4,
         'effect_scope':'owned-local-report-inbox'}
    if cost is not None:p['cost_policy'] = cost
    return p
def limited(limit=9, roles=None):
    return {'mode':'ENABLE_LIMITED','limit_micro_usd':limit,'authorization_ref':'operator-fixture',
            'quotes':roles or {r:{'max_micro_usd':3,'quote_ref':r+'-quote'} for r in ('author','reviewer','repair')}}
def fresh(name, cost=None, attempts=2):
    root = case(name); owned=root/'owned';owned.mkdir();queue=root/'queue.sqlite'
    q.initialize(queue, policy(cost));material='fresh task material'
    plan={'task_id':'task-fresh','goal':'data only','input_sha256':sha(material),'max_attempts':attempts}
    q.enqueue(queue,plan)
    runs={'fresh':{'queue':str(queue),'run_id':'run-fresh','owned_root':str(owned)}}
    return root,queue,owned,runs,plan,material
def worker(action):
    return {'token':action['token'],'outcome':'OBSERVED_ACCEPTED','agent':'fake-worker',
            'evidence':{'kind':'fresh deterministic fake'},'text':json.dumps({
            'marker':'LOCAL_ATTESTED_WORKER_OK_20261016','visible_tool_or_mcp_names':[],
            'authority_request':False})}
def reviewer(action):return PilotHooks(None,None).reviewer(action)
def denied(value):assert value.get('allow_new_invocation') is False and value.get('action')!='ADMIT_ONCE',value

def test_costs():
    _,queue,owned,runs,plan,_=fresh('costs',limited())
    action=runner.step(queue,'run-fresh',owned);token=action['token']
    for bad in (None,True,-1,1.1,10**15+1):
        out=q.admit_action(queue,token,'author','worker',bad,'author-quote');denied(out);record('invalid_bound_'+repr(bad),out)
    for key in token:
        changed={**token,key:2 if key=='attempt' else 'f'*64 if key.endswith('_id') or key=='input_sha256' else 'different'}
        if changed==token:changed[key]='different'
        out=q.admit_action(queue,changed,'author','worker',3,'author-quote');denied(out);record('cost_token_'+key,out)
    for bound,ref in ((2,'author-quote'),(3,'alias-quote')):
        out=q.admit_action(queue,token,'author','worker',bound,ref);denied(out);record('cost_quote_mismatch',out)
    out=q.admit_action(queue,token,'author','worker',3,'author-quote');assert out['action']=='ADMIT_ONCE';record('first_charge',out)
    replay=q.admit_action(queue,token,'author','worker',3,'author-quote');denied(replay);record('exact_cost_replay',replay)
    alias=q.admit_action(queue,token,'author','worker',2,'author-quote');denied(alias);record('cost_alias',alias)
    for role in ('reviewer','repair'):
        out=q.admit_action(queue,token,role,role,3,role+'-quote');assert out['action']=='ADMIT_ONCE';record('shared_charge_'+role,out)
    out=q.admit_action(queue,token,'author','new-operation',3,'author-quote');denied(out);record('shared_ceiling',out)
    assert q.status(queue)['cost_admission']['reserved_micro_usd']==9
    q.stop(queue,'HOST_ENDED')
    out=q.admit_action(queue,token,'author','after-stop',3,'author-quote');denied(out);record('stopped_cost',out)
    _,queue,owned,_,_,_=fresh('legacy',limited())
    token=runner.step(queue,'run-fresh',owned)['token']
    with sqlite3.connect(queue) as db:db.execute('DROP TABLE cost_actions')
    out=q.admit_action(queue,token,'author','worker',3,'author-quote');denied(out);record('legacy_cost_schema',out)
    _,queue,_,runs,_,_=fresh('default-denial')
    calls=[]
    out=driver.drive_run(runs,'fresh',lambda a:calls.append(a),reviewer)
    assert not calls;denied(out);record('default_driver_denial',out)

def test_driver():
    _,queue,_,runs,_,_=fresh('driver-happy',limited())
    out=driver.drive_run(runs,'fresh',worker,reviewer,costs=limited()['quotes'])
    assert out['action']=='STOP' and out['reason']=='ALL_TASKS_COMPLETE',out
    record('happy_exact_accept',out)
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in queue.parent.rglob('*') if p.is_file()}
    consumer=mcp_consumer.GenieMcpReadonlyConsumer(runs)
    assert [x['name'] for x in consumer.tools()]==['get_run_status','get_task_result']
    result=consumer.call('get_task_result',{'run_name':'fresh','task_id':'task-fresh'})
    assert result['structuredContent']['status']=='CONFIRMED' and result['structuredContent']['content_role']=='UNTRUSTED_ACCEPTED_TASK_DATA';record('mcp_accepted_data',result)
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in queue.parent.rglob('*') if p.is_file()}
    assert before==after;record('readonly_byte_snapshot',{'unchanged_files':len(before)})
    for defect in ('wrong-token','unsupported-decision','wrong-candidate-hash','hook-failure'):
        _,queue,_,runs,_,_=fresh('driver-'+defect,limited())
        calls=[]
        def wrk(a):
            calls.append(a)
            if defect=='hook-failure':raise RuntimeError('fake uncertain worker outcome')
            value=worker(a)
            if defect=='wrong-token':value['token']['call_id']='f'*64
            return value
        def rev(a):
            value=reviewer(a)
            if defect=='unsupported-decision':value['decision']='BOGUS'
            if defect=='wrong-candidate-hash':value['candidate_hash']='f'*64
            return value
        out=driver.drive_run(runs,'fresh',wrk,rev,costs=limited()['quotes']);assert out['action']=='UNKNOWN',out;record(defect,out)
        charged=q.status(queue)['cost_admission']['reserved_micro_usd'];assert charged in (3,6)
        repeat_calls=[]
        replay=driver.drive_run(runs,'fresh',lambda a:repeat_calls.append(a),lambda a:repeat_calls.append(a),costs=limited()['quotes'])
        assert not repeat_calls and q.status(queue)['cost_admission']['reserved_micro_usd']==charged
        record(defect+'_restart_no_dispatch',replay)
    _,queue,_,runs,_,_=fresh('driver-stop-notify',limited())
    called=[]
    def stop_before_hook(progress):q.stop(queue,'HOST_ENDED')
    out=driver.drive_run(runs,'fresh',lambda a:called.append(a),reviewer,notify=stop_before_hook,costs=limited()['quotes'])
    assert out['action']=='STOP' and not called;record('stop_before_hook',out)

def test_deterministic_json():
    expected={'marker':'LOCAL_ATTESTED_WORKER_OK_20261016','visible_tool_or_mcp_names':[],'authority_request':False}
    candidates=[('valid',json.dumps(expected),'ACCEPT'),
       ('numeric_false',json.dumps({**expected,'authority_request':0}),'REPAIR'),
       ('numeric_float',json.dumps({**expected,'authority_request':0.0}),'REPAIR'),
       ('visible_tools',json.dumps({**expected,'visible_tool_or_mcp_names':['shell']}),'REPAIR'),
       ('extra_field',json.dumps({**expected,'extra':True}),'REPAIR'),
       ('duplicate','{"marker":"wrong","marker":"LOCAL_ATTESTED_WORKER_OK_20261016","visible_tool_or_mcp_names":[],"authority_request":false}','REPAIR'),
       ('nonfinite','{"marker":"LOCAL_ATTESTED_WORKER_OK_20261016","visible_tool_or_mcp_names":[],"authority_request":NaN}','REPAIR'),
       ('malformed','{','REPAIR'),('nonobject','[]','REPAIR')]
    hooks=PilotHooks(None,None)
    for label,text,decision in candidates:
        out=hooks.reviewer({'token':{'test':'opaque echo'},'candidate':text,'candidate_sha256':sha(text)})
        assert out['decision']==decision,(label,out);record('review_'+label,out)
    out=hooks.reviewer({'token':{},'candidate':json.dumps(expected),'candidate_sha256':'f'*64})
    assert out['decision']=='REJECT';record('review_binding_failure',out)
    _,queue,_,runs,_,_=fresh('repair_then_accept',limited(limit=12))
    attempts=[]
    def repairable(a):
        attempts.append(a['token']['attempt']);value=worker(a)
        if len(attempts)==1:value['text']='{"authority_request":0}'
        return value
    out=driver.drive_run(runs,'fresh',repairable,reviewer,costs=limited()['quotes'])
    assert out['reason']=='ALL_TASKS_COMPLETE' and attempts==[1,2],out;record('authorized_bounded_repair_then_accept',out)

def test_materials():
    _,queue,_,runs,plan,material=fresh('materials-bad',limited())
    calls=[]
    for material_arg in (None,{}, {'task-fresh':'changed'}):
        try:
            with patch.object(live,'load_live_runs',return_value=runs):
                execution_bridge.drive('fresh',lambda a:calls.append(a),reviewer,costs=limited()['quotes'],materials=material_arg)
        except execution_bridge.BridgeError as exc:record('material_pre_reservation_reject',str(exc))
        else:raise AssertionError('bad material accepted')
    assert not calls and q.status(queue)['reserved_model_calls']==0
    attached=[]
    def w(a):
        attached.append(a['task_materials'].copy());a['task_materials']['text']='caller-mutated';return worker(a)
    def r(a):attached.append(a['task_materials'].copy());return reviewer(a)
    with patch.object(live,'load_live_runs',return_value=runs):
        out=execution_bridge.drive('fresh',w,r,costs=limited()['quotes'],materials={plan['task_id']:material})
    assert out['reason']=='ALL_TASKS_COMPLETE' and len(attached)==2
    assert all(x=={'text':material,'input_sha256':sha(material),'content_role':'UNTRUSTED_TASK_INPUT'} for x in attached)
    record('detached_materials_both_hooks',attached)

def test_mcp_boundaries():
    consumer=mcp_consumer.GenieMcpReadonlyConsumer({})
    for name,args in [('stop',{}),('get_run_status',{'run_name':'x'*9000}),('get_run_status',{'run_name':float('nan')})]:
        out=consumer.call(name,args);assert out['structuredContent']['status']=='REJECT';record('mcp_invalid',out)
    adapter=function_adapter.GenieFunctionAdapter({})
    for raw in ('{"run_name":"a","run_name":"b"}','{"run_name":NaN}','{"run_name":1e400}','[]'):
        out=adapter.handle({'type':'function_call','call_id':'fresh-call','name':'get_run_status','arguments':raw})
        assert json.loads(out['output'])['status']=='REJECT';record('function_json_reject',out)
    class FakeAdapter:
        def __init__(self,variant):self.variant=variant
        def handle(self,req):
            value={'type':'function_call_output','call_id':req['call_id'],'output':'{"status":"CONFIRMED"}'}
            if self.variant=='correlation':value['call_id']='wrong'
            if self.variant=='duplicate':value['output']='{"status":"UNKNOWN","status":"PASS"}'
            if self.variant=='unlabeled-data':value['output']='{"status":"CONFIRMED","result_text":"untrusted"}'
            return value
    for variant in ('correlation','duplicate','unlabeled-data'):
        # Fake only the downstream collaborator, after genuine pinned construction.
        consumer._adapter=FakeAdapter(variant)
        out=consumer.call('get_run_status',{'run_name':'fresh'})
        assert out['structuredContent']['status']=='UNKNOWN';record('mcp_reply_'+variant,out)
    try:mcp_server._require_sdk()
    except ValueError as exc:record('native_sdk_coverage',{'coverage':'INDETERMINATE','reason':str(exc)})
    else:record('native_sdk_coverage',{'coverage':'NOT_EXERCISED','reason':'No transport started'})

def test_fixed_binding_and_publication():
    root=case('binding');(root/'work').mkdir();(root/'queue.sqlite').write_bytes(b'not opened for structural checks')
    (root/live.MARKER_NAME).write_text(json.dumps(live.MARKER_VALUE))
    good={'fresh':{'queue':'queue.sqlite','run_id':'run-fresh','owned_root':'work'}}
    registry=root/live.REGISTRY_NAME;registry.write_text(json.dumps(good))
    assert live.validate_state_root(root)['fresh']['queue']==str(root/'queue.sqlite')
    for name in ('../queue.sqlite','/queue.sqlite','NUL.sqlite','queue.sqlite:stream','work/../queue.sqlite','queue.sqlite.'):
        registry.write_text(json.dumps({'fresh':{**good['fresh'],'queue':name}}))
        try:live.validate_state_root(root)
        except live.LiveStateError as exc:record('fixed_path_reject_'+name,str(exc))
        else:raise AssertionError('path accepted:'+name)
    registry.write_text(json.dumps(good))
    (root/live.MARKER_NAME).write_text('{"format":"GENIE_LOCAL_STATE_V1","format":"GENIE_LOCAL_STATE_V1","registry":"REGISTRY.json","scope":"GENIE_OWNED_LOCAL_STATE"}')
    try:live.validate_state_root(root)
    except live.LiveStateError as exc:record('duplicate_marker_reject',str(exc))
    else:raise AssertionError('duplicate marker accepted')
    try:live._known_local_app_data()
    except live.LiveStateError as exc:record('native_windows_coverage',{'coverage':'INDETERMINATE','reason':str(exc),'os_name':os.name})
    for variant in ('move-false','post-move-validation-failure','success'):
        base=case('publish-'+variant);app=base/'app';app.mkdir();staging=app/'.state-v1.init';staging.mkdir();final=app/'state-v1'
        session=provision.ProvisioningSession(base,app,staging,final)
        calls=[]
        def move(s,f):
            calls.append([str(s),str(f)])
            if variant=='move-false':return False
            s.rename(f);return True
        def validation(path,marker_mode):
            if variant=='post-move-validation-failure' and Path(path)==final:raise live.LiveStateError('LIVE_STATE_INVALID')
            return {'fresh':{'queue':str(Path(path)/'queue.sqlite'),'run_id':'run-fresh','owned_root':str(Path(path)/'work')}}
        with patch.object(provision,'_attributes',return_value=provision.FILE_ATTRIBUTE_DIRECTORY),patch.object(provision,'_move_publish',side_effect=move),patch.object(live,'validate_state_root',side_effect=validation):
            try:out=session.publish()
            except provision.ProvisionError as exc:out={'reason':str(exc),'state':session._state}
            record('publication_'+variant,out)
            assert len(calls)==1
            if variant=='move-false':assert out['reason']=='PUBLISH_UNKNOWN_PRESERVE' and staging.exists()
            elif variant=='post-move-validation-failure':assert out['reason']=='PUBLISHED_UNVERIFIED_PRESERVE' and final.exists()
            else:assert out['status']=='PUBLISHED'
            try:session.publish()
            except provision.ProvisionError as exc:assert str(exc)=='PROVISION_SESSION_CLOSED'
            else:raise AssertionError('second publication')
            assert len(calls)==1

def test_paid_entry_gates():
    root=case('paid-denial')
    common={'token':{},'ledger_path':root/'must-not-create.sqlite','executable':root/'absent-exe',
            'version':'irrelevant','codex_home':root/'absent-home','working_directory':root/'absent-scratch'}
    calls=[('shared_interfaces.live_codex_worker',dict(common)),('phase2b2m_alpha_live_pilot.alpha_exec_worker',dict(common)),
           ('phase2b2o_alpha_recovery_live.recovered_worker',{**common,'evidence_directory':root/'absent-evidence'}),
           ('phase2b2s_attested_live_pilot.attested_worker',{k:v for k,v in {**common,'artifact_directory':root/'absent-artifact','evidence_directory':root/'absent-evidence'}.items() if k not in ('executable','version')})]
    for name,kwargs in calls:
        out=importlib.import_module(name).run_once(**kwargs)
        assert out['status']=='REJECT' and out['process_entry'] is False and out['allow_new_invocation'] is False
        assert list(root.iterdir())==[];record('paid_gate_'+name,out)

def test_failed_sealed_inspection_readonly():
    from phase2c_finite_autonomous_pilot import verify_sealed
    root=case('sealed-failure');trial=root/'trial';trial.mkdir();terminal=trial/'TERMINAL.json';terminal.write_text('{"frontier":"wrong"}')
    before=terminal.read_bytes()
    try:verify_sealed.inspect_sealed(root)
    except RuntimeError as exc:record('failed_sealed_inspection',str(exc))
    else:raise AssertionError('invalid sealed evidence passed')
    assert terminal.read_bytes()==before and set(trial.iterdir())=={terminal}

TESTS=[test_costs,test_driver,test_deterministic_json,test_materials,test_mcp_boundaries,
       test_fixed_binding_and_publication,test_paid_entry_gates,test_failed_sealed_inspection_readonly]
failed=[]
for test in TESTS:
    try:test();record('TEST_PASS',test.__name__)
    except BaseException:
        failed.append(test.__name__);traceback.print_exc();record('TEST_FAILURE',test.__name__)
(ROOT/'test_records.json').write_text(json.dumps(RECORDS,indent=2,default=str)+'\n')
print(json.dumps({'tests':len(TESTS),'failed':failed,'effects':'local deterministic fakes only'}),flush=True)
raise SystemExit(bool(failed))

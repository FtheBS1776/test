import hashlib,json
from pathlib import Path
from shared_interfaces.function_adapter import GenieFunctionAdapter
from shared_interfaces import cli
root=Path.cwd()
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj): Path(p).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
source=Path('shared_interfaces/candidate/function_adapter.py').read_bytes()
assert hashlib.sha256(source).hexdigest()=='9627bc0967e4b6115f405671be8a2c60498101e276d96062d55572537f2769d2'
runs=cli._read_registry(str(root/'host_return/trial/REGISTRY.json'))
runs['pending']={'queue':str(root/'session_driver/trial/queue.sqlite'),'run_id':'genie-session-driver-run-20261010','owned_root':str(root/'session_driver/trial/work')}
adapter=GenieFunctionAdapter(runs)
facade=cli._load_facade().GenieStatusTools(runs)
cases=[('get_run_status',{'run_name':'actual'}),('get_task_result',{'run_name':'actual','task_id':'genie-work-host-entry-20261010'}),('get_task_result',{'run_name':'actual','task_id':'genie-plugin-routing-inventory-20261010'}),('get_task_result',{'run_name':'pending','task_id':'genie-session-driver-guide-20261010'})]
rows=[]
for i,(name,args) in enumerate(cases):
    expected=facade.call(name,args)
    call={'type':'function_call','call_id':f'readonly-{i}','name':name,'arguments':json.dumps(args)}
    reply=adapter.handle(call)
    actual=json.loads(reply['output'])
    assert reply['call_id']==call['call_id'] and actual==expected
    assert actual['status']==['PASS','CONFIRMED','CONFIRMED','UNKNOWN'][i]
    rows.append({'name':name,'arguments':args,'reply':reply,'equal_to_direct_facade':True})
save('plugin_local/trial/READONLY_COMPARISON.json',rows)
checks={}
for label,file in [('prior_stores','plugin_local/STORES_BEFORE.json'),('core_guide_pins','host_continuation/SOURCE_BINDINGS.json'),('frozen_inputs','plugin_local/INPUT_MANIFEST.json')]:
    pins=json.loads(Path(file).read_text()); assert all(digest(p)==h for p,h in pins.items());checks[label]={'count':len(pins),'unchanged':True}
checks.update({'comparison_harness_corrections':1,'status':'PASS','new_component_tests':16,'readonly_comparisons':4,'source_repairs':0,'new_model_calls':0,'new_task_reservations':0})
save('plugin_local/VERIFICATION.json',checks)
print(json.dumps(checks))

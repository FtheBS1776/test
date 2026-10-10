"""Focused callable-interface checks; no completed fixture or provider rerun."""
import hashlib, importlib.util, json, pathlib, sys, types, unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT/'shared_interfaces/candidate/status_tool.py'
spec = importlib.util.spec_from_file_location('status_tool_candidate', SOURCE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
REGISTRY = {'completed': {'queue': str(ROOT/'host_continuation/trial/queue.sqlite'),
    'run_id':'genie-host-continuation-run-20261010',
    'owned_root': str(ROOT/'host_continuation/trial/work')}}

class InterfaceTests(unittest.TestCase):
    def setUp(self): self.tool = m.GenieStatusTools(REGISTRY)
    def call(self, args=None, name='get_run_status'):
        return self.tool.call(name, {'run_name':'completed'} if args is None else args)
    def test_descriptor(self):
        t=self.tool.tools(); self.assertEqual(len(t),1);x=t[0]
        self.assertEqual(x['name'],'get_run_status');s=x['inputSchema']
        self.assertEqual(s,{'type':'object','properties':{'run_name':{'type':'string'}},'required':['run_name'],'additionalProperties':False})
        self.assertEqual(x['annotations'],{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False})
        self.assertNotIn(str(ROOT),json.dumps(t)); self.assertIn('history',x['description'])
    def test_metadata_detached(self):
        t=self.tool.tools();t[0]['inputSchema']['properties']['run_name']['type']='number'
        self.assertEqual(self.tool.tools()[0]['inputSchema']['properties']['run_name']['type'],'string')
    def test_bad_tools_no_core(self):
        with patch.object(m,'_load_core',side_effect=AssertionError('core forbidden')) as load:
            for name in ['step','submit','review','GET_RUN_STATUS','',None,[],{}]:
                self.assertEqual(self.call(name=name),{'status':'REJECT','reason':'UNSUPPORTED_TOOL'})
            load.assert_not_called()
    def test_bad_arguments_no_core(self):
        with patch.object(m,'_load_core',side_effect=AssertionError('core forbidden')) as load:
            for arg in [[],{},False,{'run_name':1},{'run_name':None},{'run_name':[]},{'run_name':'completed','queue':'/etc/passwd'},{'run_name':'completed','owned_root':'/'},{'run_name':'completed','run_id':'other'}]:
                self.assertEqual(self.call(arg),{'status':'REJECT','reason':'INVALID_ARGUMENTS'})
            load.assert_not_called()
    def test_unknown_alias_no_core(self):
        with patch.object(m,'_load_core',side_effect=AssertionError('core forbidden')) as load:
            for alias in ['unknown','../completed','/etc/passwd','', 'COMPLETED','completed\x00']:
                self.assertEqual(self.call({'run_name':alias}),{'status':'REJECT','reason':'UNKNOWN_RUN'})
            load.assert_not_called()
    def test_registry_snapshot(self):
        registry={'alias':dict(REGISTRY['completed'])};tool=m.GenieStatusTools(registry)
        registry['alias']['queue']='/bad';registry['alias']['run_id']='bad';registry.clear()
        core=types.SimpleNamespace(report=unittest.mock.Mock(return_value={'marker':'unchanged'}))
        with patch.object(m,'_load_core',return_value=core):
            self.assertEqual(tool.call('get_run_status',{'run_name':'alias'}),{'marker':'unchanged'})
        cfg=REGISTRY['completed'];core.report.assert_called_once_with(cfg['queue'],cfg['run_id'],cfg['owned_root'])
    def test_invalid_registry_sanitized(self):
        for registry in [[],{'x':[]},{'x':{'queue':'PRIVATE_SENTINEL'}},{'x':{'queue':'/x','run_id':False,'owned_root':'/x'}},{'x':{'queue':'','run_id':'r','owned_root':'/x'}}]:
            with self.assertRaisesRegex(ValueError,'^INVALID_RUN_REGISTRY$'):m.GenieStatusTools(registry)
    def test_source_pin(self):
        with patch.object(m.Path,'read_bytes',return_value=b'not reviewed source'):
            self.assertEqual(self.call(),{'status':'REJECT','reason':'STATUS_SOURCE_BINDING'})
    def test_core_failure_sanitized(self):
        core=types.SimpleNamespace(report=unittest.mock.Mock(side_effect=ValueError('/PRIVATE_PATH PRIVATE_PAYLOAD')))
        with patch.object(m,'_load_core',return_value=core):
            self.assertEqual(self.call(),{'status':'REJECT','reason':'CORE_FAILURE'})
    def test_read_failure_sanitized(self):
        with patch.object(m.Path,'read_bytes',side_effect=OSError('/PRIVATE_PATH')):
            self.assertEqual(self.call(),{'status':'REJECT','reason':'CORE_FAILURE'})
    def test_core_semantics_preserved(self):
        for sink in ['UNKNOWN','MISMATCH','CONFIRMED']:
            out={'status':'PASS','queue_history':{'state':'STOPPED'},'tasks':[{'fresh_sink':{'status':sink}}],'background_execution':False}
            core=types.SimpleNamespace(report=unittest.mock.Mock(return_value=out))
            with patch.object(m,'_load_core',return_value=core):self.assertEqual(self.call(),out)
    def test_actual_existing_readback_and_sources(self):
        old=json.loads((ROOT/'shared_interfaces/STORES_BEFORE.json').read_text())
        before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in old}
        out=self.call();cfg=REGISTRY['completed'];direct=m._load_core().report(cfg['queue'],cfg['run_id'],cfg['owned_root'])
        self.assertEqual(out,direct);self.assertEqual(out['status'],'PASS')
        self.assertEqual(out['tasks'][0]['fresh_sink']['status'],'CONFIRMED')
        self.assertFalse(out['background_execution']);self.assertNotIn(str(ROOT),json.dumps(out))
        self.assertNotIn('candidate',json.dumps(out));self.assertNotIn('evidence',out['tasks'][0]['journal'])
        self.assertEqual(before,{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in old})
        pins=json.loads((ROOT/'host_continuation/SOURCE_BINDINGS.json').read_text())
        self.assertTrue(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items()))

if __name__=='__main__':unittest.main()

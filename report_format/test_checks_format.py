"""Frozen root oracle: explicit rich checks, original captured hash, no metadata authority."""
import hashlib, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path

CODE=Path(sys.argv.pop(1)).resolve()
spec=importlib.util.spec_from_file_location('rich_report',CODE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SCOPE='TEST_LOG_SUMMARY_ONLY'

class ChecksFormat(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=self.root/'raw.json'
    def tearDown(self):self.tmp.cleanup()
    def base(self):return {'status':'PASS','count':1,'checks':[{'check':'expected rejection','passed':True,'status':'REJECT'}],'artifact':'not independently verified'}
    def entry(self,data=None,raw=None,fmt='checks'):
        raw=json.dumps(data or self.base()).encode() if raw is None else raw
        self.p.write_bytes(raw);r=m.build_report([{'path':str(self.p),'format':fmt}]);self.assertEqual(r['execution_claim'],'NONE');self.assertEqual(r['fresh_sink_claim'],'NONE');self.assertEqual(r['evidence_scope'],SCOPE);self.assertNotIn('count',r)
        e=r['entries'][0];self.assertEqual(e['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(e['bytes'],len(raw));self.assertEqual(self.p.read_bytes(),raw);return e
    def assert_summary(self,e,status,count):self.assertEqual(e['summary'],{'status':status,'count':count,'evidence_scope':SCOPE})
    def test_rich_pass_ignores_per_check_status(self):
        e=self.entry();self.assert_summary(e,'PASS',1);self.assertEqual(e['projection'],{'scope':'STATUS_COUNT_CHECK_FLAGS_ONLY','ignored_top_fields':['artifact'],'ignored_check_fields':['status']})
    def test_rich_failure(self):
        d=self.base();d['status']='FAIL';d['checks'][0]['passed']=False;self.assert_summary(self.entry(d),'FAIL',1)
    def test_rejected_boolean_flag(self):
        d=self.base();d['checks'][0]={'check':'x','rejected':True,'unused':False};self.assert_summary(self.entry(d),'PASS',1)
    def test_zero_is_no_coverage_despite_metadata(self):
        self.assert_summary(self.entry({'status':'PASS','count':0,'checks':[],'authority_valid':True}),'NO_COVERAGE',0)
    def test_declared_pass_false_flag_rejects(self):
        d=self.base();d['checks'][0]['passed']=False;e=self.entry(d);self.assert_summary(e,'REJECT',None);self.assertIsNotNone(e['projection'])
    def test_bool_count_rejects(self):
        d=self.base();d['count']=True;self.assert_summary(self.entry(d),'REJECT',None)
    def test_count_mismatch(self):
        d=self.base();d['count']=2;self.assert_summary(self.entry(d),'REJECT',None)
    def test_flag_nonbool(self):
        d=self.base();d['checks'][0]['passed']=1;self.assert_summary(self.entry(d),'REJECT',None)
    def test_both_flags_invalid_projection(self):
        d=self.base();d['checks'][0]['rejected']=True;e=self.entry(d);self.assert_summary(e,'REJECT',None);self.assertIsNone(e['projection'])
    def test_missing_core_invalid_projection(self):
        d=self.base();del d['count'];self.assertIsNone(self.entry(d)['projection'])
    def test_nonlist_checks_invalid_projection(self):
        d=self.base();d['checks']={};self.assertIsNone(self.entry(d)['projection'])
    def test_nonobject_check_invalid_projection(self):
        d=self.base();d['checks']=[True];self.assertIsNone(self.entry(d)['projection'])
    def test_nested_duplicate_metadata_rejects(self):
        raw=b'{"status":"PASS","count":0,"checks":[],"meta":{"x":1,"x":2}}';e=self.entry(raw=raw);self.assert_summary(e,'REJECT',None);self.assertIsNone(e['projection'])
    def test_nan_metadata_rejects(self):
        e=self.entry(raw=b'{"status":"PASS","count":0,"checks":[],"meta":NaN}');self.assert_summary(e,'REJECT',None)
    def test_infinite_metadata_rejects(self):
        e=self.entry(raw=b'{"status":"PASS","count":0,"checks":[],"meta":Infinity}');self.assert_summary(e,'REJECT',None)
    def test_float_overflow_metadata_rejects(self):
        e=self.entry(raw=b'{"status":"PASS","count":0,"checks":[],"meta":1e999}');self.assert_summary(e,'REJECT',None)
    def test_ignored_fields_sorted_unique(self):
        d={'status':'PASS','count':2,'checks':[{'check':'a','passed':True,'z':False,'a':'PASS'},{'check':'b','passed':True,'z':'REJECT'}],'z':{},'a':False};e=self.entry(d);self.assertEqual(e['projection']['ignored_top_fields'],['a','z']);self.assertEqual(e['projection']['ignored_check_fields'],['a','z']);self.assert_summary(e,'PASS',2)
    def test_no_extras_empty_projection_names(self):
        e=self.entry({'status':'PASS','count':1,'checks':[{'check':'x','passed':True}]});self.assertEqual(e['projection']['ignored_top_fields'],[]);self.assertEqual(e['projection']['ignored_check_fields'],[])
    def test_legacy_json_still_rejects_rich(self):
        e=self.entry(fmt='json');self.assert_summary(e,'REJECT',None);self.assertNotIn('projection',e)
    def test_legacy_json_unchanged_valid(self):
        e=self.entry({'status':'PASS','count':1,'checks':[{'check':'x','passed':True}]},fmt='json');self.assert_summary(e,'PASS',1);self.assertNotIn('projection',e)
    def test_unreadable_new_format_projection_null(self):
        e=m.build_report([{'path':str(self.p),'format':'checks'}])['entries'][0];self.assertIsNone(e['sha256']);self.assertIsNone(e['projection']);self.assert_summary(e,'REJECT',None)
    def test_unknown_format_before_read(self):
        with self.assertRaises(ValueError):m.build_report([{'path':str(self.p),'format':'check'}])
    def test_cli_direct_original_and_existing_guard(self):
        self.p.write_text(json.dumps(self.base()));out=self.root/'report.json';args=[sys.executable,'-B',str(CODE),'--output',str(out),'--input','checks',str(self.p)];p=subprocess.run(args,capture_output=True,text=True,timeout=5);self.assertEqual(p.returncode,0);self.assertEqual(p.stderr,'');body=json.loads(out.read_text());self.assert_summary(body['entries'][0],'PASS',1);before=out.read_bytes();p=subprocess.run(args,capture_output=True,text=True,timeout=5);self.assertEqual(p.returncode,2);self.assertEqual(out.read_bytes(),before)

if __name__=='__main__':unittest.main(verbosity=2)

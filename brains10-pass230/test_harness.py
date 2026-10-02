import hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, unittest
spec=importlib.util.spec_from_file_location('capture',pathlib.Path(__file__).with_name('run_evidence.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class CaptureChecks(unittest.TestCase):
    def test_changed_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);(p/'subject.txt').write_text('expected')
            h.write_json(p/'SOURCE_MANIFEST.json',{'subject.txt':h.sha(p/'subject.txt')})
            digest=h.sha(p/'SOURCE_MANIFEST.json');h.verify_source(p,digest)
            (p/'subject.txt').write_text('changed')
            with self.assertRaises(ValueError):h.verify_source(p,digest)
    def test_extra_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);h.write_json(p/'SOURCE_MANIFEST.json',{})
            digest=h.sha(p/'SOURCE_MANIFEST.json');(p/'extra.py').write_text('')
            with self.assertRaises(ValueError):h.verify_source(p,digest)
    def test_wrong_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);h.write_json(p/'SOURCE_MANIFEST.json',{})
            with self.assertRaises(ValueError):h.verify_source(p,'0'*64)
    def test_timeout_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'output.txt'
            rc=h.command([sys.executable,'-c','import time; time.sleep(2)'],p,timeout=0.05)
            self.assertEqual(rc,124)
            self.assertIn('HARNESS_COMMAND_TIMEOUT',p.read_text())
            self.assertEqual(json.loads(p.with_suffix('.txt.command.json').read_text())['exit_code'],124)
    def test_timeout_stops_child_process(self):
        import time
        with tempfile.TemporaryDirectory() as td:
            marker=pathlib.Path(td)/'late-write'
            child='import time,pathlib;time.sleep(0.3);pathlib.Path('+repr(str(marker))+').write_text("late")'
            parent='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'+repr(child)+']);time.sleep(2)'
            rc=h.command([sys.executable,'-c',parent],pathlib.Path(td)/'log',timeout=0.05)
            time.sleep(0.4)
            self.assertEqual(rc,124);self.assertFalse(marker.exists())
    def test_failed_command_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'output.txt'
            rc=h.command([sys.executable,'-c','print("partial output"); raise SystemExit(7)'],p)
            self.assertEqual(rc,7);self.assertIn('partial output',p.read_text())
    def test_existing_evidence_is_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);(p/'sentinel').write_text('keep')
            r=subprocess.run([sys.executable,'-B',str(h.BASE/'run_evidence.py'),'--output',str(p),'--expected-manifest','0'*64,'--local-rehearsal'],capture_output=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual((p/'sentinel').read_text(),'keep')
    def test_original_not_accepted_as_repaired(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):h.extract_gate(h.BASE/'original_gate.zip',pathlib.Path(td))
    def test_pre_execution_failure_is_sealed(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'new'
            r=subprocess.run([sys.executable,'-B',str(h.BASE/'run_evidence.py'),'--output',str(p),'--expected-manifest','0'*64,'--local-rehearsal'],capture_output=True)
            self.assertEqual(r.returncode,2)
            self.assertEqual(json.loads((p/'CAPTURE_STATUS.json').read_text())['status'],'INDETERMINATE')
            manifest=json.loads((p/'EVIDENCE_MANIFEST.json').read_text())
            self.assertEqual(manifest['CAPTURE_STATUS.json'],h.sha(p/'CAPTURE_STATUS.json'))

if __name__=='__main__':unittest.main()

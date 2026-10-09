"""Frozen root checks for the outer-input resource contract."""
import hashlib, importlib.util, io, json, os, stat, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch

CODE = Path(sys.argv.pop(1)).resolve()
spec = importlib.util.spec_from_file_location('bounded_verifier', CODE)
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

def archive():
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z: z.writestr('MANIFEST.json', b'{}')
    return b.getvalue()

class BoundChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.p = self.root/'input.zip'; self.raw = archive(); self.p.write_bytes(self.raw)
    def tearDown(self): self.tmp.cleanup()
    def verify(self, raw=None, expected=None):
        if raw is not None: self.p.write_bytes(raw)
        return v.verify(self.p, expected or hashlib.sha256(self.p.read_bytes()).hexdigest())
    def test_production_cap(self): self.assertEqual(v.MAX_ARCHIVE, 64*1024*1024)
    def test_small_valid(self): self.assertEqual(self.verify()['status'], 'PASS')
    def test_exact_boundary(self):
        raw = b'\0'*(4096-len(self.raw))+self.raw
        with patch.object(v, 'MAX_ARCHIVE', 4096): self.assertEqual(self.verify(raw)['status'], 'PASS')
    def test_one_byte_above_preparse(self):
        with patch.object(v, 'MAX_ARCHIVE', 4096), patch.object(v.zipfile, 'ZipFile', side_effect=AssertionError('ZIP opened')):
            with self.assertRaises(v.Rejected): self.verify(b'\0'*(4097-len(self.raw))+self.raw)
    def test_growing_read_bound(self):
        self.p.write_bytes(b'\0'*10000)
        actual_fstat = os.fstat; actual_open = open; read_sizes = []
        class Reader:
            def __init__(self, f): self.f=f
            def __enter__(self): return self
            def __exit__(self,*args): self.f.close()
            def fileno(self): return self.f.fileno()
            def read(self, n=-1): read_sizes.append(n); return self.f.read(n)
            def seek(self,*args): return self.f.seek(*args)
        def understated(fd):
            st=actual_fstat(fd); fields=list(st); fields[6]=1; return os.stat_result(fields)
        def tracked(*args,**kwargs): return Reader(actual_open(*args,**kwargs))
        with patch.object(v, 'MAX_ARCHIVE', 4096), patch.object(v.os, 'fstat', understated), patch.object(v, 'open', tracked, create=True), patch.object(v.zipfile, 'ZipFile', side_effect=AssertionError('ZIP opened')):
            with self.assertRaises(v.Rejected): v.verify(self.p, '0'*64)
        self.assertTrue(read_sizes); self.assertTrue(all(0 < n <= 4097 for n in read_sizes)); self.assertLessEqual(sum(read_sizes),4097)
    def test_anchor_before_zip(self):
        with patch.object(v.zipfile, 'ZipFile', side_effect=AssertionError('ZIP opened')):
            with self.assertRaises(v.Rejected): self.verify(expected='0'*64)
    def test_nonregular_descriptor(self):
        actual=os.fstat
        def changed(fd):
            fields=list(actual(fd)); fields[0]=stat.S_IFCHR|0o600; return os.stat_result(fields)
        with patch.object(v.os,'fstat',changed), patch.object(v.zipfile,'ZipFile',side_effect=AssertionError('ZIP opened')):
            with self.assertRaises(v.Rejected): self.verify()
    @unittest.skipUnless(hasattr(os,'mkfifo') and hasattr(os,'O_NONBLOCK'),'Unix only')
    def test_fifo_cli_bounded(self):
        p=self.root/'pipe'; os.mkfifo(p)
        got=subprocess.run([sys.executable,'-B',str(CODE),str(p),'--expected-sha256','0'*64],capture_output=True,text=True,timeout=3)
        self.assertEqual(got.returncode,2); self.assertEqual(json.loads(got.stdout)['status'],'REJECT'); self.assertEqual(got.stderr,'')
    def test_symlink_regular_allowed(self):
        link=self.root/'link'; link.symlink_to(self.p)
        self.assertEqual(v.verify(link,hashlib.sha256(self.raw).hexdigest())['status'],'PASS')
    def test_input_unchanged(self):
        before=self.p.read_bytes(); self.verify(); self.assertEqual(self.p.read_bytes(),before)

if __name__=='__main__': unittest.main(verbosity=2)

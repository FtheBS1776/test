"""R05 inspection checks on byte-verified disposable copies; no model calls."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from phase2c_finite_autonomous_pilot import verify_sealed as verifier


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class ReadonlyVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.copy = self.root / "evidence"
        self.copy.mkdir()
        shutil.copytree(verifier.HERE / "trial", self.copy / "trial")
        self.assertEqual(manifest(verifier.HERE / "trial"), manifest(self.copy / "trial"))
        shutil.copyfile(verifier.HERE / "VERIFICATION.json", self.copy / "VERIFICATION.json")
        self.before = manifest(self.copy)

    def run_main(self, *args):
        with redirect_stdout(io.StringIO()):
            return verifier.main(["--evidence-directory", str(self.copy), *map(str, args)])

    def test_default_inspection_preserves_every_input_byte_and_name(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(manifest(self.copy), self.before)

    def test_explicit_external_report_is_exclusive_and_input_is_unchanged(self):
        report = self.root / "report.json"
        self.assertEqual(self.run_main("--report", report), 0)
        self.assertEqual(json.loads(report.read_text())["status"], "PASS")
        saved = report.read_bytes()
        with self.assertRaisesRegex(ValueError, "REPORT_COLLISION"):
            self.run_main("--report", report)
        self.assertEqual(report.read_bytes(), saved)
        self.assertEqual(manifest(self.copy), self.before)

    def test_internal_report_paths_cannot_create_or_overwrite(self):
        for name in ("new.json", "VERIFICATION.json"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "REPORT_INSIDE_EVIDENCE"):
                self.run_main("--report", self.copy / name)
        self.assertEqual(manifest(self.copy), self.before)

    def test_external_symlink_to_input_cannot_overwrite(self):
        link = self.root / "link.json"
        try:
            link.symlink_to(self.copy / "VERIFICATION.json")
        except OSError:
            self.skipTest("host does not permit test symlink creation")
        with self.assertRaisesRegex(ValueError, "REPORT_INSIDE_EVIDENCE"):
            self.run_main("--report", link)
        self.assertEqual(manifest(self.copy), self.before)

    def test_invalid_copy_is_not_repaired_or_rewritten(self):
        (self.copy / "trial" / "PROGRESS.jsonl").write_text("{}\n")
        damaged = manifest(self.copy)
        with self.assertRaises((KeyError, RuntimeError)):
            self.run_main()
        self.assertEqual(manifest(self.copy), damaged)


if __name__ == "__main__":
    unittest.main(verbosity=2)

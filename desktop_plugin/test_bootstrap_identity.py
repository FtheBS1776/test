"""Exact bootstrap identity through main; no model, SDK or real transport."""
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop_plugin import entry


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


class BootstrapIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.seed = self.root / entry.SEED_DIR
        self.seed.mkdir()
        raw = b"{}\n"
        (self.seed / "REGISTRY.json").write_bytes(raw)
        self.record = {"path": "REGISTRY.json", "size": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}

    def launch(self):
        stderr = io.StringIO()
        with patch.object(entry, "_strict_data_root", return_value=self.data), patch.object(
                entry, "_bundle_root", return_value=self.root), patch.object(
                entry, "_run_transport") as transport, patch.object(
                entry.os, "environ", {}), redirect_stderr(stderr):
            result = entry.main()
        return result, transport, stderr.getvalue()

    def test_valid_first_launch_and_existing_state_preserve_identity(self):
        (self.seed / entry.SEED_MANIFEST).write_text(json.dumps(
            {"seed_id": "fixture-seed", "files": [self.record]}))
        result, transport, error = self.launch()
        self.assertEqual((result, error), (0, ""))
        registry = self.data / "state" / "REGISTRY.json"
        transport.assert_called_once_with(registry)
        marker = json.loads((registry.parent / entry.STATE_MARKER).read_text())
        self.assertIs(type(marker["state_format"]), int)
        self.assertEqual(marker["seeded_from"], "fixture-seed")
        before = snapshot(self.root)
        result, transport, error = self.launch()
        self.assertEqual((result, error), (0, ""))
        transport.assert_called_once_with(registry)
        self.assertEqual(snapshot(self.root), before)

    def test_invalid_marker_never_enters_transport_or_reseeds(self):
        state = self.data / "state"
        state.mkdir()
        (state / "REGISTRY.json").write_bytes(b"{}\n")
        cases = (
            '{"state_format":true,"seeded_from":"seed"}',
            '{"state_format":1.0,"seeded_from":"seed"}',
            '{"state_format":2,"state_format":1,"seeded_from":"seed"}',
            '{"state_format":1,"seeded_from":"other","seeded_from":"seed"}',
        )
        for raw in cases:
            with self.subTest(marker=raw):
                (state / entry.STATE_MARKER).write_text(raw)
                before = snapshot(self.root)
                with patch.object(entry.shutil, "copytree") as copy:
                    result, transport, error = self.launch()
                self.assertEqual(result, 2)
                self.assertEqual(error, "GENIE_PLUGIN_REJECT:PLUGIN_STATE_PARTIAL_PRESERVE\n")
                transport.assert_not_called()
                copy.assert_not_called()
                self.assertEqual(snapshot(self.root), before)

    def test_duplicate_seed_fields_reject_before_state_copy(self):
        record = json.dumps(self.record)
        changed = '{"path":"wrong","path":"REGISTRY.json","size":3,"sha256":' + json.dumps(self.record["sha256"]) + '}'
        cases = (
            '{"seed_id":"other","seed_id":"seed","files":[' + record + ']}',
            '{"seed_id":"seed","files":[],"files":[' + record + ']}',
            '{"seed_id":"seed","files":[' + changed + ']}',
        )
        for raw in cases:
            with self.subTest(manifest=raw):
                (self.seed / entry.SEED_MANIFEST).write_text(raw)
                before = snapshot(self.root)
                with patch.object(entry.shutil, "copytree") as copy:
                    result, transport, error = self.launch()
                self.assertEqual(result, 2)
                self.assertEqual(error, "GENIE_PLUGIN_REJECT:SEED_INTEGRITY\n")
                transport.assert_not_called()
                copy.assert_not_called()
                self.assertEqual(snapshot(self.root), before)


if __name__ == "__main__":
    unittest.main()

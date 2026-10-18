"""First-run copy uncertainty must survive later launches. NO MODEL CALL."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop_plugin import entry


class BootstrapPreservationTests(unittest.TestCase):
    def test_copy_failure_keeps_partial_bytes_and_blocks_reseed(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)

            def interrupted_copy(_source, destination, **_kwargs):
                destination.mkdir()
                (destination / "partial.sqlite").write_bytes(b"preserve interrupted copy")
                raise OSError("injected copy failure")

            with patch.object(entry, "_strict_data_root", return_value=data), patch.object(
                    entry, "_read_seed_manifest", return_value=("fixture", "unused")), patch.object(
                    entry.shutil, "copytree", side_effect=interrupted_copy) as copy:
                with self.assertRaisesRegex(entry._BootstrapReject, "^PLUGIN_STATE_INIT_UNKNOWN$"):
                    entry._provision_state()
                staged = list(data.glob(".state.init-*"))
                self.assertEqual(len(staged), 1)
                self.assertEqual((staged[0] / "partial.sqlite").read_bytes(), b"preserve interrupted copy")
                self.assertFalse((data / "state").exists())
                with self.assertRaisesRegex(entry._BootstrapReject, "^PLUGIN_STATE_PARTIAL_PRESERVE$"):
                    entry._provision_state()
                self.assertEqual(copy.call_count, 1)
                self.assertEqual((staged[0] / "partial.sqlite").read_bytes(), b"preserve interrupted copy")

    def test_publish_failure_keeps_marker_and_blocks_reseed(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)

            def complete_copy(_source, destination, **_kwargs):
                destination.mkdir()
                (destination / "REGISTRY.json").write_text("{}\n")

            with patch.object(entry, "_strict_data_root", return_value=data), patch.object(
                    entry, "_read_seed_manifest", return_value=("fixture", "unused")), patch.object(
                    entry.shutil, "copytree", side_effect=complete_copy) as copy, patch.object(
                    Path, "replace", side_effect=OSError("injected move failure")) as move:
                with self.assertRaisesRegex(entry._BootstrapReject, "^PLUGIN_STATE_INIT_UNKNOWN$"):
                    entry._provision_state()
                staged = list(data.glob(".state.init-*"))
                self.assertEqual(len(staged), 1)
                before = {p.name: p.read_bytes() for p in staged[0].iterdir()}
                self.assertIn(entry.STATE_MARKER, before)
                with self.assertRaisesRegex(entry._BootstrapReject, "^PLUGIN_STATE_PARTIAL_PRESERVE$"):
                    entry._provision_state()
                self.assertEqual((copy.call_count, move.call_count), (1, 1))
                self.assertEqual({p.name: p.read_bytes() for p in staged[0].iterdir()}, before)
                self.assertFalse((data / "state").exists())


if __name__ == "__main__":
    unittest.main()

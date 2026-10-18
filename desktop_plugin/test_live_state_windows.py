"""Reused native checks from fa4e291cfd1aa7147f39f359008f8d74a2f69798; package imports adapted.
All mutation is confined to a disposable test namespace. No model calls.
"""
import hashlib
import os
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from desktop_plugin import live_state_windows as live
from shared_interfaces import status_tool


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.original = live._known_local_app_data
        live._known_local_app_data = lambda: self.base

    def tearDown(self):
        live._known_local_app_data = self.original
        self.temp.cleanup()

    def _root(self):
        root = self.base / live.APP_DIR / live.STATE_DIR
        root.parent.mkdir(exist_ok=True)
        return root

    @unittest.skipUnless(os.name == "nt", "native Windows Known Folder API required")
    def test_native_known_folder_is_existing_absolute_directory(self):
        # Read the actual OS-selected base without provisioning any state there.
        base = self.original()
        self.assertTrue(base.is_absolute())
        self.assertTrue(base.is_dir())

    def _marker(self, root, value=None):
        (root / live.MARKER_NAME).write_text(
            json.dumps(value or live.MARKER_VALUE, sort_keys=True,
                       separators=(",", ":")) + "\n", encoding="utf-8")

    def _fixture(self):
        root = self._root()
        shutil.copytree(Path("host_return/trial"), root)
        self._marker(root)
        return root

    def test_missing_root_rejects(self):
        with self.assertRaisesRegex(live.LiveStateError, "^LIVE_STATE_UNAVAILABLE$"):
            live.load_live_runs()

    def test_marker_exact_shape(self):
        root = self._root()
        root.mkdir()
        self._marker(root, {**live.MARKER_VALUE, "extra": "x"})
        (root / live.REGISTRY_NAME).write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(live.LiveStateError, "^LIVE_STATE_INVALID$"):
            live.load_live_runs()

    def test_path_traversal_and_absolute_reject(self):
        for queue in ("../outside.sqlite", "C:\\outside.sqlite", "CON.sqlite"):
            root = self._root()
            root.mkdir()
            self._marker(root)
            registry = {"actual": {
                "queue": queue,
                "run_id": "genie-work-host-return-20261010",
                "owned_root": "work",
            }}
            (root / live.REGISTRY_NAME).write_text(
                json.dumps(registry) + "\n", encoding="utf-8")
            (root / "work").mkdir()
            with self.assertRaisesRegex(live.LiveStateError, "^LIVE_STATE_PATH$"):
                live.load_live_runs()
            shutil.rmtree(root)

    def test_valid_binding_reuses_existing_parser_and_reads_only(self):
        root = self._fixture()
        sqlite_files = sorted(root.rglob("*.sqlite"))
        before = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sqlite_files}
        runs = live.load_live_runs()
        self.assertEqual(set(runs), {"actual"})
        self.assertEqual(Path(runs["actual"]["queue"]).parent, root)
        self.assertEqual(Path(runs["actual"]["owned_root"]).parent, root)
        host = status_tool.GenieStatusTools(runs)
        status = host.call("get_run_status", {"run_name": "actual"})
        self.assertEqual(status.get("status"), "PASS")
        confirmed = [item for item in status.get("tasks", [])
                     if isinstance(item, dict)
                     and isinstance(item.get("fresh_sink"), dict)
                     and item["fresh_sink"].get("status") == "CONFIRMED"]
        self.assertTrue(confirmed)
        result = host.call("get_task_result", {
            "run_name": "actual", "task_id": confirmed[0]["task_id"]})
        self.assertEqual(result.get("status"), "CONFIRMED")
        self.assertEqual(result.get("content_role"), "UNTRUSTED_ACCEPTED_TASK_DATA")
        after = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sqlite_files}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()

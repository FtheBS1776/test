import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import live_state_windows as live
import provisioner_windows as provision
from shared_interfaces import status_tool


def _tree_hash(root):
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.original_known = live._known_local_app_data
        live._known_local_app_data = lambda: self.base

    def tearDown(self):
        live._known_local_app_data = self.original_known
        self.temp.cleanup()

    def app(self):
        return self.base / live.APP_DIR

    def final(self):
        return self.app() / live.STATE_DIR

    def staging(self):
        return self.app() / provision.STAGING_DIR

    def populate_fixture(self, workspace):
        shutil.copytree(Path("host_return/trial"), workspace, dirs_exist_ok=True)

    def test_begin_is_fixed_and_second_begin_preserves(self):
        session = provision.begin()
        self.assertEqual(session.workspace, self.staging())
        self.assertTrue(self.staging().is_dir())
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_STAGING_EXISTS_PRESERVE$"):
            provision.begin()
        self.assertTrue(self.staging().is_dir())

    def test_concurrent_begin_has_one_winner(self):
        def attempt():
            try:
                return ("OPEN", provision.begin())
            except provision.ProvisionError as exc:
                return (str(exc), None)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _n: attempt(), range(2)))
        labels = sorted(item[0] for item in outcomes)
        self.assertEqual(labels, ["OPEN", "PROVISION_STAGING_EXISTS_PRESERVE"])
        self.assertTrue(self.staging().is_dir())

    def test_existing_final_rejects_without_staging(self):
        self.app().mkdir()
        self.final().mkdir()
        sentinel = self.final() / "sentinel.txt"
        sentinel.write_text("preserve\n", encoding="utf-8")
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_FINAL_EXISTS$"):
            provision.begin()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
        self.assertFalse(self.staging().exists())

    def test_abandoned_staging_rejects_and_preserves(self):
        self.app().mkdir()
        self.staging().mkdir()
        sentinel = self.staging() / "partial.txt"
        sentinel.write_text("do not clean\n", encoding="utf-8")
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_STAGING_EXISTS_PRESERVE$"):
            provision.begin()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not clean\n")

    def test_app_directory_junction_rejects(self):
        outside = self.base / "outside-app"
        outside.mkdir()
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.app()), str(outside)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        self.assertEqual(made.returncode, 0, (made.stdout, made.stderr))
        try:
            with self.assertRaisesRegex(
                    provision.ProvisionError, "^PROVISION_NAMESPACE_INVALID$"):
                provision.begin()
        finally:
            os.rmdir(self.app())

    def test_incomplete_publish_preserves_staging_without_marker(self):
        session = provision.begin()
        (session.workspace / "unrelated.txt").write_text("partial\n", encoding="utf-8")
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_STAGING_INVALID_PRESERVE$"):
            session.publish()
        self.assertTrue(self.staging().is_dir())
        self.assertFalse((self.staging() / live.MARKER_NAME).exists())
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_SESSION_CLOSED$"):
            _ = session.workspace
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_STAGING_EXISTS_PRESERVE$"):
            provision.begin()

    def test_preseeded_marker_rejects_and_preserves(self):
        session = provision.begin()
        self.populate_fixture(session.workspace)
        marker = session.workspace / live.MARKER_NAME
        marker.write_text(json.dumps(live.MARKER_VALUE) + "\n", encoding="utf-8")
        before = _tree_hash(session.workspace)
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_STAGING_INVALID_PRESERVE$"):
            session.publish()
        self.assertEqual(_tree_hash(self.staging()), before)
        self.assertFalse(self.final().exists())

    def test_destination_appearing_before_publish_never_replaced(self):
        session = provision.begin()
        self.populate_fixture(session.workspace)
        self.final().mkdir()
        sentinel = self.final() / "existing.txt"
        sentinel.write_text("winner\n", encoding="utf-8")
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_FINAL_EXISTS$"):
            session.publish()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "winner\n")
        self.assertTrue(self.staging().is_dir())
        self.assertFalse((self.staging() / live.MARKER_NAME).exists())

    def test_reported_move_failure_is_unknown_and_preserves(self):
        session = provision.begin()
        self.populate_fixture(session.workspace)
        original_move = provision._move_publish
        provision._move_publish = lambda _staging, _final: False
        try:
            with self.assertRaisesRegex(
                    provision.ProvisionError, "^PUBLISH_UNKNOWN_PRESERVE$"):
                session.publish()
        finally:
            provision._move_publish = original_move
        self.assertTrue(self.staging().is_dir())
        self.assertTrue((self.staging() / live.MARKER_NAME).is_file())
        self.assertFalse(self.final().exists())
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_SESSION_CLOSED$"):
            session.publish()

    def test_post_move_validation_failure_is_committed_unverified(self):
        session = provision.begin()
        self.populate_fixture(session.workspace)
        original_validate = live.validate_state_root

        def injected(root, marker_mode="required"):
            resolved = Path(root).resolve(strict=True)
            if resolved.name == live.STATE_DIR:
                raise live.LiveStateError("INJECTED_POST_MOVE_FAILURE")
            return original_validate(root, marker_mode=marker_mode)

        live.validate_state_root = injected
        try:
            with self.assertRaisesRegex(
                    provision.ProvisionError, "^PUBLISHED_UNVERIFIED_PRESERVE$"):
                session.publish()
        finally:
            live.validate_state_root = original_validate

        self.assertTrue(self.final().is_dir())
        self.assertFalse(self.staging().exists())
        self.assertTrue((self.final() / live.MARKER_NAME).is_file())
        self.assertTrue((self.final() / live.REGISTRY_NAME).is_file())
        # The committed namespace is preserved rather than rolled back/replaced.
        runs = original_validate(self.final(), marker_mode="required")
        self.assertEqual(set(runs), {"actual"})
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_SESSION_CLOSED$"):
            session.publish()
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_FINAL_EXISTS$"):
            provision.begin()

    def test_valid_publish_moves_once_and_remains_readable(self):
        session = provision.begin()
        self.populate_fixture(session.workspace)
        sqlite_before = {
            path.relative_to(session.workspace).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(session.workspace.rglob("*.sqlite"))
        }
        result = session.publish()
        self.assertEqual(result, {
            "status": "PUBLISHED",
            "format": "GENIE_LOCAL_STATE_V1",
            "run_names": ["actual"],
            "scope": provision.PUBLICATION_SCOPE,
        })
        self.assertFalse(self.staging().exists())
        self.assertTrue(self.final().is_dir())
        self.assertEqual(
            json.loads((self.final() / live.MARKER_NAME).read_text(encoding="utf-8")),
            live.MARKER_VALUE)
        sqlite_after_publish = {
            path.relative_to(self.final()).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.final().rglob("*.sqlite"))
        }
        self.assertEqual(sqlite_after_publish, sqlite_before)

        runs = live.load_live_runs()
        host = status_tool.GenieStatusTools(runs)
        before_read = _tree_hash(self.final())
        status = host.call("get_run_status", {"run_name": "actual"})
        self.assertEqual(status.get("status"), "PASS")
        confirmed = [item for item in status.get("tasks", [])
                     if isinstance(item, dict)
                     and isinstance(item.get("fresh_sink"), dict)
                     and item["fresh_sink"].get("status") == "CONFIRMED"]
        self.assertTrue(confirmed)
        task = confirmed[0]["task_id"]
        accepted = host.call("get_task_result", {"run_name": "actual", "task_id": task})
        self.assertEqual(accepted.get("status"), "CONFIRMED")
        self.assertEqual(accepted.get("content_role"), "UNTRUSTED_ACCEPTED_TASK_DATA")
        self.assertEqual(_tree_hash(self.final()), before_read)

        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_FINAL_EXISTS$"):
            provision.begin()
        with self.assertRaisesRegex(
                provision.ProvisionError, "^PROVISION_SESSION_CLOSED$"):
            _ = session.workspace


if __name__ == "__main__":
    unittest.main()

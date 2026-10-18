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
from standalone_app import owner
from canonical_state_provisioner import provisioner_windows as provision


def _spec(run_id="standalone-owner-test"):
    return {
        "run_name": "actual",
        "policy": {
            "run_id": run_id,
            "max_tasks": 1,
            "max_model_calls": 1,
            "effect_scope": "owned-local-report-inbox",
        },
        "plans": [{
            "task_id": "task-1",
            "goal": "Produce one bounded test result",
            "input_sha256": hashlib.sha256(b"standalone-owner-input").hexdigest(),
            "max_attempts": 1,
        }],
    }


@unittest.skipUnless(os.name == "nt", "native Windows publication APIs required")
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

    def test_invalid_spec_does_not_acquire_staging(self):
        bad = _spec()
        bad["policy"]["max_tasks"] = True
        with self.assertRaisesRegex(owner.OwnerError, "^OWNER_INPUT_INVALID$"):
            owner.create_first_run(bad)
        self.assertFalse(self.app().exists())

    def test_partial_creation_failure_preserves_and_blocks_retry(self):
        original_write = owner._write_registry

        def fail_after_core_state(_workspace, _run_name, _run_id):
            raise owner.OwnerError("OWNER_CREATE_PRESERVE")

        owner._write_registry = fail_after_core_state
        try:
            with self.assertRaisesRegex(owner.OwnerError, "^OWNER_CREATE_PRESERVE$"):
                owner.create_first_run(_spec())
        finally:
            owner._write_registry = original_write

        self.assertTrue(self.staging().is_dir())
        self.assertTrue((self.staging() / owner.QUEUE_NAME).is_file())
        self.assertTrue((self.staging() / owner.OWNED_ROOT_NAME).is_dir())
        self.assertFalse(self.final().exists())
        with self.assertRaisesRegex(
                owner.OwnerError, "^PROVISION_STAGING_EXISTS_PRESERVE$"):
            owner.create_first_run(_spec("second-run"))

    def test_successful_create_status_and_single_step_do_not_invoke_model(self):
        created = owner.create_first_run(_spec())
        self.assertEqual(created["status"], "CREATED")
        self.assertEqual(created["run_name"], "actual")
        self.assertEqual(created["run_id"], "standalone-owner-test")
        self.assertEqual(created["task_count"], 1)
        self.assertIs(created["model_invoked"], False)
        self.assertEqual(created["publication"]["status"], "PUBLISHED")
        self.assertEqual(created["initial_status"]["status"], "PASS")
        self.assertTrue(self.final().is_dir())
        self.assertFalse(self.staging().exists())

        status_before = owner.status("actual")
        self.assertEqual(status_before.get("status"), "PASS")
        self.assertEqual(status_before["queue_history"]["reserved_model_calls"], 0)

        first = owner.advance("actual")
        self.assertEqual(first.get("action"), "INVOKE_WORKER", first)
        self.assertEqual(first["token"]["run_id"], "standalone-owner-test")
        self.assertEqual(first["request"]["task_id"], "task-1")
        self.assertEqual(first["request"]["attempt"], 1)

        status_after = owner.status("actual")
        self.assertEqual(status_after.get("status"), "PASS")
        self.assertEqual(status_after["queue_history"]["reserved_model_calls"], 1)
        task = status_after["tasks"][0]
        self.assertEqual(task["workflow"]["state"], "WAITING_WORKER")

        # A second advance reconciles the existing worker slot; it must not
        # reserve/invoke another model call.
        second = owner.advance("actual")
        self.assertEqual(second.get("action"), "RECONCILE_WORKER", second)
        self.assertIs(second.get("allow_new_invocation"), False)
        final_status = owner.status("actual")
        self.assertEqual(final_status["queue_history"]["reserved_model_calls"], 1)

        with self.assertRaisesRegex(owner.OwnerError, "^PROVISION_FINAL_EXISTS$"):
            owner.create_first_run(_spec("replacement-run"))

    def test_post_publish_binding_failure_preserves_final_and_blocks_recreate(self):
        original = live.load_live_runs
        calls = {"n": 0}

        def fail_after_publish():
            calls["n"] += 1
            raise live.LiveStateError("INJECTED_LIVE_BINDING_FAILURE")

        live.load_live_runs = fail_after_publish
        try:
            with self.assertRaisesRegex(
                    owner.OwnerError, "^OWNER_PUBLISHED_UNVERIFIED_PRESERVE$"):
                owner.create_first_run(_spec())
        finally:
            live.load_live_runs = original

        self.assertGreaterEqual(calls["n"], 1)
        self.assertTrue(self.final().is_dir())
        self.assertFalse(self.staging().exists())
        runs = original()
        self.assertEqual(runs["actual"]["run_id"], "standalone-owner-test")
        with self.assertRaisesRegex(owner.OwnerError, "^PROVISION_FINAL_EXISTS$"):
            owner.create_first_run(_spec("replacement-run"))

    def test_source_chain_rejects_controller_drift(self):
        original = owner.RUN_CONTROL_SHA256
        owner.RUN_CONTROL_SHA256 = "0" * 64
        try:
            with self.assertRaisesRegex(owner.OwnerError, "^OWNER_SOURCE_BINDING$"):
                owner.status("actual")
        finally:
            owner.RUN_CONTROL_SHA256 = original
        self.assertFalse(self.app().exists())


if __name__ == "__main__":
    unittest.main()

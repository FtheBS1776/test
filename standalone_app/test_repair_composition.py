"""R10 injected-state composition only; does not validate native Windows APIs."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from shared_interfaces.status_tool import _load_core
from standalone_app import execution_bridge as bridge, owner

COSTS = {role: {"max_micro_usd": 0, "quote_ref": "NO_MODEL_FIXTURE"}
         for role in ("author", "repair", "reviewer")}


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.queue = self.root / "queue.sqlite"
        self.material = "Supplied document: one bounded source statement."
        self.registry = {"test": {"queue": str(self.queue), "owned_root": str(self.work), "run_id": "composition-test"}}
        self.runner = _load_core().load_runner()
        self.runner.q.initialize(self.queue, {"run_id": "composition-test", "max_tasks": 1,
            "max_model_calls": 2, "effect_scope": "owned-local-report-inbox",
            "cost_policy": {"mode": "DISABLE_ALL", "limit_micro_usd": 0,
                            "authorization_ref": None, "quotes": COSTS}})
        self.runner.q.enqueue(self.queue, {"task_id": "task", "goal": "Analyze the supplied source",
            "input_sha256": hashlib.sha256(self.material.encode()).hexdigest(), "max_attempts": 2})
        self.workers, self.reviewers = [], []
        self.binding = patch.object(bridge.live, "load_live_runs", return_value=self.registry)
        self.binding.start()
        self.addCleanup(self.binding.stop)

    def worker(self, action):
        self.workers.append(action)
        return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED", "agent": "fake",
                "evidence": {"mode": "NO_MODEL_CALL"}, "text": "source-supported fixture result"}

    def reviewer(self, action):
        self.reviewers.append(action)
        return {"token": action["token"], "candidate_hash": action["candidate_sha256"],
                "decision": "ACCEPT", "reason": "FIXTURE_ONLY_NOT_REASONING_EVIDENCE"}

    def drive(self, **kwargs):
        return bridge.drive("test", kwargs.pop("worker", self.worker), self.reviewer,
                            costs=COSTS, materials=kwargs.pop("materials", {"task": self.material}), **kwargs)

    def test_exact_goal_materials_identity_and_saved_result_cross_one_driver(self):
        result = self.drive()
        self.assertEqual((result["action"], result["reason"]), ("STOP", "ALL_TASKS_COMPLETE"))
        self.assertEqual(self.workers[0]["request"]["goal"], "Analyze the supplied source")
        self.assertEqual(self.workers[0]["task_materials"]["text"], self.material)
        self.assertEqual(self.workers[0]["token"], self.reviewers[0]["token"])
        self.assertEqual(self.reviewers[0]["task_materials"]["content_role"], "UNTRUSTED_TASK_INPUT")
        self.assertEqual(owner.status("test")["tasks"][0]["fresh_sink"]["status"], "CONFIRMED")

    def test_material_mismatch_or_missing_coverage_stops_before_reservation(self):
        for materials in ({}, {"task": "altered"}):
            with self.subTest(materials=materials), self.assertRaisesRegex(bridge.BridgeError, "BRIDGE_MATERIAL_BINDING"):
                self.drive(materials=materials)
        self.assertEqual(self.workers, [])
        self.assertEqual(self.runner.q.status(self.queue)["reserved_model_calls"], 0)

    def test_binder_failure_does_not_fallback_or_invoke(self):
        with patch.object(bridge.live, "load_live_runs", side_effect=OSError("unavailable")):
            with self.assertRaisesRegex(bridge.BridgeError, "BRIDGE_LIVE_STATE_UNAVAILABLE"):
                self.drive()
        self.assertEqual(self.workers, [])

    def test_operator_stop_requires_no_model_and_prevents_next_dispatch(self):
        self.assertEqual(owner.stop("test")["reason"], "HOST_ENDED")
        result = self.drive()
        self.assertEqual((result["action"], result["reason"]), ("STOP", "HOST_ENDED"))
        self.assertEqual(self.workers, [])

    def test_unknown_hook_remains_charged_and_is_not_reassigned(self):
        def uncertain(action):
            self.workers.append(action)
            return {"token": action["token"], "outcome": "UNKNOWN", "agent": None,
                    "evidence": {"mode": "NO_MODEL_CALL"}, "text": None}
        self.assertEqual(self.drive(worker=uncertain)["action"], "UNKNOWN")
        self.assertEqual(self.drive()["action"], "RECONCILE_WORKER")
        self.assertEqual(len(self.workers), 1)
        self.assertEqual(self.runner.q.status(self.queue)["reserved_model_calls"], 1)

    def test_bad_source_pin_stops_before_binding_or_hook(self):
        with patch.object(bridge, "SESSION_DRIVER_SHA256", "0" * 64):
            with self.assertRaisesRegex(bridge.BridgeError, "BRIDGE_SOURCE_BINDING"):
                self.drive()
        self.assertEqual(self.workers, [])

    def test_disposable_snapshot_is_inspectable_without_replay_or_currentness_claim(self):
        self.drive()
        copied = self.root / "restored"
        copied.mkdir()
        shutil.copyfile(self.queue, copied / "queue.sqlite")
        shutil.copytree(self.work, copied / "work")
        reg = {"test": {"queue": str(copied / "queue.sqlite"),
                       "owned_root": str(copied / "work"), "run_id": "composition-test"}}
        with patch.object(bridge.live, "load_live_runs", return_value=reg):
            result = owner.status("test")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["tasks"][0]["fresh_sink"]["status"], "CONFIRMED")
        self.assertEqual(len(self.workers), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

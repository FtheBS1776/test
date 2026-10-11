import hashlib
from pathlib import Path
import tempfile
import unittest

import execution_bridge as bridge
import live_state_windows as live
import owner


def _spec(run_id="autodrive-test", max_calls=1, max_attempts=1):
    return {
        "run_name": "actual",
        "policy": {
            "run_id": run_id,
            "max_tasks": 1,
            "max_model_calls": max_calls,
            "effect_scope": "owned-local-report-inbox",
        },
        "plans": [{
            "task_id": "task-1",
            "goal": "Produce one bounded deterministic result",
            "input_sha256": hashlib.sha256((run_id + "-input").encode()).hexdigest(),
            "max_attempts": max_attempts,
        }],
    }


def _accepted_worker(text, calls):
    def worker(action):
        calls.append(action)
        return {
            "token": action["token"],
            "outcome": "OBSERVED_ACCEPTED",
            "agent": "deterministic-worker",
            "evidence": {"kind": "deterministic-test", "accepted": True},
            "text": text,
        }
    return worker


def _accept_reviewer(calls):
    def reviewer(action):
        calls.append(action)
        return {
            "token": action["token"],
            "candidate_hash": action["candidate_sha256"],
            "decision": "ACCEPT",
            "reason": "deterministic acceptance",
        }
    return reviewer


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.original_known = live._known_local_app_data
        live._known_local_app_data = lambda: self.base

    def tearDown(self):
        live._known_local_app_data = self.original_known
        self.temp.cleanup()

    def _result(self, task_id="task-1"):
        _control, facade, _runner = owner._load_control_chain()
        runs = live.load_live_runs()
        return facade.GenieStatusTools(runs).call(
            "get_task_result", {"run_name": "actual", "task_id": task_id})

    def test_happy_path_autodrives_to_stop_without_manual_advance(self):
        owner.create_first_run(_spec())
        worker_calls, review_calls = [], []
        text = "deterministic accepted standalone result"
        terminal = bridge.drive(
            "actual", _accepted_worker(text, worker_calls),
            _accept_reviewer(review_calls), max_actions=16)

        self.assertEqual(terminal.get("action"), "STOP", terminal)
        self.assertEqual(terminal.get("reason"), "ALL_TASKS_COMPLETE", terminal)
        self.assertEqual(terminal["counts"]["worker_hooks"], 1)
        self.assertEqual(terminal["counts"]["reviewer_hooks"], 1)
        self.assertEqual(len(worker_calls), 1)
        self.assertEqual(len(review_calls), 1)

        status = owner.status("actual")
        self.assertEqual(status.get("status"), "PASS")
        self.assertEqual(status["queue_history"]["state"], "STOPPED")
        self.assertEqual(status["queue_history"]["stop_reason"], "ALL_TASKS_COMPLETE")
        self.assertEqual(status["queue_history"]["reserved_model_calls"], 1)
        self.assertEqual(status["tasks"][0]["fresh_sink"]["status"], "CONFIRMED")

        result = self._result()
        self.assertEqual(result.get("status"), "CONFIRMED")
        self.assertEqual(result.get("result_text"), text)
        self.assertEqual(result.get("content_role"), "UNTRUSTED_ACCEPTED_TASK_DATA")

    def test_action_limit_loses_session_review_eligibility_and_reconciles(self):
        owner.create_first_run(_spec(run_id="action-limit-review"))
        worker_calls, review_calls = [], []

        # One action permits worker observation/submission but ends the driver
        # before the next REVIEW_CANDIDATE advance. The in-memory eligibility
        # record must not be reconstructed by a later process/drive.
        first = bridge.drive(
            "actual", _accepted_worker("submitted before action limit", worker_calls),
            _accept_reviewer(review_calls), max_actions=1)
        self.assertEqual(first.get("action"), "HOLD", first)
        self.assertEqual(first.get("reason"), "DRIVER_ACTION_LIMIT", first)
        self.assertIs(first.get("allow_new_invocation"), False)
        self.assertEqual(first["counts"]["worker_hooks"], 1)
        self.assertEqual(first["counts"]["reviewer_hooks"], 0)
        self.assertEqual(len(worker_calls), 1)
        self.assertEqual(review_calls, [])
        status = owner.status("actual")
        self.assertEqual(status["queue_history"]["reserved_model_calls"], 1)
        self.assertEqual(status["tasks"][0]["workflow"]["state"], "REVIEW")

        def forbidden_worker(_action):
            raise AssertionError("review continuity must not relaunch worker")

        def forbidden_reviewer(_action):
            raise AssertionError("new drive must not reconstruct reviewer eligibility")

        second = bridge.drive(
            "actual", forbidden_worker, forbidden_reviewer, max_actions=8)
        self.assertEqual(second.get("action"), "RECONCILE_REVIEW", second)
        self.assertEqual(second.get("reason"), "NO_SESSION_SUBMISSION", second)
        self.assertIs(second.get("allow_new_invocation"), False)
        self.assertEqual(second["counts"]["worker_hooks"], 0)
        self.assertEqual(second["counts"]["reviewer_hooks"], 0)
        self.assertEqual(owner.status("actual")["queue_history"]["reserved_model_calls"], 1)

    def test_uncertain_worker_observation_never_retries(self):
        owner.create_first_run(_spec(run_id="unknown-observation"))
        calls = []

        def uncertain(action):
            calls.append(action)
            return {
                "token": action["token"],
                "outcome": "UNKNOWN",
                "agent": None,
                "evidence": {"kind": "deterministic-test", "observed": "unknown"},
                "text": None,
            }

        terminal = bridge.drive("actual", uncertain, _accept_reviewer([]), max_actions=8)
        self.assertEqual(terminal.get("action"), "UNKNOWN", terminal)
        self.assertIs(terminal.get("allow_new_invocation"), False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(terminal["counts"]["worker_hooks"], 1)

        status = owner.status("actual")
        self.assertEqual(status["queue_history"]["reserved_model_calls"], 1)
        self.assertEqual(status["tasks"][0]["workflow"]["state"], "WAITING_WORKER")
        self.assertEqual(status["tasks"][0]["journal"]["host_outcome"], "UNKNOWN")
        self.assertGreaterEqual(status["tasks"][0]["journal"]["observation_count"], 1)

        def forbidden(_action):
            raise AssertionError("uncertain invocation must not be retried")

        second = bridge.drive("actual", forbidden, _accept_reviewer([]), max_actions=8)
        self.assertEqual(second.get("action"), "RECONCILE_WORKER", second)
        self.assertIs(second.get("allow_new_invocation"), False)
        self.assertEqual(second["counts"]["worker_hooks"], 0)
        self.assertEqual(owner.status("actual")["queue_history"]["reserved_model_calls"], 1)

    def test_worker_exception_is_unknown_and_later_drive_does_not_reinvoke(self):
        owner.create_first_run(_spec(run_id="worker-exception"))
        calls = []

        def exploding(action):
            calls.append(action)
            raise RuntimeError("provider may have accepted request")

        terminal = bridge.drive("actual", exploding, _accept_reviewer([]), max_actions=8)
        self.assertEqual(terminal.get("action"), "UNKNOWN", terminal)
        self.assertIs(terminal.get("allow_new_invocation"), False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(owner.status("actual")["queue_history"]["reserved_model_calls"], 1)

        def forbidden(_action):
            raise AssertionError("exceptional invocation must not be retried")

        second = bridge.drive("actual", forbidden, _accept_reviewer([]), max_actions=8)
        self.assertEqual(second.get("action"), "RECONCILE_WORKER", second)
        self.assertIs(second.get("allow_new_invocation"), False)
        self.assertEqual(second["counts"]["worker_hooks"], 0)
        self.assertEqual(owner.status("actual")["queue_history"]["reserved_model_calls"], 1)

    def test_mismatched_worker_token_is_unknown_and_not_reinvoked(self):
        owner.create_first_run(_spec(run_id="token-mismatch"))
        calls = []

        def wrong_token(action):
            calls.append(action)
            token = dict(action["token"])
            token["call_id"] = "0" * 64
            return {
                "token": token,
                "outcome": "OBSERVED_ACCEPTED",
                "agent": "deterministic-worker",
                "evidence": {"kind": "deterministic-test"},
                "text": "must not be accepted",
            }

        terminal = bridge.drive("actual", wrong_token, _accept_reviewer([]), max_actions=8)
        self.assertEqual(terminal.get("action"), "UNKNOWN", terminal)
        self.assertIs(terminal.get("allow_new_invocation"), False)
        self.assertEqual(len(calls), 1)

        def forbidden(_action):
            raise AssertionError("mismatched return must not grant retry")

        second = bridge.drive("actual", forbidden, _accept_reviewer([]), max_actions=8)
        self.assertEqual(second.get("action"), "RECONCILE_WORKER", second)
        self.assertEqual(second["counts"]["worker_hooks"], 0)
        self.assertEqual(owner.status("actual")["queue_history"]["reserved_model_calls"], 1)

    def test_existing_repair_budget_autodrives_two_attempts_only(self):
        owner.create_first_run(_spec(
            run_id="repair-autodrive", max_calls=2, max_attempts=2))
        worker_calls, review_calls = [], []

        def worker(action):
            worker_calls.append(action)
            attempt = action["request"]["attempt"]
            return {
                "token": action["token"],
                "outcome": "OBSERVED_ACCEPTED",
                "agent": "deterministic-worker",
                "evidence": {"kind": "deterministic-test", "attempt": attempt},
                "text": f"candidate attempt {attempt}",
            }

        def reviewer(action):
            review_calls.append(action)
            attempt = action["token"]["attempt"]
            return {
                "token": action["token"],
                "candidate_hash": action["candidate_sha256"],
                "decision": "REPAIR" if attempt == 1 else "ACCEPT",
                "reason": "repair once" if attempt == 1 else "accept second attempt",
            }

        terminal = bridge.drive("actual", worker, reviewer, max_actions=24)
        self.assertEqual(terminal.get("action"), "STOP", terminal)
        self.assertEqual(terminal.get("reason"), "ALL_TASKS_COMPLETE", terminal)
        self.assertEqual(terminal["counts"]["worker_hooks"], 2)
        self.assertEqual(terminal["counts"]["reviewer_hooks"], 2)
        self.assertEqual([a["request"]["attempt"] for a in worker_calls], [1, 2])
        self.assertEqual([a["token"]["attempt"] for a in review_calls], [1, 2])
        status = owner.status("actual")
        self.assertEqual(status["queue_history"]["reserved_model_calls"], 2)
        self.assertEqual(status["tasks"][0]["fresh_sink"]["status"], "CONFIRMED")
        self.assertEqual(self._result()["result_text"], "candidate attempt 2")

    def test_driver_source_drift_fails_before_worker(self):
        calls = []
        original = bridge.SESSION_DRIVER_SHA256
        bridge.SESSION_DRIVER_SHA256 = "0" * 64
        try:
            with self.assertRaisesRegex(bridge.BridgeError, "^BRIDGE_SOURCE_BINDING$"):
                bridge.drive("actual", lambda action: calls.append(action), lambda action: None)
        finally:
            bridge.SESSION_DRIVER_SHA256 = original
        self.assertEqual(calls, [])
        self.assertFalse((self.base / live.APP_DIR).exists())


if __name__ == "__main__":
    unittest.main()

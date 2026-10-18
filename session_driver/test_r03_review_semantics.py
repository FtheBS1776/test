"""R03 composed negative-path check; deterministic hooks only, no model calls."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from contextlib import closing

from phase2c_finite_autonomous_pilot.run_bounded_batch import PilotHooks
from phase2b2s_attested_live_pilot.attested_worker import EXPECTED_RESULT
from shared_interfaces import session_driver as driver
from shared_interfaces.session_driver import drive_run
from shared_interfaces.status_tool import _load_core


COSTS = {role: {"max_micro_usd": 0, "quote_ref": "DETERMINISTIC_NO_MODEL_FIXTURE"}
         for role in ("author", "repair", "reviewer")}


class R03ReviewSemanticsTests(unittest.TestCase):
    def _setup(self, root, max_attempts=1, max_calls=1):
        queue = root / "queue.sqlite"
        work = root / "work"
        work.mkdir()
        run_id = "r03-review-semantics-test"
        registry = {"test": {"queue": str(queue), "run_id": run_id,
                              "owned_root": str(work)}}
        runner = _load_core().load_runner()
        runner.q.initialize(queue, {"run_id": run_id, "max_tasks": 1,
            "max_model_calls": max_calls, "effect_scope": "owned-local-report-inbox", "cost_policy": {"mode": "DISABLE_ALL",
            "limit_micro_usd": 0, "authorization_ref": None, "quotes": COSTS}})
        runner.q.enqueue(queue, {"task_id": "invalid-candidate",
            "goal": "exercise bounded review rejection", "input_sha256": "a" * 64,
            "max_attempts": max_attempts})
        return queue, work, run_id, registry, runner

    def _drive(self, registry, candidates):
        calls = []
        hooks = PilotHooks(Path("unused"), Path("unused"))

        def worker(action):
            calls.append(action)
            return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED",
                "agent": "r03-no-model-worker", "evidence": {"mode": "NO_MODEL_CALL"},
                "text": candidates[len(calls) - 1]}

        result = drive_run(registry, "test", worker, hooks.reviewer, max_actions=8, costs=COSTS)
        return result, calls, hooks

    def test_real_reviewer_invalid_candidates_hold_without_acceptance_or_new_call(self):
        valid = json.dumps(EXPECTED_RESULT, sort_keys=True, separators=(",", ":"))
        cases = {
            "wrong_schema": '{"schema":"wrong"}',
            "wrong_boolean_value": valid.replace("false", "true"),
            "integer_for_boolean": valid.replace("false", "0"),
            "float_for_boolean": valid.replace("false", "0.0"),
            "duplicate_conflicting_key": valid.replace('"authority_request":false',
                '"authority_request":true,"authority_request":false'),
            "nonfinite": valid.replace("false", "NaN"),
            "malformed_json": "{not-json}",
        }
        for name, candidate in cases.items():
            with self.subTest(candidate=name), tempfile.TemporaryDirectory() as temporary:
                queue, work, run_id, registry, runner = self._setup(Path(temporary))
                result, calls, hooks = self._drive(registry, [candidate])
                self.assertEqual((result["action"], result["reason"]), ("HOLD", "ATTEMPT_BOUND"))
                self.assertEqual((len(calls), hooks.reviewer_calls), (1, 1))
                self.assertEqual(result["counts"]["worker_hooks"], 1)
                self.assertEqual(result["counts"]["reviewer_hooks"], 1)
                queue_status = runner.q.status(queue)
                self.assertEqual(queue_status["reserved_model_calls"], 1)
                self.assertEqual(queue_status["entries"][0]["state"], "HOLD")
                _, ledger, sink = runner.paths(work, run_id, "invalid-candidate")
                with closing(sqlite3.connect(ledger)) as db:
                    self.assertEqual(db.execute("SELECT state FROM task").fetchone()[0], "HOLD")
                    review = json.loads(db.execute("SELECT review FROM attempts").fetchone()[0])
                    self.assertEqual(review["decision"], "REPAIR")
                    self.assertEqual(review["candidate_sha256"], hashlib.sha256(candidate.encode()).hexdigest())
                    self.assertEqual(review["attempt"], calls[0]["token"]["attempt"])
                with closing(sqlite3.connect(sink)) as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM applications").fetchone()[0], 0)

    def test_real_reviewer_accepts_valid_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue, _, _, registry, runner = self._setup(Path(temporary))
            result, calls, hooks = self._drive(registry, [json.dumps(EXPECTED_RESULT)])
            self.assertEqual((result["action"], result["reason"]), ("STOP", "ALL_TASKS_COMPLETE"))
            self.assertEqual((len(calls), hooks.reviewer_calls), (1, 1))
            self.assertEqual(runner.q.status(queue)["entries"][0]["state"], "COMPLETE")

    def test_real_reviewer_repair_uses_only_existing_attempt_and_call_permission(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue, _, _, registry, runner = self._setup(Path(temporary), max_attempts=2, max_calls=2)
            result, calls, hooks = self._drive(registry, ['{"schema":"wrong"}', json.dumps(EXPECTED_RESULT)])
            self.assertEqual((result["action"], result["reason"]), ("STOP", "ALL_TASKS_COMPLETE"))
            self.assertEqual((len(calls), hooks.reviewer_calls), (2, 2))
            self.assertEqual([a["token"]["attempt"] for a in calls], [1, 2])
            self.assertNotEqual(calls[0]["token"]["call_id"], calls[1]["token"]["call_id"])
            self.assertEqual(calls[1]["request"]["feedback"], "BOUNDED_SCHEMA_MISMATCH")
            self.assertEqual(runner.q.status(queue)["reserved_model_calls"], 2)

    def test_real_reviewer_repair_cannot_bypass_call_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue, _, _, registry, runner = self._setup(Path(temporary), max_attempts=2, max_calls=1)
            result, calls, hooks = self._drive(registry, ['{"schema":"wrong"}'])
            self.assertEqual((result["action"], result["reason"]), ("STOP", "CALL_BUDGET_EXHAUSTED"))
            self.assertFalse(result["allow_new_invocation"])
            self.assertEqual((len(calls), hooks.reviewer_calls), (1, 1))
            self.assertEqual(runner.q.status(queue)["reserved_model_calls"], 1)

    def test_review_token_or_hash_mismatch_is_unknown_without_new_call(self):
        for binding in ("token", "candidate_hash", "decision"):
            with self.subTest(binding=binding), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                queue, work, run_id, registry, runner = self._setup(root)
                calls = {"worker": 0, "reviewer": 0}

                def worker(action):
                    calls["worker"] += 1
                    return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED",
                        "agent": "r03-no-model-worker", "evidence": {"mode": "NO_MODEL_CALL"},
                        "text": '{"schema":"wrong"}'}

                def reviewer(action):
                    calls["reviewer"] += 1
                    token = dict(action["token"])
                    candidate_hash = action["candidate_sha256"]
                    if binding == "token":
                        token["call_id"] = "f" * 64
                    elif binding == "candidate_hash":
                        candidate_hash = "0" * 64
                    return {"token": token, "candidate_hash": candidate_hash,
                        "decision": "REJECT" if binding == "decision" else "REPAIR",
                        "reason": "BOUNDED_SCHEMA_MISMATCH"}

                result = drive_run(registry, "test", worker, reviewer, max_actions=8, costs=COSTS)

                self.assertEqual(result["action"], "UNKNOWN")
                self.assertTrue(result["preserve"])
                self.assertFalse(result["allow_new_invocation"])
                self.assertEqual(calls, {"worker": 1, "reviewer": 1})
                self.assertEqual(runner.q.status(queue)["reserved_model_calls"], 1)
                _, ledger, _ = runner.paths(work, run_id, "invalid-candidate")
                with closing(sqlite3.connect(ledger)) as db:
                    self.assertEqual(db.execute("SELECT state FROM task").fetchone()[0], "REVIEW")
                    self.assertIsNone(db.execute("SELECT review FROM attempts").fetchone()[0])

    def test_lost_review_ack_keeps_charge_and_stops_without_repair_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue, work, run_id, registry, runner = self._setup(Path(temporary), max_attempts=2, max_calls=2)
            events = driver._load_events()
            original = events.GenieRunEvents.call
            operations = []

            def lost_ack(host, name, arguments):
                result = original(host, name, arguments)
                operations.append(arguments["operation"])
                if arguments["operation"] == "review":
                    raise OSError("injected lost review acknowledgement")
                return result

            with patch.object(driver, "_load_events", return_value=events), patch.object(
                    events.GenieRunEvents, "call", lost_ack):
                result, calls, hooks = self._drive(registry, ['{"schema":"wrong"}'])
            self.assertEqual(result["action"], "UNKNOWN")
            self.assertTrue(result["preserve"])
            self.assertFalse(result["allow_new_invocation"])
            self.assertEqual((len(calls), hooks.reviewer_calls), (1, 1))
            self.assertEqual(operations, ["observe", "submit", "review"])
            self.assertEqual(runner.q.status(queue)["reserved_model_calls"], 1)
            _, ledger, _ = runner.paths(work, run_id, "invalid-candidate")
            with closing(sqlite3.connect(ledger)) as db:
                self.assertEqual(db.execute("SELECT state FROM task").fetchone()[0], "REPAIR_READY")
                self.assertEqual(db.execute("SELECT count(*) FROM attempts").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

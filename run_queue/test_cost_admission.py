"""R07 real queue/driver admission; simulated bounds, zero provider calls."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from run_queue import run_policy as q
from shared_interfaces import session_driver as driver
from shared_interfaces.run_control import GenieRunController


class CostAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def setup_run(self, mode=None):
        queue = self.root / "queue.sqlite"
        work = self.root / "work"
        work.mkdir()
        policy = {"run_id": "cost-test", "max_tasks": 1, "max_model_calls": 2,
                  "effect_scope": "owned-local-report-inbox"}
        quotes = {role: {"max_micro_usd": 0, "quote_ref": "FIXTURE"} for role in q.COST_ROLES}
        quotes["author"] = {"max_micro_usd": 0, "quote_ref": "NO_MODEL_FIXTURE"}
        if mode is not None:
            quotes.update({role: {"max_micro_usd": 80, "quote_ref": "SIMULATED_RATE"}
                           for role in ("author", "tool", "service")})
            quotes["reviewer"] = {"max_micro_usd": 200, "quote_ref": "SIMULATED_RATE"}
        policy["cost_policy"] = {**(mode or q.COST_DEFAULT), "quotes": quotes}
        q.initialize(queue, policy)
        q.enqueue(queue, {"task_id": "cost-task", "goal": "simulated cost checks",
                          "input_sha256": "a" * 64, "max_attempts": 2})
        reg = {"test": {"queue": str(queue), "run_id": "cost-test", "owned_root": str(work)}}
        return queue, reg

    def token(self, reg):
        return GenieRunController(reg).call("advance_run", {"run_name": "test"})["token"]

    def test_default_unknown_author_cost_makes_zero_hook_calls(self):
        queue, reg = self.setup_run()
        calls = []
        result = driver.drive_run(reg, "test", calls.append, calls.append)
        self.assertEqual(result["reason"], "COST_BOUND_UNKNOWN_OR_INVALID")
        self.assertEqual(calls, [])
        self.assertEqual(q.status(queue)["cost_admission"]["reserved_micro_usd"], 0)

    def test_unknown_reviewer_cost_cannot_enter_reviewer(self):
        queue, reg = self.setup_run()
        calls = []
        def worker(action):
            return {"token": action["token"], "outcome": "OBSERVED_ACCEPTED", "agent": "fake",
                    "text": "untrusted candidate", "evidence": {"mode": "NO_MODEL_CALL"}}
        result = driver.drive_run(reg, "test", worker, calls.append,
            costs={"author": {"max_micro_usd": 0, "quote_ref": "NO_MODEL_FIXTURE"}})
        self.assertEqual(result["reason"], "COST_BOUND_UNKNOWN_OR_INVALID")
        self.assertEqual(result["counts"]["worker_hooks"], 1)
        self.assertEqual(calls, [])

    def test_disabled_positive_cost_does_not_dispatch(self):
        _, reg = self.setup_run()
        calls = []
        result = driver.drive_run(reg, "test", calls.append, calls.append,
            costs={"author": {"max_micro_usd": 1, "quote_ref": "SIMULATED_RATE"}})
        self.assertEqual(result["reason"], "COST_CALLS_DISABLED")
        self.assertEqual(calls, [])

    def test_limited_concurrent_roles_share_one_durable_budget(self):
        queue, reg = self.setup_run({"mode": "ENABLE_LIMITED", "limit_micro_usd": 100,
                                    "authorization_ref": "SIMULATION_ONLY"})
        token = self.token(reg)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda role: q.admit_action(queue, token, role, role, 80,
                "SIMULATED_RATE"), ["tool", "service"]))
        self.assertEqual(sum(r["action"] == "ADMIT_ONCE" for r in results), 1)
        self.assertEqual(sum(r.get("reason") == "COST_BUDGET_EXHAUSTED" for r in results), 1)
        self.assertEqual(q.status(queue)["cost_admission"]["reserved_micro_usd"], 80)
        # Fresh reads of the same owned queue retain charges; no reset API.
        with closing(sqlite3.connect(queue)) as db:
            self.assertEqual(db.execute("SELECT sum(max_micro_usd) FROM cost_actions").fetchone()[0], 80)

    def test_replay_alias_and_wrong_token_grant_no_new_admission(self):
        queue, reg = self.setup_run()
        token = self.token(reg)
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 0, "NO_MODEL_FIXTURE")["action"], "ADMIT_ONCE")
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 0, "NO_MODEL_FIXTURE")["action"], "RECONCILE_COST_ACTION")
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 0, "changed")["reason"], "COST_ACTION_ALIAS")
        self.assertEqual(q.admit_action(queue, {**token, "call_id": "f" * 64}, "reviewer", "review", 0, "FIXTURE")["reason"], "COST_TOKEN_BINDING")
        for amount in (None, True, -1, 1.0):
            self.assertEqual(q.admit_action(queue, token, "runner", "runner", amount, "FIXTURE")["action"], "HOLD")

    def test_unknown_hook_outcome_keeps_reserved_money_and_stable_call(self):
        queue, reg = self.setup_run({"mode": "ENABLE_LIMITED", "limit_micro_usd": 100,
                                    "authorization_ref": "SIMULATION_ONLY"})
        calls = []
        def lost(action):
            calls.append(action)
            raise OSError("simulated lost result")
        costs = {"author": {"max_micro_usd": 80, "quote_ref": "SIMULATED_RATE"}}
        first = driver.drive_run(reg, "test", lost, lost, costs=costs)
        self.assertEqual(first["action"], "UNKNOWN")
        self.assertFalse(first["allow_new_invocation"])
        self.assertEqual(q.status(queue)["cost_admission"]["reserved_micro_usd"], 80)
        second = driver.drive_run(reg, "test", lost, lost, costs=costs)
        self.assertEqual(second["action"], "RECONCILE_WORKER")
        self.assertEqual(len(calls), 1)
        self.assertEqual(q.status(queue)["reserved_model_calls"], 1)

    def test_enable_all_still_requires_known_bound_and_explicit_policy(self):
        queue, reg = self.setup_run({"mode": "ENABLE_ALL", "limit_micro_usd": None,
                                    "authorization_ref": "SIMULATION_ONLY"})
        token = self.token(reg)
        self.assertEqual(q.admit_action(queue, token, "reviewer", "review", None, "UNKNOWN")["action"], "HOLD")
        self.assertEqual(q.admit_action(queue, token, "reviewer", "review", 200, "SIMULATED_RATE")["action"], "ADMIT_ONCE")

    def test_legacy_cost_schema_is_preserved_and_denied(self):
        queue, reg = self.setup_run()
        token = self.token(reg)
        with closing(sqlite3.connect(queue)) as db:
            db.execute("DROP TABLE cost_actions")
            db.commit()
        before = hashlib.sha256(queue.read_bytes()).hexdigest()
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 0, "NO_MODEL_FIXTURE")["reason"], "COST_SCHEMA_UNAVAILABLE")
        self.assertEqual(hashlib.sha256(queue.read_bytes()).hexdigest(), before)

    def test_caller_cannot_substitute_a_zero_cost_quote_or_reinitialize_balance(self):
        queue, reg = self.setup_run({"mode": "ENABLE_LIMITED", "limit_micro_usd": 100,
                                    "authorization_ref": "SIMULATION_ONLY"})
        token = self.token(reg)
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 0, "SIMULATED_RATE")["reason"], "COST_QUOTE_NOT_APPROVED")
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 80, "SIMULATED_RATE")["action"], "ADMIT_ONCE")
        with self.assertRaises(FileExistsError):
            q.initialize(queue, {"run_id": "replacement", "max_tasks": 1, "max_model_calls": 1,
                                 "effect_scope": "owned-local-report-inbox"})
        self.assertEqual(q.status(queue)["cost_admission"]["reserved_micro_usd"], 80)

    def test_no_approved_zero_quote_means_no_free_call(self):
        queue, reg = self.setup_run()
        token = self.token(reg)
        self.assertEqual(q.admit_action(queue, token, "author", "worker", 0, "IMPLICITLY_FREE")["reason"], "COST_QUOTE_NOT_APPROVED")

    def test_unbounded_live_adapters_stop_before_process_or_ledger_entry(self):
        from shared_interfaces import live_codex_worker as live
        from phase2b2s_attested_live_pilot import attested_worker as attested
        with patch("subprocess.Popen", side_effect=AssertionError("must not spawn")):
            replies = [live.run_once(token={}, ledger_path=self.root / "ledger", executable="unused",
                version="unused", codex_home=self.root, working_directory=self.root),
                attested.run_once(token={}, artifact_directory=self.root, codex_home=self.root,
                    working_directory=self.root, ledger_path=self.root / "ledger", evidence_directory=self.root)]
        for result in replies:
            self.assertEqual(result["reason"], "LIVE_COST_BOUND_UNAVAILABLE")
            self.assertFalse(result["process_entry"])
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

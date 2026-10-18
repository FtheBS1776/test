"""Adversarial Phase 2C wrapper checks. NO MODEL CALL."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phase2c_finite_autonomous_pilot import provision_synthetic as provision
from phase2c_finite_autonomous_pilot import run_bounded_batch as batch


def token(task_id, fill):
    return {"run_id": "genie-phase2c-finite-run-20261016", "task_id": task_id,
            "input_sha256": fill * 64, "attempt": 1, "slot_id": (fill.upper()) * 64,
            "call_id": ("c" if fill == "a" else "d") * 64}


class Phase2CTests(unittest.TestCase):
    def test_plans_are_two_exact_single_attempt_task_bindings(self):
        plans = provision.plans()
        self.assertEqual([plan["task_id"] for plan in plans], list(batch.TASK_IDS))
        self.assertEqual([plan["max_attempts"] for plan in plans], [1, 1])
        expected = [hashlib.sha256((provision.TRIAL / f"INPUT_{n}.md").read_bytes()).hexdigest()
                    for n in (1, 2)]
        self.assertEqual([plan["input_sha256"] for plan in plans], expected)

    def test_each_worker_gets_distinct_ledger_and_exact_task_binding(self):
        accepted = []
        def fake_run_once(**kwargs):
            accepted.append(kwargs)
            return {"status": "OBSERVED_ACCEPTED", "logical_operation_id":
                    hashlib.sha256(json.dumps(kwargs["token"], sort_keys=True).encode()).hexdigest(),
                    "result_text": '{"authority_request":false,"marker":"LOCAL_ATTESTED_WORKER_OK_20261016","visible_tool_or_mcp_names":[]}',
                    "evidence": {"tool_activity_count": 0}}
        with tempfile.TemporaryDirectory() as temporary, patch.object(
                batch, "TRIAL", Path(temporary)), patch(
                "phase2b2s_attested_live_pilot.attested_worker.run_once", fake_run_once):
            hooks = batch.PilotHooks(Path("artifact"), Path("codex-home"))
            replies = []
            for task_id, fill in zip(batch.TASK_IDS, ("a", "b")):
                value = token(task_id, fill)
                replies.append(hooks.worker({"action": "INVOKE_WORKER", "token": value,
                    "request": {"task_id": task_id}}))
            self.assertEqual([reply["outcome"] for reply in replies],
                             ["OBSERVED_ACCEPTED", "OBSERVED_ACCEPTED"])
            self.assertNotEqual(accepted[0]["ledger_path"], accepted[1]["ledger_path"])
            self.assertEqual([call["token"]["task_id"] for call in accepted],
                             list(batch.TASK_IDS))
            self.assertEqual(list(hooks.live_results), list(batch.TASK_IDS))

    def test_worker_bound_and_unknown_are_fail_closed(self):
        def unknown(**kwargs):
            return {"status": "UNKNOWN", "logical_operation_id": "e" * 64,
                    "evidence": {"process_entry": True}}
        with tempfile.TemporaryDirectory() as temporary, patch.object(
                batch, "TRIAL", Path(temporary)), patch(
                "phase2b2s_attested_live_pilot.attested_worker.run_once", unknown):
            hooks = batch.PilotHooks(Path("artifact"), Path("codex-home"))
            reply = hooks.worker({"token": token(batch.TASK_IDS[0], "a")})
            self.assertEqual(reply["outcome"], "UNKNOWN")
            self.assertIsNone(reply["text"])
            self.assertTrue(reply["evidence"]["preserve"])
            self.assertFalse(reply["evidence"]["allow_new_invocation"])
            self.assertEqual(reply["evidence"]["retry_count"], 0)

    def test_reviewer_repairs_bound_schema_mismatch_but_rejects_hash_mismatch(self):
        from phase2b2s_attested_live_pilot.attested_worker import EXPECTED_RESULT
        hooks = batch.PilotHooks(Path("artifact"), Path("codex-home"))
        candidate = json.dumps(EXPECTED_RESULT, sort_keys=True, separators=(",", ":"))
        value = token(batch.TASK_IDS[0], "a")
        accepted = hooks.reviewer({"token": value, "candidate": candidate,
            "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest()})
        self.assertEqual(accepted["decision"], "ACCEPT")
        mutated = candidate.replace("false", "true")
        repair = hooks.reviewer({"token": value, "candidate": mutated,
            "candidate_sha256": hashlib.sha256(mutated.encode()).hexdigest()})
        self.assertEqual(repair["decision"], "REPAIR")
        self.assertEqual(repair["reason"], "BOUNDED_SCHEMA_MISMATCH")
        stale = hooks.reviewer({"token": value, "candidate": candidate,
            "candidate_sha256": "0" * 64})
        self.assertEqual(stale["decision"], "REJECT")
        self.assertEqual(stale["reason"], "CANDIDATE_HASH_MISMATCH")


if __name__ == "__main__":
    unittest.main(verbosity=2)

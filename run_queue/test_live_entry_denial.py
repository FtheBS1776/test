"""No-model regressions for exported CLI launchers with unknown total cost."""
from contextlib import ExitStack, closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from shared_interfaces import live_codex_worker as original
from phase2b2m_alpha_live_pilot import alpha_exec_worker as alpha
from phase2b2o_alpha_recovery_live import recovered_worker as recovery
from phase2b2s_attested_live_pilot import attested_worker as attested


TOKEN = {"run_id": "run", "task_id": "task", "input_sha256": "1" * 64,
         "attempt": 1, "slot_id": "2" * 64, "call_id": "3" * 64}
SUBJECTS = (original, alpha, recovery, attested)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class LiveEntryDenialTests(unittest.TestCase):
    def call(self, subject, root):
        args = dict(token=TOKEN, ledger_path=root / "evidence/operation.sqlite",
                    codex_home=root / "no-auth", working_directory=root / "scratch")
        if subject is attested:
            args.update(artifact_directory=root / "artifact",
                        evidence_directory=root / "evidence")
        else:
            args.update(executable=root / "fake-executable.txt", version="fake-only")
            if subject is recovery:
                args["evidence_directory"] = root / "evidence"
        return subject.run_once(**args)

    def prepare(self, root):
        (root / "scratch").mkdir()
        (root / "evidence").mkdir()
        (root / "fake-executable.txt").write_text("Only hashed; never executed.\n")

    def test_unknown_cost_never_claims_or_reaches_native_entry(self):
        for subject in SUBJECTS:
            with self.subTest(subject=subject.__name__), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                self.prepare(root)
                before = snapshot(root)
                observed_claims = []

                def stop_before_process(*args, **kwargs):
                    ledger = root / "evidence/operation.sqlite"
                    with closing(sqlite3.connect(ledger)) as db:
                        observed_claims.extend(db.execute(
                            "SELECT state,preserve,allow_new_invocation FROM operation"))
                    raise RuntimeError("FAKE_STOP_BEFORE_OS_PROCESS")

                with mock.patch.object(subject, "WindowsJob") as job, mock.patch.object(
                        subject.subprocess, "Popen", side_effect=stop_before_process) as popen:
                    job.return_value.accounting.return_value = {
                        "active_processes": 0, "total_processes": 0}
                    result = self.call(subject, root)
                self.assertEqual(observed_claims, [], "unadmitted operation claim")
                job.assert_not_called()
                popen.assert_not_called()
                self.assertEqual(snapshot(root), before)
                self.assertEqual(result["status"], "REJECT")
                self.assertEqual(result["reason"], "LIVE_COST_BOUND_UNAVAILABLE")
                self.assertIs(result["process_entry"], False)
                self.assertIs(result["preserve"], True)
                self.assertIs(result["allow_new_invocation"], False)

    def test_denial_preserves_existing_uncertainty_and_evidence(self):
        for subject in SUBJECTS:
            with self.subTest(subject=subject.__name__), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                self.prepare(root)
                ledger = original.OperationLedger(root / "evidence/operation.sqlite")
                self.assertTrue(ledger.claim("prior-uncertain-operation", {"token": TOKEN}))
                (root / "evidence/preserved.bin").write_bytes(b"uncertain historical evidence\x00")
                before = snapshot(root)
                with ExitStack() as stack:
                    guarded = [stack.enter_context(mock.patch.object(subject, name,
                               side_effect=AssertionError(name + " entered")))
                               for name in ("OperationLedger", "WindowsJob")]
                    guarded.append(stack.enter_context(mock.patch.object(
                        subject.subprocess, "Popen", side_effect=AssertionError("Popen entered"))))
                    result = self.call(subject, root)
                for boundary in guarded:
                    boundary.assert_not_called()
                self.assertEqual(snapshot(root), before)
                self.assertEqual(result["reason"], "LIVE_COST_BOUND_UNAVAILABLE")
                self.assertIs(result["allow_new_invocation"], False)


if __name__ == "__main__":
    unittest.main()

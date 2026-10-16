import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from phase2b2r_exact_codex_preflight import exact_codex_preflight as subject


class ExactCodexPreflightTests(unittest.TestCase):
    def test_artifact_checksum_is_independently_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = b"exact-codex"
            (root / "codex.exe").write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            (root / "codex.exe.sha256").write_text(
                f"{digest}  codex.exe\n", encoding="ascii")
            path, observed = subject.verify_artifact(root)
        self.assertEqual(path.name, "codex.exe")
        self.assertEqual(observed, digest)

    def test_artifact_mismatch_rejects_before_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "codex.exe").write_bytes(b"wrong")
            (root / "codex.exe.sha256").write_text(
                f"{'0' * 64}  codex.exe\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "CHECKSUM_MISMATCH"):
                subject.verify_artifact(root)

    def test_command_binds_tool_free_policy_and_withheld_stdin(self):
        logical_id = "a" * 64
        args = subject.command_line(__file__, logical_id)
        self.assertIn("--no-tools", args)
        self.assertEqual(args[args.index(
            "--capability-snapshot-operation-id") + 1], logical_id)
        self.assertIn("--ignore-user-config", args)
        self.assertIn("mcp_servers={}", args)
        self.assertIn("read-only", args)
        self.assertEqual(args[-1], "-")

    def test_logical_identity_binds_executable_hash(self):
        first, binding = subject.logical_operation_id("a" * 64)
        second, _ = subject.logical_operation_id("b" * 64)
        self.assertNotEqual(first, second)
        self.assertEqual(binding["model_turns"], 0)
        self.assertEqual(binding["policy_sha256"], subject.POLICY_SHA256)

    def test_child_environment_excludes_authority_values(self):
        with mock.patch.dict(os.environ, {
                "OPENAI_API_KEY": "secret", "GENIE_TOKEN": "authority",
                "SystemRoot": r"C:\Windows", "PATH": r"C:\Windows"},
                clear=True):
            value = subject.child_environment(r"C:\codex-home")
        self.assertNotIn("OPENAI_API_KEY", value)
        self.assertNotIn("GENIE_TOKEN", value)
        self.assertEqual(value["CODEX_HOME"], str(Path(
            r"C:\codex-home").resolve()))

    def test_post_entry_failure_is_unknown_and_never_retried(self):
        class BrokenJob:
            def __init__(self):
                self.terminated = 0
            def limit_flags(self):
                return subject.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            def assign_process(self, _process):
                raise OSError("assignment failed")
            def terminate(self, _code):
                self.terminated += 1
            def wait_for_active(self, _expected, _timeout):
                return True
            def accounting(self):
                return {"total_processes": 1, "active_processes": 0}
            def close(self):
                pass

        class Stream:
            def close(self):
                pass

        class Process:
            pid = 123
            _handle = 456
            stdin = stdout = stderr = Stream()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact"
            scratch = root / "scratch"
            artifact.mkdir()
            scratch.mkdir()
            raw = b"binary"
            (artifact / "codex.exe").write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            (artifact / "codex.exe.sha256").write_text(
                f"{digest}  codex.exe\n", encoding="ascii")
            with mock.patch.object(subject, "WindowsJob", BrokenJob), \
                    mock.patch.object(subject.subprocess, "Popen",
                                      return_value=Process()) as popen:
                result = subject.run_once(
                    artifact_directory=artifact, codex_home=root,
                    working_directory=scratch,
                    ledger_path=root / "operation.sqlite",
                    evidence_directory=root)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["allow_new_invocation"])


if __name__ == "__main__":
    unittest.main()

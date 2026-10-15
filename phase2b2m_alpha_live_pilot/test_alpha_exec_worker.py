import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest

from phase2b2m_alpha_live_pilot import alpha_exec_worker as subject


class AlphaExecWorkerTests(unittest.TestCase):
    def test_command_binds_isolation_and_stdin_release(self):
        with tempfile.TemporaryDirectory() as root:
            args = subject.command_line(Path("C:/alpha/codex.exe"), root)
        self.assertEqual(args[1:3], ["exec", "--ignore-user-config"])
        self.assertIn("--strict-config", args)
        self.assertIn("--ephemeral", args)
        self.assertIn("--ignore-rules", args)
        self.assertEqual(args[-1], "-")
        pairs = list(zip(args, args[1:]))
        self.assertIn(("-c", "mcp_servers={}"), pairs)
        self.assertIn(("--sandbox", "read-only"), pairs)
        for name in ("apps", "plugins", "multi_agent", "shell_tool",
                     "unified_exec", "computer_use", "browser_use"):
            self.assertIn(("--disable", name), pairs)

    def test_environment_contains_no_authority_secret(self):
        env = subject.child_environment(Path("C:/auth-location"))
        self.assertEqual(env["CODEX_HOME"], str(Path("C:/auth-location").resolve()))
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CODEX_ACCESS_TOKEN", env)
        self.assertFalse(any(key.upper().startswith("GENIE") for key in env))

    def test_event_parser_rejects_tool_activity(self):
        good = [
            {"type": "thread.started", "thread_id": "x"},
            {"type": "item.completed", "item": {"type": "reasoning",
             "text": "not authoritative"}},
            {"type": "item.completed", "item": {"type": "agent_message",
             "text": json.dumps(subject.EXPECTED_RESULT)}},
            {"type": "turn.completed", "usage": {}},
        ]
        self.assertEqual(subject._event_result(good)[1], subject.EXPECTED_RESULT)
        bad = good[:1] + [{"type": "item.completed",
                           "item": {"type": "command_execution"}}] + good[1:]
        with self.assertRaisesRegex(RuntimeError, "TOOL_ACTIVITY"):
            subject._event_result(bad)

    def test_operation_identity_binds_token_and_semantics(self):
        a = subject.logical_operation_id("a", "C:/alpha/codex.exe", "v", "11")
        b = subject.logical_operation_id("b", "C:/alpha/codex.exe", "v", "11")
        self.assertNotEqual(a[0], b[0])
        self.assertEqual(a[1]["semantic_request_sha256"],
                         subject.sha256_bytes(subject.SEMANTIC_REQUEST.encode()))

    def test_source_has_no_genie_data_in_semantic_request(self):
        request = subject.SEMANTIC_REQUEST.lower()
        for forbidden in ("token", "queue", "owned", "registry", "callback"):
            self.assertNotIn(forbidden, request)
        source = inspect.getsource(subject)
        self.assertNotIn("resume", source)


if __name__ == "__main__":
    unittest.main()

import inspect
from pathlib import Path
import tempfile
import unittest

from phase2b2l_alpha_isolation_preflight import alpha_isolation_preflight as subject


class AlphaIsolationPreflightTests(unittest.TestCase):
    def test_command_places_options_on_app_server_and_disables_authority(self):
        args = subject.command_line(Path("C:/alpha/codex.exe"))
        self.assertEqual(args[1:3], ["app-server", "--strict-config"])
        self.assertEqual(args[-2:], ["--listen", "stdio://"])
        pairs = list(zip(args, args[1:]))
        self.assertIn(("-c", "mcp_servers={}"), pairs)
        for name in ("apps", "plugins", "multi_agent", "shell_tool",
                     "unified_exec", "computer_use", "browser_use"):
            self.assertIn(("--disable", name), pairs)
        self.assertNotIn("--ignore-user-config", args)

    def test_child_environment_requires_fresh_empty_home_and_excludes_secrets(self):
        with tempfile.TemporaryDirectory() as root:
            env = subject.child_environment(root)
            self.assertEqual(env["CODEX_HOME"], str(Path(root).resolve()))
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("CODEX_ACCESS_TOKEN", env)
            Path(root, "config.toml").write_text("x")
            with self.assertRaisesRegex(ValueError, "NOT_FRESH_EMPTY"):
                subject.child_environment(root)

    def test_feature_disable_set_is_unique_and_currently_named(self):
        self.assertEqual(len(subject.DISABLED_FEATURES),
                         len(set(subject.DISABLED_FEATURES)))
        self.assertIn("codex_apps_mcp_2026_07_28", subject.DISABLED_FEATURES)
        self.assertNotIn("browser_use_mcp_client", subject.DISABLED_FEATURES)

    def test_module_has_no_model_prompt_genie_or_credential_copy(self):
        source = inspect.getsource(subject)
        for forbidden in ("thread/start", "turn/start", "SEMANTIC_REQUEST",
                          "advance_run", "apply_run_event", "auth.json",
                          "copyfile", "copy2"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

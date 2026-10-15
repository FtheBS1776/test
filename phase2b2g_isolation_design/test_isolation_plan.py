from pathlib import Path, PureWindowsPath
import inspect
import re
import unittest

from phase2b2g_isolation_design import isolation_plan as plan


class IsolationDesignTests(unittest.TestCase):
    def test_bound_runtime_fails_closed_to_upgrade_only(self):
        decision = plan.decide(plan.RuntimeSnapshot(
            version="codex-cli 0.162.1",
            supports_ignore_user_config=False,
            auth_file_exists=True,
            explicit_credentials_store=None,
            mcp_section_count=4,
            plugin_or_app_section_count=15,
        ))
        self.assertEqual(decision.status, "DESIGN_BLOCKED_NONCLAIM")
        self.assertEqual(
            decision.preferred_mechanism,
            "UPGRADE_OR_REBIND_THEN_VERIFY_FLAG_OFFLINE")
        self.assertEqual(
            decision.next_authorization, "CODEX_UPGRADE_OR_REBIND_ONLY")
        self.assertFalse(decision.credential_copy_allowed)
        self.assertFalse(decision.process_launch_allowed)

    def test_supported_runtime_still_does_not_authorize_launch(self):
        decision = plan.decide(plan.RuntimeSnapshot(
            version="synthetic-supported-version",
            supports_ignore_user_config=True,
            auth_file_exists=True,
            explicit_credentials_store="file",
            mcp_section_count=0,
            plugin_or_app_section_count=0,
        ))
        self.assertEqual(decision.status, "DESIGN_READY_NONCLAIM")
        self.assertFalse(decision.credential_copy_allowed)
        self.assertFalse(decision.process_launch_allowed)
        self.assertEqual(
            decision.next_authorization,
            "ONE_FRESH_NO_MODEL_ISOLATION_PREFLIGHT")

    def test_authority_fields_are_rejected(self):
        rejected = plan.validate_child_inputs({
            "worker_role", "semantic_request", "genie_token", "queue_path",
            "callback", "registry_path",
        })
        self.assertEqual(rejected, (
            "callback", "genie_token", "queue_path", "registry_path"))

    def test_all_named_authority_fields_are_covered(self):
        self.assertEqual(
            plan.validate_child_inputs(plan.PROHIBITED_CHILD_INPUTS),
            tuple(sorted(plan.PROHIBITED_CHILD_INPUTS)))

    def test_paths_must_be_absolute_distinct_and_outside_prohibited_roots(self):
        roots = [PureWindowsPath(r"C:\genie"), PureWindowsPath(r"C:\repo")]
        self.assertEqual(plan.validate_isolated_paths(
            PureWindowsPath(r"C:\temp\codex-home"),
            PureWindowsPath(r"C:\temp\codex-sqlite"),
            PureWindowsPath(r"C:\temp\scratch"), roots), ())
        self.assertIn("PATH_NOT_ABSOLUTE", plan.validate_isolated_paths(
            PureWindowsPath("relative"), PureWindowsPath(r"C:\temp\db"),
            PureWindowsPath(r"C:\temp\scratch"), roots))
        self.assertIn("PATHS_NOT_DISTINCT", plan.validate_isolated_paths(
            PureWindowsPath(r"C:\temp\same"),
            PureWindowsPath(r"C:\temp\same"),
            PureWindowsPath(r"C:\temp\scratch"), roots))
        self.assertIn("PATH_INTERSECTS_PROHIBITED_ROOT",
                      plan.validate_isolated_paths(
                          PureWindowsPath(r"C:\genie\child"),
                          PureWindowsPath(r"C:\temp\db"),
                          PureWindowsPath(r"C:\temp\scratch"), roots))

    def test_design_module_has_no_execution_or_copy_capability(self):
        source = inspect.getsource(plan)
        for forbidden in (
                "subprocess", "Popen", "CreateProcess", "shutil", "copyfile",
                "requests", "urllib", "socket", "auth.json').read",
                'auth.json").read'):
            self.assertNotIn(forbidden, source)

    def test_no_real_auth_path_or_secret_value_is_serialized(self):
        source = Path(plan.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Users", source)
        self.assertNotIn(".codex", source)
        self.assertIsNone(re.search(r"(?i)\b[0-9a-f]{64}\b", source))


if __name__ == "__main__":
    unittest.main()

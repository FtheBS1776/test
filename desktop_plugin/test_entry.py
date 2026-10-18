"""Live entry composition over existing binder/transport; NO MODEL CALL."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop_plugin import entry, live_state_windows as live
from shared_interfaces import mcp_server


class LiveEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        # An apparently usable retired cache must never substitute for live state.
        state = self.data / "state"
        state.mkdir()
        (state / ".genie-state.json").write_text(json.dumps(
            {"state_format": 1, "seeded_from": "retired-fixture"}))
        (state / "REGISTRY.json").write_text("{}\n")
        self.before = self.snapshot()
        self.runs = {"actual": {"queue": "owned-queue", "run_id": "owned-run",
                                "owned_root": "owned-work"}}

    def snapshot(self):
        return {p.relative_to(self.data).as_posix(): p.read_bytes()
                for p in self.data.rglob("*") if p.is_file()}

    def test_missing_or_invalid_live_state_never_uses_existing_cache(self):
        for reason in ("LIVE_STATE_UNAVAILABLE", "LIVE_STATE_INVALID", "LIVE_STATE_PATH"):
            with self.subTest(reason=reason), patch.dict(entry.os.environ,
                    {"PLUGIN_DATA": str(self.data)}, clear=True), patch.object(
                    live, "load_live_runs", side_effect=live.LiveStateError(reason)) as binder, patch.object(
                    entry, "_run_transport") as transport, redirect_stderr(io.StringIO()) as error:
                self.assertEqual(entry.main(), 2)
                self.assertEqual(error.getvalue(), "GENIE_PLUGIN_REJECT:" + reason + "\n")
                binder.assert_called_once_with()
                transport.assert_not_called()
                self.assertEqual(self.snapshot(), self.before)

    def test_unexpected_binding_failure_is_sanitized_and_preserves_cache(self):
        with patch.dict(entry.os.environ, {"PLUGIN_DATA": str(self.data)}, clear=True), patch.object(
                live, "load_live_runs", side_effect=OSError("private path")), patch.object(
                entry, "_run_transport") as transport, redirect_stderr(io.StringIO()) as error:
            self.assertEqual(entry.main(), 2)
        self.assertEqual(error.getvalue(), "GENIE_PLUGIN_REJECT:LIVE_STATE_INVALID\n")
        transport.assert_not_called()
        self.assertEqual(self.snapshot(), self.before)

    def test_valid_binding_is_passed_to_transport_without_cache_selection(self):
        with patch.dict(entry.os.environ, {"PLUGIN_DATA": str(self.data)}, clear=True), patch.object(
                live, "load_live_runs", return_value=self.runs) as binder, patch.object(
                entry, "_run_transport") as transport:
            self.assertEqual(entry.main(), 0)
        binder.assert_called_once_with()
        transport.assert_called_once_with(self.runs)
        self.assertEqual(self.snapshot(), self.before)

    def test_build_probe_requires_live_binding_and_cannot_bypass_it(self):
        with patch.dict(entry.os.environ, {entry.SELFTEST_ENV: "1", "PLUGIN_DATA": str(self.data)}, clear=True), patch.object(
                live, "load_live_runs", side_effect=live.LiveStateError("LIVE_STATE_UNAVAILABLE")), patch.object(
                entry, "_build_selftest") as probe, patch.object(
                entry, "_run_transport") as transport, redirect_stderr(io.StringIO()):
            self.assertEqual(entry.main(), 2)
            probe.assert_not_called()
            transport.assert_not_called()

    def test_source_or_sdk_binding_failure_never_enters_stdio(self):
        with patch.object(mcp_server, "main", side_effect=AssertionError("retired route")), patch.object(
                mcp_server, "build_server", side_effect=ValueError("private binding detail")), patch.object(
                mcp_server, "serve_stdio", create=True) as serve:
            with self.assertRaisesRegex(entry._BootstrapReject, "^TRANSPORT_BINDING$"):
                entry._run_transport(self.runs)
            serve.assert_not_called()

    def test_transport_failure_is_sanitized_without_retry(self):
        server = object()
        with patch.object(mcp_server, "main", side_effect=AssertionError("retired route")), patch.object(
                mcp_server, "build_server", return_value=server), patch.object(
                mcp_server, "serve_stdio", side_effect=OSError("private detail"), create=True) as serve:
            with self.assertRaisesRegex(entry._BootstrapReject, "^TRANSPORT_RUNTIME$"):
                entry._run_transport(self.runs)
            serve.assert_called_once_with(server)


if __name__ == "__main__":
    unittest.main()

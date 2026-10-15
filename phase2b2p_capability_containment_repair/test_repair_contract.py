import json
import unittest

from phase2b2p_capability_containment_repair import repair_contract as subject


EXPECTED = {
    "logical_operation_id": "logical",
    "executable_sha256": "aa",
    "model": "gpt-5.6-sol",
    "sandbox": "read-only",
    "policy_sha256": "bb",
}


def snapshot(**changes):
    value = {
        "version": 1,
        "logical_operation_id": "logical",
        "executable_sha256": "aa",
        "model": "gpt-5.6-sol",
        "sandbox": "read-only",
        "policy_sha256": "bb",
        "tool_count": 0,
        "tools": [],
    }
    value.update(changes)
    return {"type": "capability.snapshot", "snapshot": value}


def jsonl(events):
    return b"".join((json.dumps(event) + "\n").encode() for event in events)


class FakeJob:
    def __init__(self, pids):
        self.pids = pids

    def process_ids(self):
        return tuple(self.pids)


class FakeHandle:
    paths = {}
    calls = []
    exit_codes = {}

    def __init__(self, pid):
        self.pid = pid
        self.closed = False

    def image_path(self):
        self.calls.append((self.pid, "image"))
        return self.paths[self.pid]

    def exit_code(self):
        self.calls.append((self.pid, "exit"))
        return self.exit_codes.get(self.pid, 259)

    def close(self):
        self.closed = True


class RepairContractTests(unittest.TestCase):
    def test_empty_snapshot_must_precede_turn(self):
        events = [
            {"type": "thread.started"}, snapshot(), {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message"}},
            {"type": "turn.completed"},
        ]
        result = subject.classify_attested_events(jsonl(events), EXPECTED)
        self.assertEqual(result["snapshot"]["tool_count"], 0)

    def test_nonempty_stale_duplicate_and_late_snapshots_fail_closed(self):
        cases = [
            [snapshot(tool_count=1, tools=["exec"]), {"type": "turn.started"},
             {"type": "turn.completed"}],
            [snapshot(logical_operation_id="stale"), {"type": "turn.started"},
             {"type": "turn.completed"}],
            [snapshot(), snapshot(), {"type": "turn.started"},
             {"type": "turn.completed"}],
            [{"type": "turn.started"}, snapshot(), {"type": "turn.completed"}],
        ]
        for events in cases:
            with self.subTest(events=events), self.assertRaises(ValueError):
                subject.classify_attested_events(jsonl(events), EXPECTED)

    def test_only_exact_pre_turn_advisory_is_tolerated(self):
        good = [snapshot(),
                {"type": "item.completed", "item": {
                    "type": "error", "message": subject.DISABLED_CODE_MODE_ADVISORY}},
                {"type": "turn.started"}, {"type": "turn.completed"}]
        self.assertEqual(subject.classify_attested_events(
            jsonl(good), EXPECTED)["advisory_count"], 1)
        bad = [snapshot(), {"type": "turn.started"},
               {"type": "item.completed", "item": {
                   "type": "error", "message": subject.DISABLED_CODE_MODE_ADVISORY}},
               {"type": "turn.completed"}]
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_ERROR"):
            subject.classify_attested_events(jsonl(bad), EXPECTED)

    def test_any_tool_item_fails_despite_empty_snapshot(self):
        events = [snapshot(), {"type": "turn.started"},
                  {"type": "item.completed", "item": {
                      "type": "mcp_tool_call"}}, {"type": "turn.completed"}]
        with self.assertRaisesRegex(ValueError, "TOOL_ACTIVITY"):
            subject.classify_attested_events(jsonl(events), EXPECTED)

    def test_member_identity_is_captured_at_first_observation(self):
        FakeHandle.calls = []
        FakeHandle.paths = {10: "codex.exe", 11: "conhost.exe"}
        FakeHandle.exit_codes = {}
        monitor = subject.EagerMemberMonitor(
            FakeJob([10, 11]), handle_factory=FakeHandle,
            hash_file=lambda path: "hash:" + path)
        monitor.observe_once()
        self.assertEqual(FakeHandle.calls,
                         [(10, "image"), (10, "exit"),
                          (11, "image"), (11, "exit")])
        self.assertEqual(monitor.identities[10].image_sha256, "hash:codex.exe")
        self.assertTrue(subject.verify_member_accounting(
            monitor.identities, {"total_processes": 2, "active_processes": 0}))

    def test_accounting_gap_fails_closed(self):
        identities = {1: subject.MemberIdentity(1, "a", "h", True)}
        with self.assertRaisesRegex(ValueError, "TOTAL_MEMBER"):
            subject.verify_member_accounting(
                identities, {"total_processes": 2, "active_processes": 0})

    def test_exited_member_fails_closed_during_snapshot(self):
        FakeHandle.calls = []
        FakeHandle.paths = {12: "child.exe"}
        FakeHandle.exit_codes = {12: 7}
        monitor = subject.EagerMemberMonitor(
            FakeJob([12]), handle_factory=FakeHandle,
            hash_file=lambda path: "hash:" + path)
        with self.assertRaisesRegex(RuntimeError, "EXITED_BEFORE"):
            monitor.observe_once()

    def test_nonzero_active_count_fails_closed(self):
        identities = {1: subject.MemberIdentity(1, "a", "h", True)}
        with self.assertRaisesRegex(ValueError, "ACTIVE_AFTER_EXIT"):
            subject.verify_member_accounting(
                identities, {"total_processes": 1, "active_processes": 1})


if __name__ == "__main__":
    unittest.main()

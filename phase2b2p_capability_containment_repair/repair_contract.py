"""Fail-closed validators for a future tool-free Codex live turn.

This module does not launch Codex or a model.  It defines the evidence that a
patched, hash-bound Codex child must emit before the controller may release the
semantic request, and it captures Windows process identity while each process
is still observable.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import threading
import time

from shared_interfaces.windows_job import ProcessWaitHandle


CAPABILITY_EVENT = "capability.snapshot"
SNAPSHOT_VERSION = 1
DISABLED_CODE_MODE_ADVISORY = (
    "Code Mode is unavailable because code-mode host is disabled. Code mode "
    "will fail closed; enable `features.code_mode_host` and install "
    "`codex-code-mode-host`."
)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_capability_snapshot(event, expected):
    """Return a normalized snapshot or reject any widening/ambiguity."""
    if type(event) is not dict or event.get("type") != CAPABILITY_EVENT:
        raise ValueError("CAPABILITY_SNAPSHOT_MISSING")
    snapshot = event.get("snapshot")
    if type(snapshot) is not dict:
        raise ValueError("CAPABILITY_SNAPSHOT_NOT_OBJECT")
    exact = {
        "version": SNAPSHOT_VERSION,
        "logical_operation_id": expected["logical_operation_id"],
        "executable_sha256": expected["executable_sha256"].lower(),
        "model": expected["model"],
        "sandbox": expected["sandbox"],
        "policy_sha256": expected["policy_sha256"].lower(),
        "tool_count": 0,
        "tools": [],
    }
    if snapshot != exact:
        raise ValueError("CAPABILITY_SNAPSHOT_MISMATCH")
    return exact


def classify_attested_events(raw, expected):
    """Validate ordering, empty inventory, and the one known advisory shape."""
    events = []
    for line in raw.decode("utf-8", "strict").splitlines():
        if not line:
            continue
        value = json.loads(line)
        if type(value) is not dict:
            raise ValueError("EVENT_NOT_OBJECT")
        events.append(value)
    snapshots = [event for event in events if event.get("type") == CAPABILITY_EVENT]
    if len(snapshots) != 1:
        raise ValueError("CAPABILITY_SNAPSHOT_COUNT")
    snapshot_index = events.index(snapshots[0])
    turn_indices = [index for index, event in enumerate(events)
                    if event.get("type") == "turn.started"]
    if len(turn_indices) != 1 or snapshot_index >= turn_indices[0]:
        raise ValueError("CAPABILITY_SNAPSHOT_ORDER")
    snapshot = validate_capability_snapshot(snapshots[0], expected)
    advisories = []
    tool_items = []
    for index, event in enumerate(events):
        if event.get("type") not in ("item.started", "item.updated",
                                     "item.completed"):
            continue
        item = event.get("item")
        if type(item) is not dict or type(item.get("type")) is not str:
            raise ValueError("ITEM_TYPE_MISSING")
        item_type = item["type"]
        if item_type == "error":
            if (event.get("type") != "item.completed"
                    or item.get("message") != DISABLED_CODE_MODE_ADVISORY
                    or index >= turn_indices[0]):
                raise ValueError("UNEXPECTED_ERROR_ITEM")
            advisories.append(index)
        elif item_type not in ("reasoning", "plan", "agent_message",
                               "assistant_message"):
            tool_items.append(item_type)
    if len(advisories) > 1:
        raise ValueError("ADVISORY_COUNT")
    if tool_items:
        raise ValueError("TOOL_ACTIVITY_OBSERVED")
    if sum(event.get("type") == "turn.completed" for event in events) != 1:
        raise ValueError("TURN_COMPLETION_COUNT")
    return {"snapshot": snapshot, "advisory_count": len(advisories),
            "tool_item_types": []}


@dataclass(frozen=True)
class MemberIdentity:
    pid: int
    image: str
    image_sha256: str
    observed_while_active: bool


class EagerMemberMonitor:
    """Retain a handle and snapshot image identity at first PID observation."""

    def __init__(self, job, handle_factory=ProcessWaitHandle,
                 hash_file=_sha256_file, interval_seconds=0.002):
        self.job = job
        self.handle_factory = handle_factory
        self.hash_file = hash_file
        self.interval_seconds = interval_seconds
        self.handles = {}
        self.identities = {}
        self._observation_lock = threading.Lock()
        self.error = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def observe_once(self):
        with self._observation_lock:
            for pid in self.job.process_ids():
                if pid in self.handles:
                    continue
                handle = self.handle_factory(pid)
                try:
                    image = handle.image_path()
                    identity = MemberIdentity(
                        pid=pid,
                        image=image,
                        image_sha256=self.hash_file(image),
                        observed_while_active=handle.exit_code() == 259,
                    )
                    if not identity.observed_while_active:
                        raise RuntimeError(
                            "MEMBER_EXITED_BEFORE_IDENTITY_SNAPSHOT")
                except BaseException:
                    handle.close()
                    raise
                self.handles[pid] = handle
                self.identities[pid] = identity

    def _run(self):
        try:
            while not self.stop.is_set():
                self.observe_once()
                time.sleep(self.interval_seconds)
        except BaseException as exc:
            self.error = f"{type(exc).__name__}:{str(exc)[:160]}"

    def finish(self):
        self.stop.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive() or self.error:
            raise RuntimeError("MEMBER_MONITOR_UNCERTAIN")
        return dict(self.handles), dict(self.identities)


def verify_member_accounting(identities, accounting):
    total = accounting.get("total_processes")
    active = accounting.get("active_processes")
    if type(total) is not int or type(active) is not int:
        raise ValueError("JOB_ACCOUNTING_SHAPE")
    if len(identities) != total:
        raise ValueError("TOTAL_MEMBER_CAPTURE_MISMATCH")
    if active != 0:
        raise ValueError("JOB_ACTIVE_AFTER_EXIT")
    if any(not identity.observed_while_active for identity in identities.values()):
        raise ValueError("MEMBER_IDENTITY_NOT_LIVE_SNAPSHOTTED")
    return True


__all__ = [
    "CAPABILITY_EVENT", "DISABLED_CODE_MODE_ADVISORY", "EagerMemberMonitor",
    "MemberIdentity", "classify_attested_events", "validate_capability_snapshot",
    "verify_member_accounting",
]

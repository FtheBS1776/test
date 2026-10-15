"""Execute one fresh fixture-only eager-identity Job Object preflight."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

from phase2b2p_capability_containment_repair.repair_contract import (
    EagerMemberMonitor,
    verify_member_accounting,
)
from shared_interfaces.windows_job import (
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    STILL_ACTIVE,
    WindowsJob,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "phase2b2b_containment" / "process_tree_fixture.py"
GATE = b"RELEASE_AFTER_JOB_ASSIGNMENT\n"


def _readline(stream, result):
    try:
        result.append(stream.readline(4096))
    except BaseException as exc:
        result.append(exc)


def run():
    if os.name != "nt":
        raise OSError("WINDOWS_REQUIRED")
    job = WindowsJob()
    process = None
    monitor = None
    handles = {}
    report_holder = []
    termination_attempted = False
    try:
        with tempfile.TemporaryDirectory(prefix="genie-eager-member-") as scratch:
            environment = {"GENIE_EXECUTION_CLASS": "NO_MODEL_CALL_REPAIR_PREFLIGHT"}
            for key in ("SystemRoot", "WINDIR"):
                if key in os.environ:
                    environment[key] = os.environ[key]
            process = subprocess.Popen(
                [sys.executable, "-I", "-S", "-B", str(FIXTURE),
                 "--role", "parent"],
                cwd=scratch, env=environment, shell=False,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            job.assign_process(process)
            if (job.limit_flags() != JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    or not job.contains_handle(int(process._handle))):
                raise RuntimeError("ASSIGNMENT_NOT_VERIFIED")
            monitor = EagerMemberMonitor(job)
            monitor.observe_once()
            monitor.start()
            reader = threading.Thread(
                target=_readline, args=(process.stdout, report_holder), daemon=True)
            reader.start()
            process.stdin.write(GATE)
            process.stdin.close()
            reader.join(timeout=5)
            if reader.is_alive() or len(report_holder) != 1:
                raise RuntimeError("FIXTURE_REPORT_TIMEOUT")
            if isinstance(report_holder[0], BaseException):
                raise report_holder[0]
            report = json.loads(report_holder[0].decode("ascii", "strict"))
            if report.get("model_invoked") is not False:
                raise RuntimeError("MODEL_FIXTURE_CONTRACT")
            deadline = time.monotonic() + 5
            while job.accounting()["total_processes"] < 2:
                if time.monotonic() >= deadline:
                    raise RuntimeError("DESCENDANT_NOT_ACCOUNTED")
                monitor.observe_once()
                time.sleep(0.005)
            monitor.observe_once()
            before = job.accounting()
            termination_attempted = True
            job.terminate(0x2B2)
            if not job.wait_for_active(0, 10):
                raise RuntimeError("JOB_DID_NOT_REACH_ZERO")
            process.wait(timeout=5)
            handles, identities = monitor.finish()
            after = job.accounting()
            verify_member_accounting(identities, after)
            for handle in handles.values():
                if not handle.wait(2) or handle.exit_code() == STILL_ACTIVE:
                    raise RuntimeError("MEMBER_NOT_TERMINATED")
            return {
                "classification": "NO_MODEL_EAGER_IDENTITY_PREFLIGHT_VERIFIED",
                "model_invoked": False,
                "assignment_verified_before_gate": True,
                "termination_attempt_count": 1,
                "accounting_before_termination": before,
                "accounting_after_termination": after,
                "members": [identity.__dict__ for _, identity in
                            sorted(identities.items())],
                "allow_model_turn": False,
                "allow_new_invocation": False,
            }
    finally:
        if monitor is not None and monitor.thread.is_alive():
            try:
                handles, _ = monitor.finish()
            except Exception:
                pass
        if not termination_attempted:
            try:
                job.terminate(0x2B2)
            except Exception:
                pass
        for handle in handles.values():
            try:
                handle.close()
            except Exception:
                pass
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except Exception:
                    pass
        job.close()


if __name__ == "__main__":
    destination = Path(__file__).resolve().parent / "NO_MODEL_PREFLIGHT.json"
    if destination.exists():
        raise SystemExit("NO_MODEL_PREFLIGHT_ALREADY_EXISTS")
    result = run()
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, sort_keys=True))

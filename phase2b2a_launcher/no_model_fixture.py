"""Deterministic child used only to test the Phase 2B2A process boundary."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time


PROTOCOL = "genie-no-model-worker-fixture-v1"
MODES = {
    "success", "crash", "nonzero", "timeout", "malformed", "oversize",
    "stderr_oversize", "invalid_utf8", "duplicate", "nonfinite", "extra",
    "wrong_hash", "wrong_protocol", "wrong_stdin", "wrong_argv",
    "wrong_environment", "repository_true", "model_true", "wrong_proposal",
    "wrong_classification", "stderr", "missing",
}


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


def _constant(_value):
    raise ValueError("nonfinite value")


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8", errors="strict")


def _inside_repository():
    current = Path.cwd().resolve()
    return any((path / ".git").exists() for path in (current, *current.parents))


def _success(raw, body):
    request_hash = body.get("request_sha256")
    value = {
        "protocol": PROTOCOL,
        "classification": "UNTRUSTED_FIXTURE_OUTPUT",
        "request_sha256": request_hash,
        "stdin_sha256": hashlib.sha256(raw).hexdigest(),
        "argv_sha256": hashlib.sha256(_canonical(sys.argv)).hexdigest(),
        "environment_keys": sorted(key.upper() for key in os.environ),
        "cwd_is_repository": _inside_repository(),
        "model_invoked": False,
        "proposal": "NO_MODEL_CALL",
    }
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--mode", required=True, choices=sorted(MODES))
    args = parser.parse_args(argv)

    if args.mode == "timeout":
        time.sleep(30)
        return 0
    if args.mode == "crash":
        os._exit(7)
    if args.mode == "nonzero":
        sys.stderr.write("FIXTURE_NONZERO\n")
        return 9
    if args.mode == "oversize":
        sys.stdout.buffer.write(b"x" * 131072)
        return 0
    if args.mode == "stderr_oversize":
        sys.stderr.buffer.write(b"x" * 32768)
        time.sleep(30)
        return 0
    if args.mode == "invalid_utf8":
        sys.stdout.buffer.write(b"\xff")
        return 0
    if args.mode == "malformed":
        sys.stdout.write("{")
        return 0
    if args.mode == "duplicate":
        sys.stdout.write('{"status":"one","status":"two"}')
        return 0
    if args.mode == "nonfinite":
        sys.stdout.write('{"value":NaN}')
        return 0

    raw = sys.stdin.buffer.read()
    try:
        body = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=_constant)
    except Exception:
        return 11
    value = _success(raw, body)
    if args.mode == "wrong_hash":
        value["request_sha256"] = "0" * 64
    if args.mode == "wrong_protocol":
        value["protocol"] = "wrong"
    if args.mode == "wrong_stdin":
        value["stdin_sha256"] = "0" * 64
    if args.mode == "wrong_argv":
        value["argv_sha256"] = "0" * 64
    if args.mode == "wrong_environment":
        value["environment_keys"] = ["UNEXPECTED"]
    if args.mode == "repository_true":
        value["cwd_is_repository"] = True
    if args.mode == "model_true":
        value["model_invoked"] = True
    if args.mode == "wrong_proposal":
        value["proposal"] = "UNEXPECTED"
    if args.mode == "wrong_classification":
        value["classification"] = "TRUSTED"
    if args.mode == "missing":
        del value["proposal"]
    if args.mode == "extra":
        value["extra"] = True
    if args.mode == "stderr":
        sys.stderr.write("UNEXPECTED_STDERR\n")
    sys.stdout.buffer.write(_canonical(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

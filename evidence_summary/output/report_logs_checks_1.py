"""Report bounded snapshots of supplied logs, with no execution claims.

The only code loaded from disk is the fixed, SHA256-pinned repository parser.
Input logs are decoded as text and summarized, never executed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import types

LIMIT = 1048576
SCOPE = "TEST_LOG_SUMMARY_ONLY"
DEPENDENCY_SHA256 = "5e635b97b764c0f88ae8e497ca48ec76e480d677610b24915cc2e900e681d826"


def _load_summarize():
    # Both output/report_logs_1.py and delivered report_logs.py share this
    # evidence_summary ancestor. No cwd-based or external fallback is allowed.
    evidence_dir = next(
        (parent for parent in Path(__file__).resolve().parents
         if parent.name == "evidence_summary"), None
    )
    if evidence_dir is None:
        raise RuntimeError("fixed repository dependency location unavailable")
    source_path = evidence_dir.parent / "comparison_pilot" / "validation_summary.py"
    with open(source_path, "rb") as source:
        raw = source.read(12001)
    if hashlib.sha256(raw).hexdigest() != DEPENDENCY_SHA256:
        raise RuntimeError("repository parser source pin mismatch")
    module = types.ModuleType("_pinned_validation_summary")
    module.__file__ = str(source_path)
    # Import exactly the verified bytes rather than allowing a loader to
    # reopen the pathname or use an unverified cached bytecode file.
    exec(compile(raw, str(source_path), "exec"), module.__dict__)
    return module.summarize


def _validate_inputs(inputs):
    if type(inputs) is not list or not 1 <= len(inputs) <= 8:
        raise ValueError("inputs must be a list of 1..8 specifications")
    validated = []
    seen = set()
    for spec in inputs:
        if type(spec) is not dict or set(spec) != {"path", "format"}:
            raise ValueError("each specification needs exactly path and format")
        path, format = spec["path"], spec["format"]
        if type(path) is not str or not 1 <= len(path) <= 4096 or "\x00" in path:
            raise ValueError("invalid input path")
        if type(format) is not str or format not in ("unittest", "json", "checks"):
            raise ValueError("invalid input format")
        if path in seen:
            raise ValueError("duplicate exact input path")
        seen.add(path)
        validated.append((path, format))
    return validated


def _rejected_summary():
    return {"status": "REJECT", "count": None, "evidence_scope": SCOPE}


def _nonblocking_opener(path, flags):
    # This avoids waiting for a FIFO writer before fstat rejects nonregular
    # files. Regular files retain ordinary binary-read semantics.
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))



def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("nonstandard JSON constant")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON float")
    return number


def _checks_summary(text, summarize):
    # Validate the complete JSON, including metadata, before extracting core.
    # Metadata values never supply summary authority and are never echoed.
    try:
        data = json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant, parse_float=_finite_float)
        json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
        core_keys = {"status", "count", "checks"}
        if type(data) is not dict or not core_keys <= set(data):
            raise ValueError("missing core fields")
        if type(data["checks"]) is not list:
            raise ValueError("checks must be a list")
        core_checks = []
        ignored_check_fields = set()
        for check in data["checks"]:
            if type(check) is not dict or "check" not in check:
                raise ValueError("check object required")
            if ("passed" in check) == ("rejected" in check):
                raise ValueError("exactly one check flag required")
            flag = "passed" if "passed" in check else "rejected"
            core_checks.append({"check": check["check"], flag: check[flag]})
            ignored_check_fields.update(set(check) - {"check", flag})
        core = {"status": data["status"], "count": data["count"], "checks": core_checks}
        core_text = json.dumps(core, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False)
        projection = {
            "scope": "STATUS_COUNT_CHECK_FLAGS_ONLY",
            "ignored_top_fields": sorted(set(data) - core_keys),
            "ignored_check_fields": sorted(ignored_check_fields),
        }
        # Preserve projection for structurally extracted cores even when the
        # unchanged strict parser rejects status/count/name/flag consistency.
        return summarize(core_text, "json"), projection
    except (ValueError, TypeError, RecursionError, OverflowError):
        return _rejected_summary(), None


def _capture(path, format, summarize):
    entry = {
        "path": path,
        "format": format,
        "sha256": None,
        "bytes": None,
        "read_status": "UNREADABLE",
        "summary": _rejected_summary(),
    }
    if format == "checks":
        entry["projection"] = None
    try:
        with open(path, "rb", opener=_nonblocking_opener) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                return entry
            raw = source.read(LIMIT + 1)
    except (OSError, ValueError):
        return entry
    if len(raw) > LIMIT:
        entry["read_status"] = "TOO_LARGE"
        return entry
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    entry["bytes"] = len(raw)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        entry["read_status"] = "INVALID_UTF8"
        return entry
    entry["read_status"] = "CAPTURED"
    if format == "checks":
        entry["summary"], entry["projection"] = _checks_summary(text, summarize)
    else:
        entry["summary"] = summarize(text, format)
    return entry


def build_report(inputs):
    """Validate all specifications, then capture each input once in order.

    Invalid specifications raise ValueError before any input log is opened.
    Per-file read failures are entries, not whole-report failures. Each hash
    binds captured bytes; separate captures are not an atomic group snapshot.
    """
    validated = _validate_inputs(inputs)
    summarize = _load_summarize()
    entries = [_capture(path, format, summarize) for path, format in validated]
    return {
        "status": "REPORT_BUILT",
        "evidence_scope": SCOPE,
        "execution_claim": "NONE",
        "fresh_sink_claim": "NONE",
        "entries": entries,
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


class _Once(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if getattr(namespace, self.dest) is not None:
            raise ValueError("output must be specified exactly once")
        setattr(namespace, self.dest, value)


def main(argv=None):
    status = "REJECT"
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument("--output", required=True, action=_Once)
        parser.add_argument("--input", nargs=2, action="append", required=True)
        args = parser.parse_args(argv)
        inputs = [{"path": path, "format": format} for format, path in args.input]
        report = build_report(inputs)
        # Serialize everything before exclusive creation. ASCII escaping also
        # permits any valid host path string to appear in strict UTF8 JSON.
        serialized = json.dumps(report, ensure_ascii=True, separators=(",", ":")) + "\n"
        with open(args.output, "x", encoding="utf-8", newline="\n") as output:
            output.write(serialized)
        status = "REPORT_WRITTEN"
    except (OSError, ValueError, RuntimeError):
        # Keep any newly-created partial output for inspection. No retry,
        # deletion, replacement, automatic parents or success receipt.
        pass
    print(json.dumps({"status": status, "evidence_scope": SCOPE}, separators=(",", ":")))
    return 0 if status == "REPORT_WRITTEN" else 2


if __name__ == "__main__":
    sys.exit(main())

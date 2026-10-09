"""Summarize supplied validation logs; this does not verify their execution."""

import argparse
import json
import os
import re
import sys

SCOPE = "TEST_LOG_SUMMARY_ONLY"
LIMIT = 1024 * 1024
SUMMARY = re.compile(r"Ran ([0-9]+) tests? in ([0-9]+(?:\.[0-9]+)?)s")
OK = re.compile(r"OK(?: \(skipped=([0-9]+)\))?")
FAILED = re.compile(
    r"FAILED \((?:failures=([0-9]+)(?:, errors=([0-9]+))?"
    r"|errors=([0-9]+))(?:, skipped=([0-9]+))?\)"
)


def _result(status, count=None):
    return {"status": status, "count": count, "evidence_scope": SCOPE}


def _unittest(text):
    lines = text.splitlines()
    nonblank = [i for i, line in enumerate(lines) if line.strip()]
    summaries = [(i, SUMMARY.fullmatch(line)) for i, line in enumerate(lines)
                 if SUMMARY.fullmatch(line)]
    if len(summaries) != 1 or not nonblank:
        return _result("REJECT")
    summary_index, summary = summaries[0]
    # A summary or result-like line that is unsupported is contradictory evidence.
    markers = []
    for i, line in enumerate(lines):
        if re.match(r"Ran\s+[0-9]+\s+tests?\b", line) and i != summary_index:
            return _result("REJECT")
        if re.match(r"(?:OK\b|FAILED\b|NO TESTS RAN\b)", line):
            markers.append(i)
    if markers != [nonblank[-1]] or summary_index >= markers[0]:
        return _result("REJECT")
    # Only blank lines may separate the summary from its concluding result.
    if any(line.strip() for line in lines[summary_index + 1:markers[0]]):
        return _result("REJECT")
    n = int(summary.group(1))
    marker = lines[markers[0]]
    if marker == "NO TESTS RAN":
        return _result("NO_COVERAGE", 0) if n == 0 else _result("REJECT")
    ok = OK.fullmatch(marker)
    if ok:
        skipped = int(ok.group(1) or "0")
        if skipped > n:
            return _result("REJECT")
        effective = n - skipped
        return _result("PASS" if effective else "NO_COVERAGE", effective)
    failed = FAILED.fullmatch(marker)
    if not failed:
        return _result("REJECT")
    failures, errors, errors_only, skipped = (
        int(value or "0") for value in failed.groups()
    )
    errors += errors_only
    if failures + errors == 0 or failures + errors + skipped > n:
        return _result("REJECT")
    return _result("FAIL", n - skipped)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("nonstandard JSON constant")


def _json(text):
    data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    if type(data) is not dict or set(data) != {"status", "count", "checks"}:
        return _result("REJECT")
    status, count, checks = data["status"], data["count"], data["checks"]
    if (type(status) is not str or status not in ("PASS", "FAIL")
            or type(count) is not int or count < 0 or type(checks) is not list
            or count != len(checks)):
        return _result("REJECT")
    flags = []
    for check in checks:
        if type(check) is not dict or set(check) not in (
                {"check", "passed"}, {"check", "rejected"}):
            return _result("REJECT")
        name = check["check"]
        if (type(name) is not str or not name or name != name.strip()
                or len(name) > 200):
            return _result("REJECT")
        flag = check["passed"] if "passed" in check else check["rejected"]
        if type(flag) is not bool:
            return _result("REJECT")
        flags.append(flag)
    if count == 0:
        return _result("NO_COVERAGE", 0)
    if (status == "PASS") != all(flags):
        return _result("REJECT")
    return _result(status, count)


def summarize(text, format):
    """Return only status, count, and evidence scope; malformed logs reject."""
    try:
        if type(text) is not str or type(format) is not str:
            return _result("REJECT")
        if format == "unittest":
            return _unittest(text)
        if format == "json":
            return _json(text)
        return _result("REJECT")
    except Exception:
        return _result("REJECT")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument("path")
        parser.add_argument("--format", required=True, choices=("unittest", "json"))
        args = parser.parse_args(argv)
        with open(args.path, "rb") as stream:
            if os.fstat(stream.fileno()).st_size > LIMIT:
                raise ValueError("input exceeds size limit")
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("input exceeds size limit")
        result = summarize(raw.decode("utf-8", errors="strict"), args.format)
    except Exception:
        result = _result("REJECT")
    print(json.dumps(result, separators=(",", ":")))
    return {"PASS": 0, "FAIL": 1, "NO_COVERAGE": 1, "REJECT": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())

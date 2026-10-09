"""Summarize supplied validation logs, without verifying their execution.

CLI: python3.12 -B validation_summary_1.py PATH --format unittest|json
All results describe only the supplied log, never its authenticity or correctness.
"""
import argparse
import json
import re
import sys

LIMIT = 1024 * 1024
SCOPE = "TEST_LOG_SUMMARY_ONLY"
SUMMARY = re.compile(r"Ran ([0-9]+) tests? in ([0-9]+(?:\.[0-9]+)?)s")
OK_SKIP = re.compile(r"OK \(skipped=([0-9]+)\)")
FAILURE = re.compile(
    r"FAILED \((?:failures=[0-9]+(?:, errors=[0-9]+)?|errors=[0-9]+)"
    r"(?:, skipped=[0-9]+)?\)"
)


def _result(status, count=None):
    return {"status": status, "count": count, "evidence_scope": SCOPE}


def _marker(line):
    """Return marker kind and counts, or None for ordinary trace text."""
    if line == "OK":
        return "OK", {"skipped": 0}
    match = OK_SKIP.fullmatch(line)
    if match:
        return "OK", {"skipped": int(match.group(1))}
    if line == "NO TESTS RAN":
        return "EMPTY", {}
    if FAILURE.fullmatch(line):
        fields = line[len("FAILED ("):-1].split(", ")
        return "FAILED", {k: int(v) for k, v in (f.split("=") for f in fields)}
    return None


def _unittest(text):
    lines = [line for line in text.splitlines() if line.strip()]
    summaries = []
    markers = []
    for i, line in enumerate(lines):
        match = SUMMARY.fullmatch(line)
        if match:
            summaries.append((i, int(match.group(1))))
        elif line.lstrip().startswith("Ran "):
            return _result("REJECT")
        marker = _marker(line)
        if marker is not None:
            markers.append((i, marker))
        elif re.match(r"(?:OK|FAILED|NO TESTS RAN)(?:\s|\(|$)", line.lstrip()):
            # A result-like line in an unsupported form cannot supply evidence.
            return _result("REJECT")
    if len(summaries) != 1 or len(markers) != 1:
        return _result("REJECT")
    summary_index, total = summaries[0]
    marker_index, (kind, counts) = markers[0]
    if marker_index != len(lines) - 1 or summary_index != marker_index - 1:
        return _result("REJECT")
    if kind == "EMPTY":
        return _result("NO_COVERAGE", 0) if total == 0 else _result("REJECT")
    if any(value > total for value in counts.values()) or sum(counts.values()) > total:
        return _result("REJECT")
    effective = total - counts.get("skipped", 0)
    if kind == "FAILED":
        if total == 0 or counts.get("failures", 0) + counts.get("errors", 0) == 0:
            return _result("REJECT")
        return _result("FAIL", effective)
    return _result("PASS" if effective else "NO_COVERAGE", effective)


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def _invalid_constant(value):
    raise ValueError("nonstandard JSON constant")


def _json(text):
    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if type(data) is not dict or set(data) != {"status", "count", "checks"}:
        return _result("REJECT")
    declared, count, checks = data["status"], data["count"], data["checks"]
    if type(declared) is not str or declared not in ("PASS", "FAIL"):
        return _result("REJECT")
    if type(count) is not int or count < 0 or type(checks) is not list or count != len(checks):
        return _result("REJECT")
    flags = []
    for check in checks:
        if type(check) is not dict or set(check) not in ({"check", "passed"}, {"check", "rejected"}):
            return _result("REJECT")
        name = check["check"]
        if type(name) is not str or not name or name != name.strip() or len(name) > 200:
            return _result("REJECT")
        flag = check["passed"] if "passed" in check else check["rejected"]
        if type(flag) is not bool:
            return _result("REJECT")
        flags.append(flag)
    if count == 0:
        return _result("NO_COVERAGE", 0)
    actual = "PASS" if all(flags) else "FAIL"
    return _result(actual, count) if declared == actual else _result("REJECT")


def summarize(text, format):
    """Return status, effective count, and scope; malformed inputs are REJECT."""
    try:
        if type(text) is not str or type(format) is not str or format not in ("unittest", "json"):
            return _result("REJECT")
        if len(text) > LIMIT or len(text.encode("utf-8", errors="strict")) > LIMIT:
            return _result("REJECT")
        return _unittest(text) if format == "unittest" else _json(text)
    except Exception:
        # Includes invalid JSON, excessive nesting, invalid integers and surrogates.
        return _result("REJECT")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    result = _result("REJECT")
    try:
        parser = _Parser(add_help=False, allow_abbrev=False)
        parser.add_argument("path")
        parser.add_argument("--format", required=True, choices=("unittest", "json"))
        args = parser.parse_args(argv)
        with open(args.path, "rb") as source:
            raw = source.read(LIMIT + 1)
        if len(raw) <= LIMIT:
            result = summarize(raw.decode("utf-8", errors="strict"), args.format)
    except Exception:
        pass
    print(json.dumps(result, separators=(",", ":")))
    return {"PASS": 0, "FAIL": 1, "NO_COVERAGE": 1, "REJECT": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())

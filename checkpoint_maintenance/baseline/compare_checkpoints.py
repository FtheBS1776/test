"""Read-only checkpoint manifest comparison; Python 3.12 standard library."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import types
import zipfile

VERIFIER_SHA256 = "6b3c01c598e904c9aa171d7b22995cd0eb918db2c9cabf289c1003987db737b6"
SNAPSHOT_LIMIT = 64 * 1024 * 1024
SCOPE = "INTEGRITY_COMPARISON_ONLY"


class Rejected(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Rejected("CLI_ARGUMENTS: " + message)


def load_verifier():
    # The candidate is staged one level below its eventual run_queue location.
    directory = Path(__file__).resolve().parent
    if directory.name == "model_output":
        directory = directory.parent
    source = directory.parent / "host_adapter" / "verify_checkpoint.py"
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != VERIFIER_SHA256:
        raise Rejected("VERIFIER_SOURCE_BINDING")
    # Load the exact pinned bytes, avoiding a second mutable-source read.
    # This executes reviewed owned source, never code from either archive.
    module = types.ModuleType("_pinned_checkpoint_verifier")
    module.__file__ = str(source)
    exec(compile(raw, str(source), "exec"), module.__dict__)
    return module


def snapshot_manifest(path, expected, verifier):
    # Full verification precedes this snapshot; the snapshot's own outer hash
    # must match the same anchor before any of its compressed content is parsed.
    with open(path, "rb") as stream:
        snapshot = stream.read(SNAPSHOT_LIMIT + 1)
    if len(snapshot) > SNAPSHOT_LIMIT:
        raise Rejected("COMPRESSED_SNAPSHOT_LIMIT")
    actual = hashlib.sha256(snapshot).hexdigest()
    if actual != expected:
        raise Rejected("SNAPSHOT_SHA256_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(snapshot), "r") as archive:
        info = archive.getinfo("MANIFEST.json")
        if info.file_size > verifier.MAX_MANIFEST:
            raise Rejected("SNAPSHOT_MANIFEST_LIMIT")
        with archive.open(info, "r") as manifest:
            raw = manifest.read(verifier.MAX_MANIFEST + 1)
            if len(raw) > verifier.MAX_MANIFEST:
                raise Rejected("SNAPSHOT_MANIFEST_LIMIT")
        return verifier.manifest_schema(raw)


def compare(old_path, new_path, old_sha, new_sha):
    verifier = load_verifier()
    if not verifier.hash_string(old_sha) or not verifier.hash_string(new_sha):
        raise Rejected("EXPECTED_SHA256_FORMAT")
    for path, expected in ((old_path, old_sha), (new_path, new_sha)):
        result = verifier.verify(path, expected)
        if result.get("status") != "PASS" or result.get("outer_sha256") != expected:
            raise Rejected("CHECKPOINT_NOT_VERIFIED")
    old = snapshot_manifest(old_path, old_sha, verifier)
    new = snapshot_manifest(new_path, new_sha, verifier)
    shared = old.keys() & new.keys()
    return {"status": "PASS", "old_sha256": old_sha, "new_sha256": new_sha,
            "added": sorted(new.keys() - old.keys()),
            "removed": sorted(old.keys() - new.keys()),
            "changed": sorted(name for name in shared if old[name] != new[name]),
            "unchanged": sorted(name for name in shared if old[name] == new[name]),
            "evidence_scope": SCOPE}


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("old_zip")
        parser.add_argument("new_zip")
        parser.add_argument("--old-sha256", required=True)
        parser.add_argument("--new-sha256", required=True)
        args = parser.parse_args(argv)
        result = compare(args.old_zip, args.new_zip, args.old_sha256, args.new_sha256)
    except Exception as exc:
        # Ordinary dependency, parsing, CRC, path and I/O failures are JSON only.
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(json.dumps({"status": "REJECT", "reason": reason,
                          "evidence_scope": SCOPE}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

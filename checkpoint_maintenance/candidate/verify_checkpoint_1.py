"""Read-only bounded checkpoint ZIP verification. Python 3.12, stdlib only."""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
import zipfile

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_MEMBERS = 4096
MAX_TOTAL = 64 * 1024 * 1024
MAX_MEMBER = 24 * 1024 * 1024
MAX_MANIFEST = 1024 * 1024
CHUNK = 64 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")


class Rejected(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Rejected(reason)


def hash_string(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def safe_name(name):
    require(type(name) is str and bool(name), "EMPTY_MEMBER_NAME")
    require("\\" not in name and "\x00" not in name, "UNSAFE_MEMBER_NAME")
    require(not name.startswith("/"), "ABSOLUTE_MEMBER_NAME")
    parts = name.split("/")
    require(all(p not in ("", ".", "..") for p in parts), "UNSAFE_PATH_COMPONENT")
    require(not re.match(r"^[A-Za-z]:", name), "WINDOWS_DRIVE_PREFIX")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(value):
    raise Rejected("NONSTANDARD_JSON_CONSTANT")


def manifest_schema(raw):
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)
    require(type(data) is dict, "MANIFEST_OBJECT_REQUIRED")
    for name, entry in data.items():
        safe_name(name)
        require(name != "MANIFEST.json", "MANIFEST_SELF_REFERENCE")
        require(type(entry) is dict and set(entry) == {"sha256", "size"},
                "MANIFEST_ENTRY_SCHEMA")
        require(hash_string(entry["sha256"]), "MANIFEST_HASH")
        require(type(entry["size"]) is int and 0 <= entry["size"] <= MAX_MEMBER,
                "MANIFEST_SIZE")
    return data


def verify(path, expected):
    require(hash_string(expected), "EXPECTED_SHA256_FORMAT")
    # Nonblocking open permits descriptor checks without waiting for a FIFO
    # writer on Unix. It does not establish a general regular-file I/O deadline.
    def readonly_opener(name, flags):
        return os.open(name, flags | getattr(os, "O_NONBLOCK", 0))

    # Keep a single read-only descriptor for outer hashing and ZIP reading.
    # Unbuffered reads avoid extra input read-ahead beyond the counted request.
    with open(path, "rb", buffering=0, opener=readonly_opener) as archive:
        metadata = os.fstat(archive.fileno())
        require(stat.S_ISREG(metadata.st_mode), "NONREGULAR_ARCHIVE")
        require(metadata.st_size <= MAX_ARCHIVE, "ARCHIVE_SIZE_LIMIT")
        outer = hashlib.sha256()
        outer_bytes = 0
        while True:
            chunk = archive.read(min(CHUNK, MAX_ARCHIVE - outer_bytes + 1))
            if not chunk:
                break
            outer_bytes += len(chunk)
            require(outer_bytes <= MAX_ARCHIVE, "ARCHIVE_SIZE_LIMIT")
            outer.update(chunk)
        outer_sha = outer.hexdigest()
        require(outer_sha == expected, "OUTER_SHA256_MISMATCH")
        archive.seek(0)
        with zipfile.ZipFile(archive, "r") as zf:
            infos = zf.infolist()
            require(len(infos) <= MAX_MEMBERS, "MEMBER_COUNT_LIMIT")
            members = {}
            declared_total = 0
            for info in infos:
                # ZipInfo may truncate a raw filename at a NUL; reject that alias.
                require(info.orig_filename == info.filename, "MEMBER_NAME_ALIAS")
                name = info.filename
                safe_name(name)
                require(name not in members, "DUPLICATE_MEMBER")
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                require(kind in (0, stat.S_IFREG), "NONREGULAR_MEMBER")
                require(not info.is_dir() and not (info.external_attr & 0x10),
                        "DIRECTORY_MEMBER")
                cap = MAX_MANIFEST if name == "MANIFEST.json" else MAX_MEMBER
                require(0 <= info.file_size <= cap, "DECLARED_MEMBER_LIMIT")
                declared_total += info.file_size
                require(declared_total <= MAX_TOTAL, "DECLARED_TOTAL_LIMIT")
                members[name] = info
            require("MANIFEST.json" in members, "MISSING_MANIFEST")
            total = 0

            def read_member(info, keep=False):
                nonlocal total
                cap = MAX_MANIFEST if info.filename == "MANIFEST.json" else MAX_MEMBER
                size = 0
                sha = hashlib.sha256()
                retained = bytearray() if keep else None
                with zf.open(info, "r") as stream:
                    while True:
                        chunk = stream.read(CHUNK)
                        if not chunk:
                            break
                        size += len(chunk)
                        total += len(chunk)
                        require(size <= cap, "ACTUAL_MEMBER_LIMIT")
                        require(total <= MAX_TOTAL, "ACTUAL_TOTAL_LIMIT")
                        sha.update(chunk)
                        if keep:
                            retained.extend(chunk)
                require(size == info.file_size, "DECLARED_ACTUAL_SIZE_MISMATCH")
                return size, sha.hexdigest(), retained

            _, _, raw_manifest = read_member(members["MANIFEST.json"], True)
            manifest = manifest_schema(raw_manifest)
            require(set(manifest) == set(members) - {"MANIFEST.json"},
                    "EXACT_INVENTORY_REQUIRED")
            for name, entry in manifest.items():
                require(members[name].file_size == entry["size"], "MANIFEST_DECLARED_SIZE")
                size, sha, _ = read_member(members[name])
                require(size == entry["size"], "PAYLOAD_SIZE_MISMATCH")
                require(sha == entry["sha256"], "PAYLOAD_SHA256_MISMATCH")
            require(total == declared_total, "TOTAL_SIZE_MISMATCH")
    return {"status": "PASS", "outer_sha256": outer_sha,
            "payload_files": len(manifest), "total_uncompressed_bytes": total,
            "evidence_scope": "INTEGRITY_ONLY"}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Rejected("CLI_ARGUMENTS: " + message)


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("zip_path")
        parser.add_argument("--expected-sha256", required=True)
        args = parser.parse_args(argv)
        result = verify(args.zip_path, args.expected_sha256)
    except Exception as exc:
        reason = str(exc) if isinstance(exc, Rejected) else type(exc).__name__
        print(json.dumps({"status": "REJECT", "reason": reason,
                          "evidence_scope": "INTEGRITY_ONLY"}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

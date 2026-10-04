#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import stat
import zipfile


def sha(b): return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("--expected-zip-sha256")
    a = ap.parse_args()
    zpath = pathlib.Path(a.archive)
    digest = sha(zpath.read_bytes())
    if a.expected_zip_sha256 and digest != a.expected_zip_sha256:
        raise SystemExit("OUTER_SHA256_MISMATCH")
    with zipfile.ZipFile(zpath) as z:
        infos = z.infolist()
        names = [x.filename for x in infos]
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise SystemExit("ZIP_CRC_OR_DUPLICATE_FAILURE")
        for info in infos:
            p = pathlib.PurePosixPath(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if p.is_absolute() or ".." in p.parts or mode == stat.S_IFLNK:
                raise SystemExit("UNSAFE_MEMBER:" + info.filename)
        if "SOURCE_MANIFEST.json" not in names:
            raise SystemExit("SOURCE_MANIFEST_MISSING")
        manifest = json.loads(z.read("SOURCE_MANIFEST.json"))
        if set(names) != set(manifest) | {"SOURCE_MANIFEST.json"}:
            raise SystemExit("ZIP_INVENTORY_MISMATCH")
        for name, expected in manifest.items():
            if sha(z.read(name)) != expected:
                raise SystemExit("MEMBER_SHA256_MISMATCH:" + name)
    print("PASS219_ETCD_PACKAGE_VERIFY_PASS", digest)


if __name__ == "__main__":
    main()

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("gate_version") != "BRAINS10-PASS184-STRICT-BLIND-REVIEW-v1":
        raise SystemExit("VERIFY_GATE_FAIL: version")
    files = manifest.get("subject_files")
    if type(files) is not dict or len(files) != 9:
        raise SystemExit("VERIFY_GATE_FAIL: manifest")
    for name, expected in sorted(files.items()):
        if type(name) is not str or type(expected) is not str or len(expected) != 64:
            raise SystemExit("VERIFY_GATE_FAIL: manifest field")
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            raise SystemExit(f"VERIFY_GATE_FAIL: {name}")
    print("VERIFY_GATE_PASS")


if __name__ == "__main__":
    main()

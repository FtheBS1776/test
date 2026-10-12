"""Read the synthetic Phase 2A trial without advancing or repairing it."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3


TRIAL = Path(__file__).resolve().parent / "trial"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _database(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = [row[0] for row in connection.execute(
            "select name from sqlite_master "
            "where type='table' and name not like 'sqlite_%' order by name")]
        result = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = connection.execute("select * from " + quoted).fetchall()
            result[table] = [dict(row) for row in rows]
        return result
    finally:
        connection.close()


def snapshot():
    files = [path for path in TRIAL.rglob("*") if path.is_file()]
    owned = TRIAL / "work"
    return {
        "input_sha256": _sha256(TRIAL / "INPUT.md"),
        "policy": json.loads((TRIAL / "POLICY.json").read_text(encoding="utf-8")),
        "plan": json.loads((TRIAL / "PLAN.json").read_text(encoding="utf-8")),
        "registry": json.loads((TRIAL / "REGISTRY.json").read_text(encoding="utf-8")),
        "owned_files": [
            path.relative_to(owned).as_posix()
            for path in sorted(owned.rglob("*")) if path.is_file()
        ],
        "files": {
            path.relative_to(TRIAL).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(files)
        },
        "databases": {
            path.relative_to(TRIAL).as_posix(): _database(path)
            for path in sorted(files) if path.suffix == ".sqlite"
        },
    }


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2, sort_keys=True, ensure_ascii=True))

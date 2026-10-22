"""Installed CLI startup storage failures, atomic migration and repair/retry."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_startup_review.py /path/to/runtime-guard-mcp")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="runtime-guard-startup-") as temporary:
        root = Path(temporary)
        config = root / "config.json"
        env = {key: value for key, value in os.environ.items() if not key.startswith("RUNTIME_GUARD_") and key not in ("PYTHONPATH", "PYTHONHOME")}

        def launch(path):
            config.write_text(json.dumps({"workspace_root": str(root), "audit_db": str(path)}))
            return subprocess.run([executable, "--config", str(config)], input=b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n', capture_output=True, cwd=root, env=env, timeout=8)

        def rejected(result):
            assert result.returncode == 2 and result.stdout == b""
            assert b"Cannot initialize Runtime Guard" in result.stderr
            assert b"Traceback" not in result.stderr
            assert b"synthetic-private-marker" not in result.stderr

        corrupt = root / "synthetic-private-marker-corrupt.sqlite"
        corrupt.write_bytes(b"not SQLite")
        rejected(launch(corrupt))
        directory = root / "synthetic-private-marker-directory"
        directory.mkdir()
        rejected(launch(directory))
        locked = root / "locked.sqlite"
        assert launch(locked).returncode == 0
        holder = sqlite3.connect(locked)
        try:
            holder.execute("BEGIN IMMEDIATE")
            rejected(launch(locked))
        finally:
            holder.close()
        assert launch(locked).returncode == 0

        legacy = root / "legacy.sqlite"
        connection = sqlite3.connect(legacy, timeout=0.25)
        try:
            connection.execute("CREATE TABLE decisions (time_utc INTEGER NOT NULL, caller_hash TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, rule TEXT NOT NULL)")
            connection.executemany("INSERT INTO decisions VALUES (?, ?, ?, ?, ?)", [(index, "fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND") for index in (1, 2)])
            connection.execute("CREATE TRIGGER refuse_second_update BEFORE UPDATE ON decisions WHEN OLD.rowid=2 BEGIN SELECT RAISE(ABORT, 'synthetic-private-marker'); END")
            connection.commit()
            original = connection.execute("SELECT * FROM decisions").fetchall()
            rejected(launch(legacy))
            assert len(list(connection.execute("PRAGMA table_info(decisions)"))) == 5
            assert connection.execute("SELECT * FROM decisions").fetchall() == original
            connection.execute("DROP TRIGGER refuse_second_update")
            connection.commit()
            assert launch(legacy).returncode == 0
            assert len(list(connection.execute("PRAGMA table_info(decisions)"))) == 7
            assert connection.execute("SELECT COUNT(*) FROM decisions WHERE prev_hash IS NOT NULL AND content_hash IS NOT NULL").fetchone()[0] == 2
        finally:
            connection.close()
    print("PASS: installed startup rejects corrupt/directory/busy audit storage without diagnostics; failed migration rolls back and repair/retry succeeds")


if __name__ == "__main__":
    main()

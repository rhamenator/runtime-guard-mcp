"""Audit startup is atomic and storage failures never expose their diagnostics."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from runtime_guard_mcp.audit import AuditLog


class AuditStartupTests(unittest.TestCase):
    def test_failed_legacy_migration_rolls_back_schema_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "audit.sqlite")
            connection = sqlite3.connect(path, timeout=0.25)
            try:
                connection.execute("CREATE TABLE decisions (time_utc INTEGER NOT NULL, caller_hash TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, rule TEXT NOT NULL)")
                connection.executemany("INSERT INTO decisions VALUES (?, ?, ?, ?, ?)", [(index, "fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND") for index in (1, 2)])
                connection.execute("CREATE TRIGGER refuse_second_update BEFORE UPDATE ON decisions WHEN OLD.rowid=2 BEGIN SELECT RAISE(ABORT, 'synthetic-private-marker'); END")
                connection.commit()
                before = connection.execute("SELECT * FROM decisions").fetchall()
                with self.assertRaises(sqlite3.IntegrityError):
                    AuditLog(path)
                self.assertEqual([row[1] for row in connection.execute("PRAGMA table_info(decisions)")], ["time_utc", "caller_hash", "tool", "status", "rule"])
                self.assertEqual(connection.execute("SELECT * FROM decisions").fetchall(), before)
                # A separate connection must immediately be able to repair/retry.
                connection.execute("DROP TRIGGER refuse_second_update")
                connection.commit()
                recovered = AuditLog(path)
                try:
                    self.assertEqual(recovered.verify_integrity()["records_checked"], 2)
                finally:
                    recovered._db.close()
            finally:
                connection.close()

    def test_startup_storage_errors_are_controlled_and_nonreflective(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            corrupt = root / "synthetic-private-marker.sqlite"
            corrupt.write_bytes(b"not a SQLite database")
            directory = root / "synthetic-private-marker-directory"
            directory.mkdir()
            locked = root / "locked.sqlite"
            initial = AuditLog(str(locked))
            initial._db.close()
            holder = sqlite3.connect(locked)
            try:
                holder.execute("BEGIN IMMEDIATE")
                for path in (corrupt, directory, locked):
                    config = root / "config.json"
                    config.write_text(json.dumps({"workspace_root": str(root), "audit_db": str(path)}))
                    process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server", "--config", str(config)], input=b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n', capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=5)
                    self.assertEqual(process.returncode, 2)
                    self.assertEqual(process.stdout, b"")
                    self.assertIn(b"Cannot initialize Runtime Guard", process.stderr)
                    self.assertNotIn(b"Traceback", process.stderr)
                    self.assertNotIn(b"synthetic-private-marker", process.stderr)
            finally:
                holder.close()

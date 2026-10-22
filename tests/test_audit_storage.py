"""Exercise real SQLite write contention and SQLITE_FULL, without filling the host disk."""
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from runtime_guard_mcp.server import RuntimeGuard


class AuditStorageTests(unittest.TestCase):
    def test_busy_audit_fails_closed_and_recovers(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "audit.sqlite")
            guard = RuntimeGuard(root, audit_db=path)
            holder = sqlite3.connect(path)
            try:
                holder.execute("BEGIN IMMEDIATE")
                started = time.monotonic()
                result = guard.call("dry_run_command", {"command": "git status"}, "fixture")
                elapsed = time.monotonic() - started
                self.assertEqual(result["structuredContent"]["rule"], "AUDIT_UNAVAILABLE")
                self.assertTrue(result["isError"])
                self.assertLess(elapsed, 2.0)
                self.assertNotIn("READ_ONLY_COMMAND", result["content"][0]["text"])
                holder.rollback()
                recovered = guard.call("dry_run_command", {"command": "git status"}, "fixture")
                self.assertFalse(recovered["isError"])
                self.assertEqual(guard.audit.verify_integrity(), {"valid": True, "records_checked": 1, "failed_rowid": None})
            finally:
                holder.close()
                guard.audit._db.close()

    def test_sqlite_full_fails_closed_then_restored_capacity_recovers(self):
        with tempfile.TemporaryDirectory() as root:
            guard = RuntimeGuard(root, audit_db=str(Path(root) / "audit.sqlite"))
            db = guard.audit._db
            try:
                pages = db.execute("PRAGMA page_count").fetchone()[0]
                self.assertEqual(db.execute(f"PRAGMA max_page_count={pages}").fetchone()[0], pages)
                full = False
                for _ in range(256):
                    try:
                        guard.audit.record("fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND")
                    except sqlite3.OperationalError as error:
                        self.assertEqual(error.sqlite_errorcode, sqlite3.SQLITE_FULL)
                        full = True
                        break
                self.assertTrue(full, "bounded fixture did not reach SQLITE_FULL")
                before = guard.audit.verify_integrity()
                self.assertTrue(before["valid"])
                blocked = guard.call("dry_run_command", {"command": "git status"}, "fixture")
                self.assertTrue(blocked["isError"])
                self.assertEqual(blocked["structuredContent"]["rule"], "AUDIT_UNAVAILABLE")
                self.assertNotIn("READ_ONLY_COMMAND", blocked["content"][0]["text"])
                self.assertEqual(guard.audit.verify_integrity(), before)
                db.execute(f"PRAGMA max_page_count={pages + 100}")
                recovered = guard.call("dry_run_command", {"command": "git status"}, "fixture")
                self.assertFalse(recovered["isError"])
                self.assertEqual(guard.audit.verify_integrity(), {"valid": True, "records_checked": before["records_checked"] + 1, "failed_rowid": None})
            finally:
                db.close()

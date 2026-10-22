import concurrent.futures
import sqlite3
import tempfile
import unittest
from pathlib import Path

from runtime_guard_mcp.audit import AuditCapacityError, AuditLog
from runtime_guard_mcp.server import RuntimeGuard


class AuditCapacityTests(unittest.TestCase):
    def test_record_capacity_is_atomic_under_concurrent_calls(self):
        with tempfile.TemporaryDirectory() as root:
            guard = RuntimeGuard(root, audit_db=str(Path(root) / "audit.sqlite"), audit_max_records=3)
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(lambda _: guard.call("dry_run_command", {"command": "git status"}, "fixture"), range(16)))
                rules = [result["structuredContent"]["rule"] for result in results]
                self.assertEqual(rules.count("READ_ONLY_COMMAND"), 3)
                self.assertEqual(rules.count("AUDIT_CAPACITY"), 13)
                self.assertEqual(guard.audit.verify_integrity(), {"valid": True, "records_checked": 3, "failed_rowid": None})
                for result in results:
                    if result["isError"]:
                        self.assertNotIn("READ_ONLY_COMMAND", result["content"][0]["text"])
            finally:
                guard.audit._db.close()

    def test_restart_and_backup_preserve_full_chain(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "audit.sqlite")
            audit = AuditLog(path, max_records=2)
            audit.record("fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND")
            audit.record("fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND")
            tip = audit._tip
            audit._db.close()
            reopened = AuditLog(path, max_records=2)
            try:
                with self.assertRaises(AuditCapacityError):
                    reopened.record("fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND")
                self.assertEqual(reopened._tip, tip)
                archive = str(Path(root) / "archive.sqlite")
                with sqlite3.connect(archive) as destination:
                    reopened._db.backup(destination)
                destination.close()
            finally:
                reopened._db.close()
            archived = AuditLog(archive, max_records=1)
            try:
                self.assertEqual(archived.verify_integrity()["records_checked"], 2)
                with self.assertRaises(AuditCapacityError):
                    archived.record("fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND")
            finally:
                archived._db.close()
            fresh = AuditLog(str(Path(root) / "fresh.sqlite"), max_records=2)
            try:
                fresh.record("fixture", "dry_run_command", "SAFE", "READ_ONLY_COMMAND")
                self.assertEqual(fresh.verify_integrity()["records_checked"], 1)
            finally:
                fresh._db.close()

    def test_invalid_limits_rejected(self):
        for value in (0, -1, True, 1.5, "2", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AuditLog(":memory:", max_records=value)

"""Regression for Python memory growth while opening/verifying long audit chains."""
import sqlite3
import tempfile
import tracemalloc
import unittest
from pathlib import Path

from runtime_guard_mcp.audit import AuditIntegrityError, AuditLog


class AuditMemoryTests(unittest.TestCase):
    def test_large_chain_scan_memory_and_late_corruption(self):
        count = 12000
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "audit.sqlite")
            initial = AuditLog(path)
            initial._db.close()

            def records():
                previous = "0" * 64
                for index in range(count):
                    current = AuditLog._hash(previous, index, "synthetic-caller", "budget_guard", "SAFE", "WITHIN_BUDGET")
                    yield index, "synthetic-caller", "budget_guard", "SAFE", "WITHIN_BUDGET", previous, current
                    previous = current

            with sqlite3.connect(path) as seed:
                seed.executemany("INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)", records())
            seed.close()
            # The ceiling covers Python allocations, not SQLite/native cache or RSS.
            # A materialized 12k-row chain exceeds it by several MiB.
            tracemalloc.start()
            try:
                opened = AuditLog(path)
                _, startup_peak = tracemalloc.get_traced_memory()
                tracemalloc.reset_peak()
                result = opened.verify_integrity()
                _, verify_peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(result, {"valid": True, "records_checked": count, "failed_rowid": None})
            self.assertLess(startup_peak, 1024 * 1024)
            self.assertLess(verify_peak, 1024 * 1024)
            opened._db.execute("UPDATE decisions SET rule = 'CORRUPTED' WHERE rowid = ?", (count,))
            opened._db.commit()
            self.assertEqual(opened.verify_integrity(), {"valid": False, "records_checked": count - 1, "failed_rowid": count})
            opened._db.close()
            with self.assertRaises(AuditIntegrityError):
                AuditLog(path)

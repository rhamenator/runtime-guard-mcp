"""SQLite affinity permits malformed stored values; audit errors stay controlled."""
from pathlib import Path
import sqlite3
import tempfile
import unittest
from runtime_guard_mcp.audit import AuditIntegrityError, AuditLog
from runtime_guard_mcp.server import RuntimeGuard


class AuditFieldTypesTests(unittest.TestCase):
    def test_blob_fields_fail_closed_and_repair_recovers(self):
        for column in ('time_utc', 'caller_hash', 'tool', 'status', 'rule'):
            with self.subTest(column=column), tempfile.TemporaryDirectory() as root:
                guard = RuntimeGuard(root, audit_db=str(Path(root) / 'audit.sqlite'))
                db = guard.audit._db
                try:
                    guard.call('dry_run_command', {'command': 'git status'}, 'fixture')
                    original = db.execute(f'SELECT {column} FROM decisions').fetchone()[0]
                    db.execute(f'UPDATE decisions SET {column}=?', (b'synthetic-private-marker',))
                    db.commit()
                    result = guard.call('dry_run_command', {'command': 'git status'}, 'fixture')
                    self.assertEqual(result['structuredContent']['rule'], 'AUDIT_UNAVAILABLE')
                    self.assertTrue(result['isError'])
                    self.assertNotIn('synthetic-private-marker', str(result))
                    self.assertFalse(guard.audit.verify_integrity()['valid'])
                    self.assertEqual(db.execute('SELECT count(*) FROM decisions').fetchone()[0], 1)
                    self.assertFalse(db.in_transaction)
                    db.execute(f'UPDATE decisions SET {column}=?', (original,))
                    db.commit()
                    self.assertFalse(guard.call('dry_run_command', {'command': 'git status'}, 'fixture')['isError'])
                    self.assertTrue(guard.audit.verify_integrity()['valid'])
                finally:
                    db.close()

    def test_invalid_stored_type_refuses_restart(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / 'audit.sqlite')
            audit = AuditLog(path)
            audit.record('fixture', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')
            audit._db.execute('UPDATE decisions SET time_utc=?', (b'private-marker',))
            audit._db.commit()
            audit._db.close()
            with self.assertRaises(AuditIntegrityError):
                AuditLog(path)

    def test_legacy_blob_backfill_rolls_back(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / 'audit.sqlite')
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE decisions (time_utc INTEGER, caller_hash TEXT, tool TEXT, status TEXT, rule TEXT)')
                db.execute('INSERT INTO decisions VALUES (?, ?, ?, ?, ?)', (1, 'fixture', 'tool', 'SAFE', b'private-marker'))
            with self.assertRaises(AuditIntegrityError):
                AuditLog(path)
            with sqlite3.connect(path) as db:
                self.assertEqual(len(list(db.execute('PRAGMA table_info(decisions)'))), 5)

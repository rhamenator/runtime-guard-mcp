import concurrent.futures
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from runtime_guard_mcp.audit import AuditLog, AuditWalCapacityError
from runtime_guard_mcp.server import RuntimeGuard


class AuditStorageLimitsTests(unittest.TestCase):
    def test_database_ceiling_preserves_rows_and_restart_requires_room(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / 'audit.sqlite')
            log = AuditLog(path, max_db_bytes=8192)
            try:
                for _ in range(100):
                    try:
                        log.record('caller', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')
                    except sqlite3.OperationalError as error:
                        self.assertEqual(error.sqlite_errorcode, sqlite3.SQLITE_FULL)
                        break
                else:
                    self.fail('real database ceiling never reached')
                self.assertLessEqual(log._db.execute('PRAGMA page_count').fetchone()[0] * log._db.execute('PRAGMA page_size').fetchone()[0], 8192)
                before = log.verify_integrity()
                self.assertTrue(before['valid'])
                self.assertGreater(before['records_checked'], 0)
            finally:
                log._db.close()
            recovered = AuditLog(path, max_db_bytes=16384)
            try:
                recovered.record('caller', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')
                self.assertEqual(recovered.verify_integrity()['records_checked'], before['records_checked'] + 1)
            finally:
                recovered._db.close()
            with self.assertRaises(ValueError):
                AuditLog(path, max_db_bytes=8192)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM decisions').fetchone()[0], before['records_checked'] + 1)

    def test_pinned_reader_concurrent_denial_then_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / 'audit.sqlite')
            log = AuditLog(path, wal_checkpoint_bytes=4096)
            log.record('caller', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')
            reader = sqlite3.connect(path)
            try:
                reader.execute('BEGIN')
                reader.execute('SELECT * FROM decisions').fetchall()
                size = Path(path + '-wal').stat().st_size
                def denied(_):
                    with self.assertRaises(AuditWalCapacityError):
                        log.record('caller', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(denied, range(4)))
                self.assertEqual(Path(path + '-wal').stat().st_size, size)
                self.assertEqual(log.verify_integrity()['records_checked'], 1)
                reader.rollback()
                def write(_):
                    log.record('caller', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(write, range(40)))
                self.assertEqual(log.verify_integrity(), {'valid': True, 'records_checked': 41, 'failed_rowid': None})
            finally:
                reader.close()
                log._db.close()

    def test_tool_denies_without_computed_result_and_recovers(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / 'audit.sqlite')
            guard = RuntimeGuard(root, audit_db=path, audit_wal_checkpoint_bytes=4096)
            guard.call('dry_run_command', {'command': 'git status'}, 'caller')
            reader = sqlite3.connect(path)
            try:
                reader.execute('BEGIN')
                reader.execute('SELECT * FROM decisions').fetchall()
                result = guard.call('dry_run_command', {'command': 'git status'}, 'caller')
                self.assertTrue(result['isError'])
                self.assertEqual(result['structuredContent']['rule'], 'AUDIT_WAL_CAPACITY')
                self.assertNotIn('READ_ONLY_COMMAND', result['content'][0]['text'])
                reader.rollback()
                self.assertFalse(guard.call('dry_run_command', {'command': 'git status'}, 'caller')['isError'])
            finally:
                reader.close()
                guard.audit._db.close()

    def test_storage_configuration_types(self):
        for values in ({'max_db_bytes': True}, {'max_db_bytes': 8191}, {'wal_checkpoint_bytes': False}, {'wal_checkpoint_bytes': 4095}):
            with self.assertRaises(ValueError):
                AuditLog(':memory:', **values)

    def test_wal_inspection_failure_is_controlled_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            guard = RuntimeGuard(root, audit_db=str(Path(root) / 'audit.sqlite'))
            try:
                with mock.patch('runtime_guard_mcp.audit.Path.stat', side_effect=PermissionError('synthetic-private-marker')):
                    result = guard.call('dry_run_command', {'command': 'git status'}, 'caller')
                self.assertTrue(result['isError'])
                self.assertEqual(result['structuredContent']['rule'], 'AUDIT_UNAVAILABLE')
                self.assertNotIn('synthetic-private-marker', str(result))
                self.assertEqual(guard.audit.verify_integrity()['records_checked'], 0)
                self.assertFalse(guard.call('dry_run_command', {'command': 'git status'}, 'caller')['isError'])
            finally:
                guard.audit._db.close()

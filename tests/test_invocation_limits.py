import concurrent.futures
import sqlite3
import tempfile
import unittest

from runtime_guard_mcp.policy import InvocationLimiter
from runtime_guard_mcp.server import RuntimeGuard


class InvocationTests(unittest.TestCase):
    def test_atomic_bounded_admission_and_recovery(self):
        now = [0.0]
        limiter = InvocationLimiter(17, lambda: now[0])
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(lambda _: limiter.admit(), range(100))), 17)
        now[0] = 59.999
        self.assertFalse(limiter.admit())
        now[0] = 60
        self.assertTrue(limiter.admit())
        self.assertEqual(limiter._count, 1)

    def test_shared_tools_callers_and_no_denied_effects(self):
        with tempfile.TemporaryDirectory() as root:
            guard = RuntimeGuard(root, audit_db=root + "/audit.sqlite", invocations_minute=1)
            first = guard.call('dry_run_command', {'command': 'pwd'}, 'a')
            self.assertFalse(first['isError'])
            cases = [('audit_path_access', {'path': 'x'}),
                     ('dry_run_command', {'command': 'pwd'}),
                     ('budget_guard', {'session_id': 'new', 'tokens': 100000, 'consume': True}),
                     ('secret_masker', {'session_id': 'new', 'stream_id': 'x', 'chunk': 'secret', 'final': False})]
            for name, args in cases:
                result = guard.call(name, args, 'different')
                self.assertTrue(result['isError'])
                self.assertEqual(result['structuredContent']['rule'], 'INVOCATION_RATE_LIMIT')
            with sqlite3.connect(root + "/audit.sqlite") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 1)
            guard.invocations._start -= 60
            result = guard.call('budget_guard', {'session_id': 'new', 'tokens': 100000, 'consume': True}, 'different')
            self.assertFalse(result['isError'])

    def test_invalid_requests_do_not_consume_admission(self):
        with tempfile.TemporaryDirectory() as root:
            guard = RuntimeGuard(root, invocations_minute=1)
            for params in [{'name': 'unknown'}, {'name': 'dry_run_command', 'arguments': {'command': 1}}]:
                self.assertIn('error', guard.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': params}))
            result = guard.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                   'params': {'name': 'dry_run_command', 'arguments': {'command': 'pwd'}}})
            self.assertFalse(result['result']['isError'])

    def test_invalid_limit(self):
        for value in [0, -1, True, 1.0]:
            with self.assertRaises(ValueError):
                InvocationLimiter(value)

import unittest
from runtime_guard_mcp.server import RuntimeGuard, valid_notification_meta, valid_tracestate

INVALID = [None, {}, True, 'a=', '=x', 'A=x', '1=x', 'a=x,a=y', 'a=x=y', 'a=x\ny',
           'a=x\ty', 'a=é', 'a.b=x', 'a @b=x', 'a@1=x', '@a=x', 'a@@b=x',
           'a' * 257 + '=x', 'a=' + 'x' * 257, 'a' * 242 + '@b=x', 'a@' + 'b' * 15 + '=x',
           ','.join('a'+str(i)+'=x' for i in range(33)), ' ' * 32769]


class TracestateTests(unittest.TestCase):
    def test_grammar_boundaries_and_notification_metadata(self):
        valid = ['', ' \t', ',,', ' \ta= x \t, b=Y', '1@system=x', 'a_-*/=X',
                 'a' * 256 + '=' + 'x' * 256, 'a' * 241 + '@' + 'b' * 14 + '=x',
                 ','.join('a'+str(i)+'=x' for i in range(32)), ' ' * 32768]
        for value in valid:
            self.assertTrue(valid_tracestate(value), repr(value[:40]))
            self.assertTrue(valid_notification_meta({'tracestate': value}))
        for value in INVALID:
            self.assertFalse(valid_tracestate(value), repr(value)[:80])
            self.assertFalse(valid_notification_meta({'tracestate': value}))

    def test_invalid_metadata_cannot_consume_budget(self):
        guard = RuntimeGuard('/tmp/work')
        for index, value in enumerate(INVALID):
            frame = {'jsonrpc': '2.0', 'id': index, 'method': 'tools/call', 'params': {
                '_meta': {'tracestate': value}, 'name': 'budget_guard', 'arguments': {
                    'session_id': 'state', 'commands': 1, 'consume': True}}}
            self.assertEqual(guard.handle(frame)['error'], {'code': -32602, 'message': 'Invalid tracestate metadata'})
        self.assertFalse(guard.call('budget_guard', {'session_id': 'state', 'commands': 120, 'consume': True}, 'local')['isError'])

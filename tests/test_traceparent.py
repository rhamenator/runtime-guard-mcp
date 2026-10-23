import unittest
from runtime_guard_mcp.server import RuntimeGuard, valid_notification_meta, valid_traceparent

VALID = '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INVALID = [None, {}, 1, True, '', VALID.upper(), 'ff' + VALID[2:], VALID + '-extra',
           VALID[:-1], VALID.replace('0af7651916cd43dd8448eb211c80319c', '0' * 32),
           VALID.replace('00f067aa0ba902b7', '0' * 16), VALID[:35] + '_' + VALID[36:],
           '01' + VALID[2:] + 'x', VALID[:-2] + 'gg', VALID[:-1] + 'é']


class TraceparentTests(unittest.TestCase):
    def test_wire_format_and_future_prefix(self):
        for value in [VALID, VALID[:-2] + 'ff', '01' + VALID[2:], '01' + VALID[2:] + '-future']:
            self.assertTrue(valid_traceparent(value), value)
            self.assertTrue(valid_notification_meta({'traceparent': value}))
        for value in INVALID:
            self.assertFalse(valid_traceparent(value), repr(value))
            self.assertFalse(valid_notification_meta({'traceparent': value}))

    def test_invalid_traceparent_cannot_consume_budget(self):
        guard = RuntimeGuard('/tmp/work')
        for i, value in enumerate(INVALID):
            frame = {'jsonrpc': '2.0', 'id': i, 'method': 'tools/call', 'params': {
                '_meta': {'traceparent': value}, 'name': 'budget_guard',
                'arguments': {'session_id': 'trace', 'commands': 1, 'consume': True}}}
            result = guard.handle(frame)
            self.assertEqual(result['error']['code'], -32602)
            self.assertEqual(result['error']['message'], 'Invalid traceparent metadata')
        result = guard.call('budget_guard', {'session_id': 'trace', 'commands': 120, 'consume': True}, 'local')
        self.assertFalse(result['isError'])

import unittest
from runtime_guard_mcp.server import RuntimeGuard, valid_baggage, valid_notification_meta

INVALID = [None, {}, True, '', ' ', '=x', 'bare', 'a=x,', ',a=x', 'a="x"', 'a=x\\y',
           'a=x y', 'a=é', 'a=%', 'a=%0', 'a=%xx', 'a=x;', 'a=x;=y', 'a=x;bad key',
           'a=x;property=%GG', 'a@b=x', 'a=x\ny', 'a=' + 'x' * 8191,
           ','.join('a=x' for _ in range(65))]


class BaggageTests(unittest.TestCase):
    def test_wire_grammar_boundaries_and_no_decoding(self):
        valid = ['a=', 'A=x,a=y', ' a = x ; bare ; property = =x ',
                 'a=%C3%A9%00%ff%25', 'a=x=y=z', 'a=x;property=;bare',
                 "!#$%&'*+-.^_`|~=x", 'a=' + 'x' * 8190, ','.join('a=x' for _ in range(64))]
        for value in valid:
            self.assertTrue(valid_baggage(value), value[:60])
            self.assertTrue(valid_notification_meta({'baggage': value}))
        for value in INVALID:
            self.assertFalse(valid_baggage(value), repr(value)[:60])
            self.assertFalse(valid_notification_meta({'baggage': value}))

    def test_invalid_baggage_cannot_consume_budget(self):
        guard = RuntimeGuard('/tmp/work')
        for identifier, value in enumerate(INVALID):
            frame = {'jsonrpc': '2.0', 'id': identifier, 'method': 'tools/call', 'params': {
                '_meta': {'baggage': value}, 'name': 'budget_guard', 'arguments': {
                    'session_id': 'baggage', 'commands': 1, 'consume': True}}}
            self.assertEqual(guard.handle(frame)['error'], {'code': -32602, 'message': 'Invalid baggage metadata'})
        self.assertFalse(guard.call('budget_guard', {'session_id': 'baggage', 'commands': 120, 'consume': True}, 'local')['isError'])

import importlib.util
from pathlib import Path
import sys
import threading
import time
from runtime_guard_mcp.server import StdioDispatcher, META_PREFIX, MODERN_VERSION
import unittest
from runtime_guard_mcp.policy import SecretMasker

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lifecycle_review', ROOT / 'scripts/legacy_lifecycle_review.py')
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


class ReviewFixTests(unittest.TestCase):
    def test_stdio_legacy_admission_and_modern_state_preservation(self):
        self.assertEqual(lifecycle.review([sys.executable, '-m', 'runtime_guard_mcp.server'], ROOT / 'src')['status'], 'PASS')

    def test_quoted_assignment_values_and_every_chunk_boundary(self):
        fixtures = [('"password":"SyntheticPass123!"', 'SyntheticPass123!'),
                    ('"API_KEY": "Synthetic value with spaces"', 'Synthetic value with spaces'),
                    ("'token': 'SyntheticPass123!'", 'SyntheticPass123!'),
                    ('password=SyntheticPass123!', 'SyntheticPass123!'),
                    ('"secret":"Synthetic\\"quoted value"', 'Synthetic\\"quoted value')]
        for assignment, secret in fixtures:
            text = '{' + assignment + ',"public":"keep"}'
            for split in range(len(text) + 1):
                with self.subTest(assignment=assignment, split=split):
                    masker = SecretMasker()
                    first = masker.mask('owner', 'session', 'stream', text[:split], False)
                    last = masker.mask('owner', 'session', 'stream', text[split:], True)
                    output = first['text'] + last['text']
                    self.assertNotIn(secret, output)
                    self.assertIn('[REDACTED_PASSWORD_ASSIGNMENT_1]', output)
                    self.assertIn('"public":"keep"', output)
                    again = masker.mask('owner', 'session', 'again', text, True)
                    self.assertEqual(output, again['text'])

    def test_nonsecret_json_and_short_values_remain_unchanged(self):
        text = '{"public":"keep","password":"short"}'
        self.assertEqual(SecretMasker().mask('owner', 's', 'x', text, True)['text'], text)

    def test_initialized_notification_is_silent_when_saturated(self):
        started, release = threading.Event(), threading.Event()
        replies = []
        class Guard:
            def handle(self, message, caller, modern_stdio=False):
                started.set()
                if not release.wait(2):
                    raise RuntimeError('fixture deadline')
                return {'jsonrpc': '2.0', 'id': message['id'], 'result': {}}
        dispatcher = StdioDispatcher(Guard(), replies.append, capacity=1)
        frame = lambda identifier: {'jsonrpc': '2.0', 'id': identifier, 'method': 'ping', 'params': {
            '_meta': {META_PREFIX + 'protocolVersion': MODERN_VERSION, META_PREFIX + 'clientCapabilities': {}}}}
        try:
            dispatcher.submit(frame(1))
            self.assertTrue(started.wait(1))
            dispatcher.submit({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            self.assertEqual(replies, [])
            self.assertEqual(dispatcher.legacy_phase, 'new')
            release.set()
            deadline = time.monotonic() + 2
            while dispatcher.queue.unfinished_tasks and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertEqual(dispatcher.queue.unfinished_tasks, 0)
            dispatcher.submit(frame(2))
            while dispatcher.queue.unfinished_tasks and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertEqual([reply['id'] for reply in replies], [1, 2])
        finally:
            release.set()
            dispatcher.close()

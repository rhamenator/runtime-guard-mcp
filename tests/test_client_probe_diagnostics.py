"""Failure hints must not turn arbitrary request IDs into rate-limit claims."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("probe_diagnostics", Path(__file__).parents[1] / "scripts/client_probe_diagnostics.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProbeDiagnosticsTests(unittest.TestCase):
    def test_random_identifier_is_not_a_limit(self):
        self.assertEqual(module.classify_limit('{"id":"a429b-uuid", "error":"failed"}'), "unknown")

    def test_rate_limit_indicators(self):
        for text in ('HTTP 429', '{"httpStatusCode":429}', 'rate_limit_exceeded'):
            self.assertEqual(module.classify_limit(text), "rate_limit")

    def test_quota_takes_precedence(self):
        self.assertEqual(module.classify_limit('HTTP 429 insufficient_quota'), "account_quota")

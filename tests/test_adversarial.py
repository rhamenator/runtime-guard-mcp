"""Synthetic adversarial inputs; no commands are executed or real secrets used."""

import concurrent.futures
import tempfile
import unittest

from runtime_guard_mcp.policy import BudgetState, SecretMasker, audit_path_access, dry_run_command
from runtime_guard_mcp.server import RuntimeGuard


class AdversarialPolicyTests(unittest.TestCase):
    def test_destructive_find_variants_never_safe(self):
        for command in ("find . -delete", "find . -exec rm {} \\;", "find . -exec sh -c 'touch /tmp/x' \\;"):
            with self.subTest(command=command):
                self.assertNotEqual(dry_run_command(command)["status"], "SAFE")

    def test_sensitive_virtual_paths_never_safe(self):
        for command in ("cat /proc/self/environ", "cat ~/.config/gcloud/application_default_credentials.json"):
            with self.subTest(command=command):
                self.assertNotEqual(dry_run_command(command)["status"], "SAFE")

    def test_path_edges(self):
        with tempfile.TemporaryDirectory() as root:
            for path in ("../../etc/shadow", "src/../.env.production", "\x00bad"):
                with self.subTest(path=repr(path)):
                    self.assertEqual(audit_path_access(path, root)["status"], "BLOCKED")

    def test_atomic_budget_reservations(self):
        state = BudgetState(token_hour=10, payload_hour=100, commands_minute=100)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(lambda _: state.check("caller", "session", 1, 0, 0, "", True)["status"], range(64)))
        self.assertEqual(results.count("SAFE"), 10)
        self.assertEqual(results.count("BLOCKED"), 54)

    def test_split_synthetic_secret_never_emitted_raw(self):
        token = "ghp_" + "A" * 24
        masker = SecretMasker()
        emitted = []
        for character in token:
            emitted.append(masker.mask("caller", "session", "stream", character, False)["text"])
        emitted.append(masker.mask("caller", "session", "stream", "", True)["text"])
        self.assertNotIn(token, "".join(emitted))
        self.assertIn("[REDACTED_GITHUB_TOKEN_1]", "".join(emitted))


class AdversarialProtocolTests(unittest.TestCase):
    def test_malformed_messages_have_controlled_results(self):
        guard = RuntimeGuard("/tmp")
        messages = [None, [], 1, "x", {}, {"jsonrpc": "1.0", "id": 1, "method": "ping"}, {"jsonrpc": "2.0", "id": True, "method": "ping"}, {"jsonrpc": "2.0", "id": {}, "method": "ping"}, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": []}, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "budget_guard", "arguments": {"session_id": "s", "tokens": "many"}}}]
        for message in messages:
            with self.subTest(message=repr(message)):
                result = guard.handle(message)
                self.assertIsInstance(result, dict)
                self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()

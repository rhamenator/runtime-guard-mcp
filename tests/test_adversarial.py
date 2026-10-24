"""Synthetic adversarial inputs; no commands are executed or real secrets used."""

import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime_guard_mcp.policy import BudgetState, SecretMasker, audit_path_access, dry_run_command
from runtime_guard_mcp.server import RuntimeGuard


class AdversarialPolicyTests(unittest.TestCase):
    def test_destructive_find_variants_never_safe(self):
        for command in ("find . -delete", "find . -exec rm {} \\;", "find . -exec sh -c 'touch /tmp/x' \\;"):
            with self.subTest(command=command):
                self.assertNotEqual(dry_run_command(command)["status"], "SAFE")
        self.assertEqual(dry_run_command("find . -exec rm -rf /tmp/example {} +")["status"], "BLOCKED")
        self.assertEqual(dry_run_command("find . -exec git push --force {} +")["status"], "BLOCKED")

    def test_read_oriented_commands_with_side_effect_options(self):
        commands = ("git diff --output=review.patch", "git log --output history.txt",
                    "find . -fprint names.txt", "find . -fprint0 names.bin",
                    "find . -fprintf names.txt %p", "find . -fls names.txt",
                    "rg --pre=formatter pattern .", "rg --pre formatter pattern .",
                    "rg --hostname-bin=hostname-helper pattern .")
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(dry_run_command(command)["status"], "NEEDS_CONFIRMATION")
        for command in ("git diff", "git log -1", "find . -print", "rg pattern ."):
            with self.subTest(command=command):
                self.assertEqual(dry_run_command(command)["status"], "SAFE")

    def test_shell_control_syntax_requires_review(self):
        # Classify strings only: none of these proposed commands are executed.
        for shell in ("bash", "sh", "pwsh"):
            for command in ("cat example.txt & touch marker.txt", "cat example.txt &",
                            "cat <(printf fixture)", "cat example.txt < input.txt",
                            "cat (helper)", "cat example.txt\rtouch marker.txt",
                            "cat 'literal&name'", "rg 'pattern(group)' ."):
                with self.subTest(shell=shell, command=command):
                    self.assertEqual(dry_run_command(command, shell)["status"], "NEEDS_CONFIRMATION")
            self.assertEqual(dry_run_command("cat example.txt", shell)["status"], "SAFE")

    def test_sensitive_virtual_paths_never_safe(self):
        for command in ("cat /proc/self/environ", "cat ~/.config/gcloud/application_default_credentials.json"):
            with self.subTest(command=command):
                self.assertNotEqual(dry_run_command(command)["status"], "SAFE")

    def test_path_edges(self):
        with tempfile.TemporaryDirectory() as root:
            for path in ("../../etc/shadow", "src/../.env.production", "\x00bad"):
                with self.subTest(path=repr(path)):
                    self.assertEqual(audit_path_access(path, root)["status"], "BLOCKED")

    def test_symlink_escapes_allowed_workspace(self):
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as outside:
            inside = Path(workspace) / "ordinary.txt"
            inside.touch()
            link = Path(workspace) / "escape"
            link.symlink_to(outside, target_is_directory=True)
            self.assertEqual(audit_path_access(str(inside), workspace)["status"], "SAFE")
            result = audit_path_access(str(link), workspace)
            self.assertEqual((result["status"], result["rule"]), ("BLOCKED", "OUTSIDE_WORKSPACE"))

    def test_atomic_budget_reservations(self):
        state = BudgetState(token_hour=10, payload_hour=100, commands_minute=100)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(lambda _: state.check("caller", "session", 1, 0, 0, "", True)["status"], range(64)))
        self.assertEqual(results.count("SAFE"), 10)
        self.assertEqual(results.count("BLOCKED"), 54)

    def test_budget_history_cap_blocks_without_partial_reservation(self):
        state = BudgetState(token_hour=100, payload_hour=100, commands_minute=100, max_events_per_metric=2)
        for _ in range(2):
            self.assertEqual(state.check("caller", "session", 1, 0, 0, "", True)["status"], "SAFE")
        result = state.check("caller", "session", 1, 1, 0, "", True)
        self.assertEqual((result["status"], result["rule"]), ("BLOCKED", "BUDGET_STATE_LIMIT"))
        self.assertEqual(len(state._events[("caller", "payload")]), 0)

    def test_budget_history_cap_is_atomic_and_expires(self):
        state = BudgetState(token_hour=100, max_events_per_metric=10)
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            outcomes = list(pool.map(lambda _: state.check("caller", "session", 1, 0, 0, "", True)["status"], range(32)))
        self.assertEqual((outcomes.count("SAFE"), outcomes.count("BLOCKED")), (10, 22))
        self.assertEqual(len(state._events[("caller", "tokens")]), 10)
        with patch("runtime_guard_mcp.policy.time.monotonic", return_value=state._events[("caller", "tokens")][-1][0] + 3601):
            self.assertEqual(state.check("caller", "session", 1, 0, 0, "", True)["status"], "SAFE")
        self.assertEqual(len(state._events[("caller", "tokens")]), 1)

    def test_fingerprint_history_cap_expires_across_sessions(self):
        state = BudgetState(max_fingerprint_events=2)
        with patch("runtime_guard_mcp.policy.time.monotonic", side_effect=[100.0, 101.0, 102.0, 402.0]):
            self.assertEqual(state.check("caller", "one", 0, 0, 0, "a", True)["status"], "SAFE")
            self.assertEqual(state.check("caller", "two", 0, 0, 0, "b", True)["status"], "SAFE")
            result = state.check("caller", "three", 0, 0, 0, "c", True)
            self.assertEqual(result["rule"], "FINGERPRINT_STATE_LIMIT")
            self.assertEqual(len(state._fingerprint_order), 2)
            self.assertEqual(state.check("caller", "three", 0, 0, 0, "c", True)["status"], "SAFE")
            self.assertEqual(len(state._fingerprint_order), 1)
            self.assertEqual(len(state._fingerprints), 1)

    def test_split_synthetic_secret_never_emitted_raw(self):
        token = "ghp_" + "A" * 24
        masker = SecretMasker()
        emitted = []
        for character in token:
            emitted.append(masker.mask("caller", "session", "stream", character, False)["text"])
        emitted.append(masker.mask("caller", "session", "stream", "", True)["text"])
        self.assertNotIn(token, "".join(emitted))
        self.assertIn("[REDACTED_GITHUB_TOKEN_1]", "".join(emitted))

    def test_masker_limits_active_streams_and_recovers_after_final(self):
        masker = SecretMasker(max_streams=2)
        for stream in ("one", "two"):
            self.assertEqual(masker.mask("caller", "session", stream, "", False)["status"], "SAFE")
        self.assertEqual(masker.mask("caller", "session", "three", "", False)["rule"], "STREAM_LIMIT")
        self.assertEqual(masker.mask("caller", "session", "one", "", True)["status"], "SAFE")
        self.assertEqual(masker.mask("caller", "session", "three", "", False)["status"], "SAFE")

    def test_masker_secret_limit_fails_closed(self):
        masker = SecretMasker(max_secrets_per_caller=1)
        first = "ghp_" + "A" * 24
        second = "ghp_" + "B" * 24
        result = masker.mask("caller", "session", "one", first, True)
        self.assertIn("[REDACTED_GITHUB_TOKEN_1]", result["text"])
        result = masker.mask("caller", "session", "two", second, True)
        self.assertEqual((result["status"], result["rule"]), ("BLOCKED", "SECRET_STATE_LIMIT"))
        self.assertNotIn("text", result)
        self.assertIn("[REDACTED_GITHUB_TOKEN_1]", masker.mask("caller", "session", "three", first, True)["text"])
        result = masker.mask("caller", "session", "split", second + " " + "x" * 16384, False)
        self.assertEqual((result["status"], result["rule"]), ("BLOCKED", "SECRET_STATE_LIMIT"))
        self.assertEqual(masker.mask("caller", "session", "split", "tail", False)["rule"], "STREAM_RESET_REQUIRED")
        self.assertEqual(masker.mask("caller", "session", "split", "", True)["rule"], "STREAM_RESET_REQUIRED")

    def test_masker_invalid_unicode_returns_controlled_block(self):
        result = SecretMasker().mask("caller", "session", "stream", "password=abcdefgh\ud800", True)
        self.assertEqual((result["status"], result["rule"]), ("BLOCKED", "INVALID_UNICODE"))


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

import os
import sqlite3
import tempfile
import unittest
import json
from pathlib import Path

from runtime_guard_mcp.audit import AuditIntegrityError, AuditLog
from runtime_guard_mcp.policy import BudgetState, SecretMasker, audit_path_access, dry_run_command
from runtime_guard_mcp.server import RuntimeGuard


class PathTests(unittest.TestCase):
    def test_containment_and_sensitive_paths(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(audit_path_access("src/main.py", root)["status"], "SAFE")
            self.assertEqual(audit_path_access("../outside", root)["rule"], "OUTSIDE_WORKSPACE")
            self.assertEqual(audit_path_access(".env", root)["rule"], "SENSITIVE_PATH")
            self.assertEqual(audit_path_access(".env.production", root)["rule"], "SENSITIVE_PATH")
            self.assertEqual(audit_path_access("file", root, "delete")["status"], "NEEDS_CONFIRMATION")
            outside = Path(root).parent / "outside-for-runtime-guard-test"
            (Path(root) / "link").symlink_to(outside)
            self.assertEqual(audit_path_access("link/file", root)["rule"], "OUTSIDE_WORKSPACE")
            self.assertEqual(audit_path_access(str(outside / "file"), root, allowed_roots=[str(outside)])["status"], "SAFE")


class ShellTests(unittest.TestCase):
    def test_command_risk(self):
        self.assertEqual(dry_run_command("git status")["status"], "SAFE")
        self.assertEqual(dry_run_command("rm -rf /tmp/test")["rule"], "RECURSIVE_DELETE")
        self.assertEqual(dry_run_command("git push origin main --force-with-lease")["rule"], "FORCE_PUSH")
        self.assertEqual(dry_run_command("git -C repo push origin main --force")["rule"], "FORCE_PUSH")
        self.assertEqual(dry_run_command("Remove-Item -Recurse -Force C:\\Temp", "pwsh")["rule"], "RECURSIVE_DELETE")
        self.assertEqual(dry_run_command("pwsh -Command Remove-Item foo", "pwsh")["status"], "NEEDS_CONFIRMATION")
        self.assertEqual(dry_run_command("cat file | bash")["status"], "NEEDS_CONFIRMATION")
        self.assertEqual(dry_run_command("cat /etc/shadow")["rule"], "SENSITIVE_PATH")
        self.assertEqual(dry_run_command("cat ~/.ssh/id_ed25519")["rule"], "SENSITIVE_PATH")


class BudgetTests(unittest.TestCase):
    def test_budget_and_loop(self):
        budget = BudgetState(token_hour=10, payload_hour=100, commands_minute=10)
        self.assertEqual(budget.check("caller", "s", 9, 0, 0, "", True)["status"], "SAFE")
        self.assertEqual(budget.check("caller", "other-session", 2, 0, 0, "", True)["rule"], "TOKENS_BUDGET")
        for _ in range(5):
            self.assertEqual(budget.check("caller", "s", 0, 0, 0, "same", True)["status"], "SAFE")
        self.assertEqual(budget.check("caller", "s", 0, 0, 0, "same", True)["rule"], "REPEATED_LOOP")


class MaskTests(unittest.TestCase):
    def test_chunked_token_and_stable_placeholder(self):
        masker = SecretMasker()
        token = "ghp_" + "A" * 24
        first = masker.mask("caller", "s", "stream", "before " + token[:12], False)
        second = masker.mask("caller", "s", "stream", token[12:] + " after", True)
        self.assertEqual(first["text"], "")
        self.assertNotIn(token, second["text"])
        self.assertIn("[REDACTED_GITHUB_TOKEN_1]", second["text"])
        again = masker.mask("caller", "s", "stream2", token, True)
        self.assertEqual(again["text"], "[REDACTED_GITHUB_TOKEN_1]")

    def test_large_chunk_holds_tail(self):
        masker = SecretMasker()
        token = "AKIA" + "A" * 16
        first = masker.mask("caller", "s", "x", "x" * 20000 + token[:8], False)
        second = masker.mask("caller", "s", "x", token[8:], True)
        self.assertNotIn("AKIA", first["text"])
        self.assertIn("[REDACTED_AWS_ACCESS_KEY_1]", second["text"][-100:])

    def test_private_identifiers(self):
        masker = SecretMasker()
        result = masker.mask("caller", "s", "x", "Reach a.person@example.com or 123-45-6789", True)
        self.assertNotIn("a.person@example.com", result["text"])
        self.assertNotIn("123-45-6789", result["text"])
        self.assertIn("[REDACTED_EMAIL_ADDRESS_1]", result["text"])
        self.assertIn("[REDACTED_US_SSN_1]", result["text"])


class AuditTests(unittest.TestCase):
    def test_redacted_audit(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "audit.sqlite3")
            guard = RuntimeGuard(root, audit_db=db)
            guard.call("dry_run_command", {"command": "git status"}, "caller")
            with sqlite3.connect(db) as connection:
                row = connection.execute("SELECT caller_hash, tool, status, rule FROM decisions").fetchone()
            self.assertEqual(row[1:], ("dry_run_command", "SAFE", "READ_ONLY_COMMAND"))
            self.assertNotIn("caller", row[0])
            self.assertTrue(guard.audit.verify_integrity()["valid"])

    def test_audit_detects_mutation_and_interior_deletion(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "audit.sqlite3")
            guard = RuntimeGuard(root, audit_db=db)
            for command in ("git status", "git diff", "git log"):
                guard.call("dry_run_command", {"command": command}, "caller")
            self.assertTrue(guard.audit.verify_integrity()["valid"])
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE decisions SET rule='altered' WHERE rowid=2")
            self.assertFalse(guard.audit.verify_integrity()["valid"])
            with sqlite3.connect(db) as connection:
                connection.execute("DELETE FROM decisions WHERE rowid=2")
            self.assertFalse(guard.audit.verify_integrity()["valid"])

    def test_legacy_audit_migrates(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "audit.sqlite3")
            with sqlite3.connect(db) as connection:
                connection.execute("CREATE TABLE decisions (time_utc INTEGER NOT NULL, caller_hash TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, rule TEXT NOT NULL)")
                connection.execute("INSERT INTO decisions VALUES (1, 'caller-hash', 'dry_run_command', 'SAFE', 'READ_ONLY_COMMAND')")
            guard = RuntimeGuard(root, audit_db=db)
            self.assertTrue(guard.audit.verify_integrity()["valid"])
            guard.call("dry_run_command", {"command": "git status"}, "caller")
            self.assertEqual(guard.audit.verify_integrity()["records_checked"], 2)

    def test_tampered_audit_refuses_restart_and_new_decisions(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "audit.sqlite3")
            guard = RuntimeGuard(root, audit_db=db)
            guard.call("dry_run_command", {"command": "git status"}, "caller")
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE decisions SET rule='altered' WHERE rowid=1")
            response = guard.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "dry_run_command", "arguments": {"command": "git diff"}}})
            self.assertEqual((response["result"]["structuredContent"]["status"], response["result"]["structuredContent"]["rule"]), ("BLOCKED", "AUDIT_UNAVAILABLE"))
            with self.assertRaises(AuditIntegrityError):
                AuditLog(db)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 1)

    def test_audit_storage_failure_never_returns_masked_result(self):
        with tempfile.TemporaryDirectory() as root:
            guard = RuntimeGuard(root, audit_db=os.path.join(root, "audit.sqlite3"))
            guard.audit._db.close()
            synthetic = "ghp_" + "A" * 24
            response = guard.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "secret_masker", "arguments": {"session_id": "s", "stream_id": "x", "chunk": synthetic, "final": True}}})
            self.assertEqual((response["result"]["structuredContent"]["status"], response["result"]["structuredContent"]["rule"]), ("BLOCKED", "AUDIT_UNAVAILABLE"))
            self.assertNotIn(synthetic, json.dumps(response))


if __name__ == "__main__":
    unittest.main()

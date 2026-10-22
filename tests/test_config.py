"""Startup configuration rejects ambiguous or unbounded input before serving."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime_guard_mcp.server import MAX_MESSAGE


class ConfigTests(unittest.TestCase):
    def test_invalid_config_is_controlled_and_does_not_echo_input(self):
        cases = (
            b'{"token_hour":1,"token_hour":999,"private":"synthetic-marker"}',
            b'{"token_hour":NaN}', b'\xff', b'{', b'x' * (MAX_MESSAGE + 1), None,
        )
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'config.json'
            for raw in cases:
                with self.subTest(size=len(raw) if raw is not None else None):
                    if raw is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(raw)
                    result = subprocess.run([sys.executable, '-m', 'runtime_guard_mcp.server', '--config', str(path)], input=b'', capture_output=True, env=dict(os.environ, PYTHONPATH='src'), timeout=5)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, b'')
                    self.assertIn(b'Cannot read config', result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)
                    self.assertNotIn(b'synthetic-marker', result.stderr)
            path.write_text(json.dumps({'workspace_root': root, 'token_hour': 1}))
            result = subprocess.run([sys.executable, '-m', 'runtime_guard_mcp.server', '--config', str(path)], input=b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n', capture_output=True, env=dict(os.environ, PYTHONPATH='src'), timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['result'], {})

    def test_invalid_audit_capacity_is_controlled(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.json"
            for value in (0, -1, True, 1.5, "synthetic-marker", None):
                path.write_text(json.dumps({"audit_max_records": value}))
                result = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server", "--config", str(path)], input=b"", capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b"audit_max_records must be a positive integer", result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)
                self.assertNotIn(b"synthetic-marker", result.stderr)

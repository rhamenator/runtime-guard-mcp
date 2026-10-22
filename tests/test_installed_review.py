"""Regression checks for the installed-package evidence harness."""

import importlib.util
import json
import os
import subprocess
import sys
from unittest import mock
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import tempfile
import threading
import unittest

from runtime_guard_mcp.server import BoundedHTTPServer

spec = importlib.util.spec_from_file_location("installed_review", Path(__file__).resolve().parents[1] / "scripts" / "wfuzz_loopback_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class PingHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        length = self.headers.get("Content-Length")
        if length is None:
            return  # Probe cleanup can close a deliberately unfinished request.
        self.rfile.read(int(length))
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class InstalledReviewTests(unittest.TestCase):
    def test_resource_snapshot_reports_kib_threads_and_descriptors(self):
        with tempfile.TemporaryDirectory() as root:
            process = Path(root) / "123"
            (process / "fd").mkdir(parents=True)
            (process / "status").write_text("Name: fixture\nVmRSS: 1024 kB\nVmHWM: 2048 kB\nThreads: 3\n")
            (process / "fd" / "0").touch()
            (process / "fd" / "1").touch()
            self.assertEqual(review.process_resources(123, Path(root)), {"status": "measured", "rss_kib": 1024, "peak_rss_kib": 2048, "threads": 3, "file_descriptors": 2})

    def test_secret_scan_includes_uncheckpointed_sidecar_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            audit = Path(root) / "audit.sqlite"
            audit.write_bytes(b"clean main file")
            wal = Path(str(audit) + "-wal")
            wal.write_bytes(b"synthetic-private-marker")
            self.assertTrue(review.audit_contains_secret(audit, b"synthetic-private-marker"))
            wal.write_bytes(b"clean sidecar")
            self.assertFalse(review.audit_contains_secret(audit, b"synthetic-private-marker"))

    def test_saturation_probe_distinguishes_one_and_32_slots(self):
        for capacity in (1, 32):
            with self.subTest(capacity=capacity):
                server = BoundedHTTPServer(("127.0.0.1", 0), PingHandler, max_handlers=capacity)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    if capacity == 1:
                        with self.assertRaisesRegex(AssertionError, "held connection"):
                            review.handler_saturation_review(server.server_port, "synthetic")
                    else:
                        review.handler_saturation_review(server.server_port, "synthetic")
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=2)

    def test_installed_environment_rejects_inherited_python_and_guard_overrides(self):
        with tempfile.TemporaryDirectory() as root:
            shadow = Path(root) / "shadow"
            shadow.mkdir()
            (shadow / "json.py").write_text("raise RuntimeError('synthetic-source-shadow')\n")
            overrides = {"PYTHONPATH": str(shadow), "PYTHONHOME": str(Path(root) / "missing-home"),
                         "RUNTIME_GUARD_CONFIG": "synthetic-config", "RUNTIME_GUARD_WORKSPACE_ROOT": "synthetic-root",
                         "RUNTIME_GUARD_AUTH_TOKEN": "synthetic-inherited-token"}
            with mock.patch.dict(os.environ, overrides):
                environment = review.installed_environment("synthetic-generated-token")
            result = subprocess.run([sys.executable, "-c", "import json; print(json.dumps({'installed': True}))"],
                                    cwd=root, env=environment, capture_output=True, text=True, timeout=5, check=True)
            self.assertEqual(json.loads(result.stdout), {"installed": True})
            self.assertEqual({key: value for key, value in environment.items() if key.startswith("RUNTIME_GUARD_")},
                             {"RUNTIME_GUARD_AUTH_TOKEN": "synthetic-generated-token"})
            self.assertNotIn("PYTHONPATH", environment)
            self.assertNotIn("PYTHONHOME", environment)

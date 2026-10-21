"""Regression checks for the installed-package evidence harness."""

import importlib.util
import json
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

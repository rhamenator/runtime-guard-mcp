import json
import os
import subprocess
import sys
import socket
import time
import unittest
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from runtime_guard_mcp.server import BoundedHTTPServer, MAX_MESSAGE, RuntimeGuard, TOOLS


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.guard = RuntimeGuard("/tmp/work")

    def test_initialize_and_tools(self):
        init = self.guard.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        listed = self.guard.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(listed["result"]["tools"]), 4)
        schema_file = Path(__file__).resolve().parents[1] / "schemas" / "tools.json"
        self.assertEqual(json.loads(schema_file.read_text()), TOOLS)

    def test_call_and_validation(self):
        call = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "dry_run_command", "arguments": {"command": "rm -rf /"}}}
        response = self.guard.handle(call)
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(response["result"]["structuredContent"]["rule"], "RECURSIVE_DELETE")
        call["params"]["arguments"] = {"command": "git status", "unexpected": "x"}
        self.assertEqual(self.guard.handle(call)["error"]["code"], -32602)
        self.assertEqual(self.guard.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "missing"}})["error"]["code"], -32602)

    def test_stdio_process(self):
        env = dict(os.environ, PYTHONPATH="src")
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server", "--workspace-root", "/tmp/work"], input=b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n', stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(json.loads(process.stdout)["result"]["tools"]), 4)

    def test_stdio_oversized_line_is_drained_before_next_request(self):
        env = dict(os.environ, PYTHONPATH="src")
        oversized = b"x" * (MAX_MESSAGE * 3) + b"\n"
        valid = b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=oversized + valid, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0]["error"]["code"], -32600)
        self.assertEqual((responses[1]["id"], responses[1]["result"]), (7, {}))

    def test_http_process(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, PYTHONPATH="src")
        process = subprocess.Popen([sys.executable, "-m", "runtime_guard_mcp.server", "--transport", "http", "--host", "127.0.0.1", "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            url = f"http://127.0.0.1:{port}/mcp"
            for _ in range(50):
                try:
                    request = Request(url, data=b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}', headers={"Content-Type": "application/json"})
                    with urlopen(request, timeout=1) as response:
                        body = json.load(response)
                    break
                except OSError:
                    time.sleep(0.02)
            else:
                self.fail("HTTP server did not start")
            self.assertEqual(len(body["result"]["tools"]), 4)
            denied = Request(url, data=b'{"jsonrpc":"2.0","id":2,"method":"ping"}', headers={"Origin": "https://evil.example"})
            with self.assertRaises(HTTPError) as error:
                urlopen(denied, timeout=1)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
            bad_host = Request(url, data=b'{"jsonrpc":"2.0","id":3,"method":"ping"}', headers={"Host": "evil.example"})
            with self.assertRaises(HTTPError) as error:
                urlopen(bad_host, timeout=1)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
            invalid_host = Request(url, data=b'{"jsonrpc":"2.0","id":3,"method":"ping"}', headers={"Host": "localhost:bad"})
            with self.assertRaises(HTTPError) as error:
                urlopen(invalid_host, timeout=1)
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
            invalid_origin = Request(url, data=b'{"jsonrpc":"2.0","id":3,"method":"ping"}', headers={"Origin": "ftp://localhost"})
            with self.assertRaises(HTTPError) as error:
                urlopen(invalid_origin, timeout=1)
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
            body = b'{"jsonrpc":"2.0","id":4,"method":"ping"}'
            for headers, expected in (
                (b"Content-Type: application/json\r\nContent-Length: 42\r\nContent-Length: 42\r\n", 400),
                (b"Content-Type: application/json\r\nContent-Length: 42\r\nTransfer-Encoding: chunked\r\n", 400),
                (b"Content-Length: 42\r\n", 415),
                (b"Host: evil.example\r\nContent-Type: application/json\r\nContent-Length: 42\r\n", 400),
                (b"Origin: http://localhost\r\nOrigin: http://evil.example\r\nContent-Type: application/json\r\nContent-Length: 42\r\n", 400),
                (b"Authorization: Bearer one\r\nAuthorization: Bearer two\r\nContent-Type: application/json\r\nContent-Length: 42\r\n", 400),
                (b"Content-Type: application/json\r\nContent-Type: text/plain\r\nContent-Length: 42\r\n", 415),
                (b"Content-Type: application/json\r\nContent-Length: " + b"9" * 5000 + b"\r\n", 413),
            ):
                with self.subTest(headers=headers[:40]):
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
                        connection.settimeout(2)
                        connection.sendall(b"POST /mcp HTTP/1.1\r\nHost: 127.0.0.1\r\n" + headers + b"Connection: close\r\n\r\n" + body)
                        status_line = connection.recv(256).split(b"\r\n", 1)[0]
                    self.assertEqual(int(status_line.split()[1]), expected)
            with urlopen(request, timeout=1) as response:
                self.assertEqual(json.load(response)["result"]["tools"][0]["name"], "audit_path_access")
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_http_handler_cap_and_recovery(self):
        entered = threading.Event()
        release = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                if self.path == "/hold":
                    entered.set()
                    release.wait(timeout=2)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

        server = BoundedHTTPServer(("127.0.0.1", 0), Handler, max_handlers=1, socket_timeout=1)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        held = socket.create_connection(server.server_address, timeout=2)
        held.settimeout(2)
        try:
            held.sendall(b"GET /hold HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            self.assertTrue(entered.wait(timeout=1))
            with self.assertRaises(HTTPError) as error:
                urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=2)
            self.assertEqual(error.exception.code, 503)
            error.exception.close()
            release.set()
            self.assertIn(b"200 OK", held.recv(1024))
            for _ in range(50):
                try:
                    with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=2) as response:
                        self.assertEqual(response.status, 200)
                    break
                except HTTPError as error:
                    error.close()
                    time.sleep(0.02)
            else:
                self.fail("Handler slot was not released")
        finally:
            release.set()
            held.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_http_idle_connection_times_out(self):
        class QuietHandler(BaseHTTPRequestHandler):
            def log_error(self, *_args):
                pass

        server = BoundedHTTPServer(("127.0.0.1", 0), QuietHandler, max_handlers=1, socket_timeout=0.1)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as idle:
                idle.settimeout(2)
                idle.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n")
                self.assertEqual(idle.recv(1), b"")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

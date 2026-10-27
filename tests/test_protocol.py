import json
import http.client
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

from runtime_guard_mcp.server import BoundedHTTPServer, MAX_JSON_DEPTH, MAX_JSON_STRUCTURE_TOKENS, MAX_MESSAGE, RuntimeGuard, TOOLS, parse_json_request


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.guard = RuntimeGuard("/tmp/work")

    def test_initialize_and_tools(self):
        init = self.guard.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1"}}})
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        listed = self.guard.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(listed["result"]["tools"]), 4)
        schema_file = Path(__file__).resolve().parents[1] / "schemas" / "tools.json"
        self.assertEqual(json.loads(schema_file.read_text()), TOOLS)

    def test_initialize_required_fields_and_recovery(self):
        valid = {"protocolVersion": "future-version", "capabilities": {"extension": {}}, "clientInfo": {"name": "fixture", "version": "1", "title": "Fixture"}, "extension": {}}
        invalid = [None, [], {}, {**valid, "protocolVersion": 7}, {**valid, "capabilities": []}, {**valid, "clientInfo": None}, {**valid, "clientInfo": {"name": "fixture"}}, {**valid, "clientInfo": {"name": 7, "version": "1"}}, {**valid, "clientInfo": {"name": "fixture", "version": "1", "title": False}}]
        frames = [{"jsonrpc": "2.0", "id": index, "method": "initialize", "params": params} for index, params in enumerate(invalid)]
        for frame in frames:
            self.assertEqual(self.guard.handle(frame)["error"]["code"], -32602)
        frames.append({"jsonrpc": "2.0", "id": 99, "method": "initialize", "params": valid})
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=5, check=True)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([reply["error"]["code"] for reply in replies[:-1]], [-32602] * len(invalid))
        self.assertEqual(replies[-1]["result"]["protocolVersion"], "2025-06-18")

    def test_call_and_validation(self):
        call = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "dry_run_command", "arguments": {"command": "rm -rf /"}}}
        response = self.guard.handle(call)
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(response["result"]["structuredContent"]["rule"], "RECURSIVE_DELETE")
        call["params"]["arguments"] = {"command": "git status", "unexpected": "x"}
        self.assertEqual(self.guard.handle(call)["error"]["code"], -32602)
        self.assertEqual(self.guard.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "missing"}})["error"]["code"], -32602)

    def test_invalid_ids_are_not_reflected_from_malformed_envelopes(self):
        frames = [{"id": value, "method": 7} for value in (True, [], {"private": "synthetic-marker"})]
        for frame in frames:
            with self.subTest(frame=frame):
                reply = self.guard.handle(frame)
                self.assertEqual((reply["id"], reply["error"]["code"]), (None, -32600))
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames) + b'{"jsonrpc":"2.0","id":9,"method":"ping"}\n', capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=5, check=True)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([(reply["id"], reply["error"]["code"]) for reply in replies[:-1]], [(None, -32600)] * 3)
        self.assertEqual((replies[-1]["id"], replies[-1]["result"]), (9, {}))

    def test_invalid_request_ids_cannot_consume_budget_in_either_era(self):
        for modern in (False, True):
            guard = RuntimeGuard("/tmp/work")
            params = {"name": "budget_guard", "arguments": {"session_id": "ids", "commands": 1, "consume": True}}
            if modern:
                params["_meta"] = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                                   "io.modelcontextprotocol/clientCapabilities": {}}
            for identifier in (None, 1.0, 1.5, True, [], {"synthetic-marker": "private"}):
                reply = guard.handle({"jsonrpc": "2.0", "id": identifier, "method": "tools/call", "params": params}, modern_stdio=True)
                self.assertEqual((reply["id"], reply["error"]["code"]), (None, -32600))
                self.assertNotIn("synthetic-marker", json.dumps(reply))
            params["arguments"]["commands"] = 120
            result = guard.handle({"jsonrpc": "2.0", "id": "recovery", "method": "tools/call", "params": params}, modern_stdio=True)
            self.assertEqual(result["result"]["structuredContent"]["status"], "SAFE")

    def test_scalar_params_are_rejected_and_stdio_recovers(self):
        frames = [{"jsonrpc": "2.0", "id": index, "method": method, "params": value}
                  for index, (method, value) in enumerate((
                      ("ping", None), ("tools/list", True), ("initialize", 7), ("ping", "synthetic-marker")))]
        for frame in frames:
            reply = self.guard.handle(frame)
            self.assertEqual((reply["id"], reply["error"]["code"]), (frame["id"], -32602))
        self.assertIsNone(self.guard.handle({"jsonrpc": "2.0", "method": "notifications/initialized", "params": None}))
        for params in ({}, {"_meta": {"example/extension": True}}):
            self.assertEqual(self.guard.handle({"jsonrpc": "2.0", "id": 9, "method": "ping", "params": params})["result"], {})
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames) + b'{"jsonrpc":"2.0","id":9,"method":"ping"}\n', capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=5, check=True)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([reply["error"]["code"] for reply in replies[:-1]], [-32602] * 4)
        self.assertEqual(replies[-1]["result"], {})

    def test_object_params_and_metadata_reject_before_tool_side_effects(self):
        self.guard = RuntimeGuard("/tmp/work", token_hour=1)
        frames = []
        for value in ([], None, True, 7, "synthetic-private-marker"):
            frames.append({"jsonrpc": "2.0", "id": len(frames), "method": "tools/call", "params": {"name": "budget_guard", "arguments": {"session_id": "fixture", "tokens": 1, "consume": True}, "_meta": value}})
        frames.append({"jsonrpc": "2.0", "id": 99, "method": "ping", "params": []})
        for frame in frames:
            self.assertEqual(self.guard.handle(frame)["error"]["code"], -32602)
        remaining = self.guard.call("budget_guard", {"session_id": "fixture", "tokens": 1, "consume": True}, "local")
        self.assertEqual(remaining["structuredContent"]["status"], "SAFE")
        frames.append({"jsonrpc": "2.0", "id": 100, "method": "ping", "params": {"_meta": {"example/extension": {"nested": True}}}})
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=5, check=True)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([reply["error"]["code"] for reply in replies[:-1]], [-32602] * 6)
        self.assertNotIn("synthetic-private-marker", process.stdout.decode())
        self.assertEqual(replies[-1]["result"], {})

    def test_stdio_process(self):
        env = dict(os.environ, PYTHONPATH="src")
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server", "--workspace-root", "/tmp/work"], input=b'{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n', stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(json.loads(process.stdout.splitlines()[-1])["result"]["tools"]), 4)

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

    def test_stdio_rejects_ambiguous_json_and_recovers(self):
        env = dict(os.environ, PYTHONPATH="src")
        invalid = [
            b'{"jsonrpc":"2.0","id":1,"method":"ping","x":NaN}',
            b'{"jsonrpc":"2.0","id":1,"method":"ping","method":"tools/list"}',
            b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"dry_run_command","arguments":{"command":"git status","command":"rm -rf /"}}}',
            b'{"jsonrpc":"2.0","id":1,"method":"ping","x":1e999}',
            b'\xff{"jsonrpc":"2.0","id":1,"method":"ping"}',
            b'[' * (MAX_JSON_DEPTH + 1) + b'0' + b']' * (MAX_JSON_DEPTH + 1),
            b'[' + b'0,' * MAX_JSON_STRUCTURE_TOKENS + b'0]',
        ]
        valid = b'{"jsonrpc":"2.0","id":7,"method":"ping"}'
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"\n".join([*invalid, valid, b""]), capture_output=True, env=env, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([reply["error"]["code"] for reply in responses[:-1]], [-32700] * len(invalid))
        self.assertEqual((responses[-1]["id"], responses[-1]["result"]), (7, {}))

    def test_json_nesting_limit_ignores_quoted_brackets(self):
        at_limit = b'[' * MAX_JSON_DEPTH + b'0' + b']' * MAX_JSON_DEPTH
        self.assertIsInstance(parse_json_request(at_limit), list)
        quoted = b'{"text":"' + b'[' * (MAX_JSON_DEPTH + 10) + b'\\\"' + b']' * (MAX_JSON_DEPTH + 10) + b'"}'
        self.assertIn("text", parse_json_request(quoted))
        beyond_limit = b'[' * (MAX_JSON_DEPTH + 1) + b'0' + b']' * (MAX_JSON_DEPTH + 1)
        with self.assertRaises(ValueError):
            parse_json_request(beyond_limit)

    def test_json_structure_limit_ignores_quoted_commas(self):
        at_limit = b'[' + b'0,' * (MAX_JSON_STRUCTURE_TOKENS - 1) + b'0]'
        self.assertEqual(len(parse_json_request(at_limit)), MAX_JSON_STRUCTURE_TOKENS)
        quoted = b'{"text":"' + b',' * (MAX_JSON_STRUCTURE_TOKENS + 1) + b'"}'
        self.assertIn("text", parse_json_request(quoted))
        beyond_limit = b'[' + b'0,' * MAX_JSON_STRUCTURE_TOKENS + b'0]'
        with self.assertRaises(ValueError):
            parse_json_request(beyond_limit)

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
            for invalid_id in (True, [], {"private": "synthetic-marker"}):
                malformed = Request(url, data=json.dumps({"id": invalid_id, "method": 7}).encode(), headers={"Content-Type": "application/json"})
                with urlopen(malformed, timeout=1) as response:
                    reply = json.load(response)
                self.assertEqual((reply["id"], reply["error"]["code"]), (None, -32600))
            for params in (None, True, 7, "synthetic-marker"):
                malformed = Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 8, "method": "ping", "params": params}).encode(), headers={"Content-Type": "application/json"})
                with urlopen(malformed, timeout=1) as response:
                    reply = json.load(response)
                self.assertEqual((reply["id"], reply["error"]["code"]), (8, -32602))
            marker = b"SYNTHETIC_PRIVATE_MARKER"
            for wire, expected in (
                (marker + b" /mcp HTTP/1.1\r\nHost: localhost\r\n\r\n", 501),
                (b"POST /mcp HTTP/" + marker + b"\r\nHost: localhost\r\n\r\n", 400),
                (b"POST /mcp HTTP/1.1\r\nHost: localhost\r\nX-Test: " + marker + b"x" * 65536 + b"\r\n\r\n", 431),
            ):
                with self.subTest(expected=expected):
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
                        connection.sendall(wire)
                        reply = http.client.HTTPResponse(connection)
                        reply.begin()
                        raw = reply.read()
                        self.assertEqual(reply.status, expected)
                        self.assertEqual(reply.getheader("Content-Type"), "application/json")
                        self.assertNotIn(marker, raw)
                        self.assertEqual(set(json.loads(raw)), {"error"})
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                connection.request("HEAD", "/mcp")
                reply = connection.getresponse()
                self.assertEqual((reply.status, reply.read()), (501, b""))
            finally:
                connection.close()
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
            for malformed in (
                b'{"jsonrpc":"2.0","id":4,"method":"ping","x":NaN}',
                b'{"jsonrpc":"2.0","id":4,"method":"ping","method":"tools/list"}',
                b'{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"dry_run_command","arguments":{"command":"git status","command":"rm -rf /"}}}',
                b'{"jsonrpc":"2.0","id":4,"method":"ping","x":1e999}',
                b'\xff{"jsonrpc":"2.0","id":4,"method":"ping"}',
                b'[' * (MAX_JSON_DEPTH + 1) + b'0' + b']' * (MAX_JSON_DEPTH + 1),
                b'[' + b'0,' * MAX_JSON_STRUCTURE_TOKENS + b'0]',
            ):
                with self.subTest(malformed=malformed):
                    malformed_request = Request(url, data=malformed, headers={"Content-Type": "application/json"})
                    with urlopen(malformed_request, timeout=1) as response:
                        self.assertEqual(json.load(response)["error"]["code"], -32700)
            with urlopen(request, timeout=1) as response:
                self.assertEqual(json.load(response)["result"]["tools"][0]["name"], "audit_path_access")
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_http_bearer_auth_near_matches_and_unicode(self):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        token = "synthetic-token-0123456789"
        process = subprocess.Popen([sys.executable, "-m", "runtime_guard_mcp.server", "--transport", "http", "--port", str(port)], env=dict(os.environ, PYTHONPATH="src", RUNTIME_GUARD_AUTH_TOKEN=token), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def send(authorization):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                headers = {"Content-Type": "application/json"}
                if authorization is not None:
                    headers["Authorization"] = authorization
                connection.request("POST", "/mcp", b'{"jsonrpc":"2.0","id":1,"method":"ping"}', headers)
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()
        try:
            for _ in range(50):
                try:
                    if send(None)[0] == 401:
                        break
                except OSError:
                    time.sleep(0.02)
            else:
                self.fail("authenticated HTTP server did not start")
            for value in (None, "Bearer " + token[:-1], "Bearer " + token[:-1] + "X", "Bearer X" + token[1:], "bearer " + token, "Bearer é"):
                with self.subTest(value=value):
                    self.assertEqual(send(value), (401, {"error": "Unauthorized"}))
            self.assertEqual(send("Bearer " + token), (200, {"jsonrpc": "2.0", "id": 1, "result": {}}))
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

    def test_http_byte_drip_hits_absolute_deadline(self):
        reading = threading.Event()

        class DripHandler(BaseHTTPRequestHandler):
            def log_error(self, *_args):
                pass

            def log_message(self, *_args):
                pass

            def do_POST(self):
                reading.set()
                self.rfile.read(100)

            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

        server = BoundedHTTPServer(("127.0.0.1", 0), DripHandler, max_handlers=1, socket_timeout=1, connection_deadline=0.25)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as drip:
                drip.settimeout(2)
                drip.sendall(b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\nx")
                self.assertTrue(reading.wait(timeout=1))
                with self.assertRaises(HTTPError) as error:
                    urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=2)
                self.assertEqual(error.exception.code, 503)
                error.exception.close()
                for _ in range(5):
                    time.sleep(0.05)
                    try:
                        drip.sendall(b"x")
                    except OSError:
                        break
                for _ in range(30):
                    try:
                        with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=2) as response:
                            self.assertEqual(response.read(), b"ok")
                        break
                    except HTTPError as error:
                        error.close()
                        time.sleep(0.02)
                else:
                    self.fail("A byte-dripping client held the handler after its absolute deadline")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

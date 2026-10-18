import json
import os
import subprocess
import sys
import socket
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from runtime_guard_mcp.server import RuntimeGuard, TOOLS


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
        finally:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()

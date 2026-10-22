import json
import os
import subprocess
import sys
import threading
import unittest

from runtime_guard_mcp.server import META_PREFIX, MODERN_VERSION, RuntimeGuard, StdioDispatcher, valid_meta_key


def request(identifier=1, method="ping", **params):
    return {"jsonrpc": "2.0", "id": identifier, "method": method, "params": {"_meta": {META_PREFIX + "protocolVersion": MODERN_VERSION, META_PREFIX + "clientCapabilities": {}}, **params}}


class ModernTests(unittest.TestCase):
    def test_malformed_idless_envelopes_still_return_errors(self):
        frames = [{"method": 7}, {"jsonrpc": "1.0", "method": "ping"}, request(4)]
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=6, check=True)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([reply["error"]["code"] for reply in replies[:2]], [-32600, -32600])
        self.assertEqual(replies[2]["id"], 4)

    def test_metadata_key_grammar(self):
        for key in ("", "progressToken", "io.modelcontextprotocol/protocolVersion", "com.example/custom_name", "a/", "a-b.c1/name.1"):
            self.assertTrue(valid_meta_key(key), key)
        for key in ("/name", "a//name", "a.-b/name", "a_/name", "é/name", "a/_name", "a/name-", "a/" + "x" * 65536 + "!"):
            self.assertFalse(valid_meta_key(key), key[:32])

    def test_stateless_discovery_results_and_legacy_interleave(self):
        guard = RuntimeGuard("/tmp/work")
        frames = [request(1, "server/discover"), request(2, "tools/list"), {"jsonrpc": "2.0", "id": 3, "method": "ping"}, request(4, "tools/call", name="dry_run_command", arguments={"command": "git status"})]
        process = subprocess.run([sys.executable, "-m", "runtime_guard_mcp.server"], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), capture_output=True, env=dict(os.environ, PYTHONPATH="src"), timeout=6, check=True)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(replies[0]["result"]["supportedVersions"], [MODERN_VERSION, "2025-06-18"])
        self.assertEqual(replies[0]["result"]["cacheScope"], "private")
        names = [tool["name"] for tool in replies[1]["result"]["tools"]]
        self.assertEqual(names, sorted(names))
        self.assertEqual(replies[2]["result"], {})
        for index in (0, 1, 3):
            self.assertEqual(replies[index]["result"]["resultType"], "complete")
            self.assertIn(META_PREFIX + "serverInfo", replies[index]["result"]["_meta"])
        self.assertEqual(replies[3]["result"]["structuredContent"]["status"], "SAFE")
        self.assertEqual(guard.handle(request(), modern_stdio=False)["error"]["code"], -32022)

    def test_metadata_validation_and_version_errors(self):
        guard = RuntimeGuard("/tmp/work")
        for meta in ({}, {META_PREFIX + "protocolVersion": MODERN_VERSION}, {META_PREFIX + "protocolVersion": MODERN_VERSION, META_PREFIX + "clientCapabilities": []}, {META_PREFIX + "protocolVersion": MODERN_VERSION, META_PREFIX + "clientCapabilities": {"roots": True}}):
            self.assertEqual(guard.handle(request(method="server/discover", _meta=meta), modern_stdio=True)["error"]["code"], -32602)
        message = request()
        message["params"]["_meta"][META_PREFIX + "protocolVersion"] = "2099-01-01"
        error = guard.handle(message, modern_stdio=True)["error"]
        self.assertEqual(error["code"], -32022)
        self.assertEqual(error["data"], {"supported": [MODERN_VERSION, "2025-06-18"], "requested": "2099-01-01"})
        for identifier in (None, 1.5, True):
            for version in (MODERN_VERSION, "2099-01-01"):
                message = request(identifier)
                message["params"]["_meta"][META_PREFIX + "protocolVersion"] = version
                self.assertEqual(guard.handle(message, modern_stdio=True)["error"]["code"], -32600)
        message = request()
        message["params"]["_meta"][META_PREFIX + "clientInfo"] = {"name": "fixture", "version": "1", "title": False}
        self.assertEqual(guard.handle(message, modern_stdio=True)["error"]["code"], -32602)

    def test_wire_cancellation_suppresses_inflight_reply(self):
        # A controlled slow policy fixture tests the real reader/worker/output path.
        # Production tools have no artificial delay and are not command executors.
        code = """
import sys, time
from runtime_guard_mcp.server import RuntimeGuard, serve_stdio
class Fixture(RuntimeGuard):
    def call(self, name, arguments, caller):
        sys.stderr.write('STARTED\\n'); sys.stderr.flush()
        time.sleep(0.3)
        return super().call(name, arguments, caller)
serve_stdio(Fixture('/tmp/work'))
"""
        process = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, PYTHONPATH="src"))
        deadline = threading.Timer(5, process.kill)
        deadline.start()
        try:
            process.stdin.write(json.dumps(request(1, "tools/call", name="dry_run_command", arguments={"command": "git status"})).encode() + b"\n")
            process.stdin.flush()
            self.assertEqual(process.stderr.readline(), b"STARTED\n")
            frames = [{"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}}, request(2)]
            stdout, stderr = process.communicate(b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
            replies = [json.loads(line) for line in stdout.splitlines()]
            self.assertEqual([reply["id"] for reply in replies], [2])
        finally:
            deadline.cancel()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe:
                    pipe.close()

    def test_saturated_dispatch_cancellation_and_recovery(self):
        started, release, received = threading.Event(), threading.Event(), threading.Event()
        replies, calls = [], []

        class SlowGuard:
            def handle(self, message, caller, modern_stdio=False):
                calls.append(message["id"])
                if message["id"] == 1:
                    started.set()
                    if not release.wait(3):
                        raise RuntimeError("fixture timed out")
                return {"jsonrpc": "2.0", "id": message["id"], "result": {}}

        def emit(reply):
            replies.append(reply)
            received.set()

        dispatcher = StdioDispatcher(SlowGuard(), emit, capacity=2)
        try:
            dispatcher.submit(request(1))
            self.assertTrue(started.wait(1))
            dispatcher.submit(request(2))
            dispatcher.submit(request(3))
            self.assertEqual(replies[-1]["error"]["code"], 1001)
            for identifier in ([], True, "unknown"):
                dispatcher.submit({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": identifier}})
            for identifier in (1, 2):
                dispatcher.submit({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": identifier, "reason": "synthetic-marker"}})
            release.set()
            dispatcher.queue.join()
            self.assertEqual(calls, [1])
            self.assertEqual(len(replies), 1)
            received.clear()
            dispatcher.submit(request(1))
            self.assertTrue(received.wait(1))
            dispatcher.queue.join()
            self.assertEqual(replies[-1]["id"], 1)
            self.assertEqual(replies[-1]["result"], {})
            dispatcher.submit({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}})
            self.assertEqual(len(replies), 2)
        finally:
            release.set()
            dispatcher.close()

    def test_unrelated_client_interrupt_cannot_cancel_advisory_work(self):
        # Codex/Cursor can interrupt their turn without sending request cancellation.
        started, release = threading.Event(), threading.Event()
        effects, replies = [], []

        class Guard:
            def handle(self, message, caller, modern_stdio=False):
                if message["id"] == 1:
                    started.set()
                    if not release.wait(2):
                        raise RuntimeError("fixture timeout")
                effects.append(message["id"])
                return {"jsonrpc": "2.0", "id": message["id"], "result": {}}

        dispatcher = StdioDispatcher(Guard(), replies.append)
        try:
            dispatcher.submit(request(1))
            self.assertTrue(started.wait(1))
            dispatcher.submit({"jsonrpc": "2.0", "method": "client/turn-interrupted", "params": {"requestId": 1}})
            release.set()
            dispatcher.queue.join()
            self.assertEqual(effects, [1])
            self.assertEqual([reply["id"] for reply in replies], [1])
            dispatcher.submit(request(2))
            dispatcher.queue.join()
            self.assertEqual(effects, [1, 2])
            self.assertEqual([reply["id"] for reply in replies], [1, 2])
        finally:
            release.set()
            dispatcher.close()

    def test_nested_capabilities_rejected_before_budget_mutation(self):
        guard = RuntimeGuard("/tmp/work")
        invalid = [{"experimental": {"probe": True}}, {"extensions": {"probe": {}}},
                   {"extensions": {"com.example/invalid!": {}}}, {"extensions": {"com.example/probe": []}},
                   {"sampling": {"tools": False}}, {"sampling": {"context": None}},
                   {"elicitation": {"form": []}}, {"elicitation": {"url": 1}}]
        for capabilities in invalid:
            message = request(method="tools/call", name="budget_guard", arguments={"session_id": "review", "commands": 1, "consume": True})
            message["params"]["_meta"][META_PREFIX + "clientCapabilities"] = capabilities
            result = guard.handle(message, modern_stdio=True)
            self.assertEqual(result["error"]["code"], -32602)
            self.assertNotIn("probe", json.dumps(result))
        valid = request(method="tools/call", name="budget_guard", arguments={"session_id": "review", "commands": 120, "consume": True})
        self.assertEqual(guard.handle(valid, modern_stdio=True)["result"]["structuredContent"]["status"], "SAFE")

    def test_nested_capabilities_and_single_page_cursor(self):
        guard = RuntimeGuard("/tmp/work")
        message = request(method="tools/list")
        message["params"]["_meta"][META_PREFIX + "clientCapabilities"] = {
            "experimental": {"probe": {}}, "extensions": {"com.example/probe": {"custom": [1, True]}},
            "sampling": {"context": {}, "tools": {}}, "elicitation": {"form": {}, "url": {}},
            "com.example/custom": {"future": True}}
        result = guard.handle(message, modern_stdio=True)["result"]
        self.assertEqual(len(result["tools"]), 4)
        self.assertNotIn("nextCursor", result)
        for cursor in ("", "synthetic-marker", 1, None, [], {}):
            for modern in (True, False):
                frame = request(method="tools/list", cursor=cursor) if modern else {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"cursor": cursor}}
                error = guard.handle(frame, modern_stdio=True)
                self.assertEqual(error["error"]["code"], -32602)
                self.assertNotIn("synthetic-marker", json.dumps(error))
        self.assertEqual(len(guard.handle(request(method="tools/list"), modern_stdio=True)["result"]["tools"]), 4)

"""Installed HTTP internal-error correlation/redaction and recovery fixture."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time


def fixture(root, port):
    from runtime_guard_mcp.server import RuntimeGuard, serve_http

    class FaultGuard(RuntimeGuard):
        failures = 2

        def handle(self, message, *args, **kwargs):
            if message.get('method') == 'notifications/fault':
                raise RuntimeError('synthetic-private-exception')
            return super().handle(message, *args, **kwargs)

        def call(self, *args, **kwargs):
            if self.failures:
                self.failures -= 1
                raise RuntimeError('synthetic-private-exception')
            return super().call(*args, **kwargs)

    serve_http(FaultGuard(root), '127.0.0.1', port, os.environ['RUNTIME_GUARD_AUTH_TOKEN'])


def review(installed_python):
    from wfuzz_loopback_review import installed_environment, request
    token = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix='runtime-guard-http-error-') as directory:
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        process = subprocess.Popen([str(Path(installed_python).absolute()), str(Path(__file__).absolute()), '--fixture', directory, str(port)],
                                   cwd=directory, env=installed_environment(token), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    status, raw = request(port, token)
                    assert status == 200 and json.loads(raw)['result'] == {}
                    break
                except OSError:
                    assert process.poll() is None and time.monotonic() < deadline
                    time.sleep(.02)
            for identifier in (7, 'correlated'):
                frame = {'jsonrpc': '2.0', 'id': identifier, 'method': 'tools/call', 'params': {'name': 'dry_run_command', 'arguments': {'command': 'git status'}}}
                status, raw = request(port, token, json.dumps(frame).encode())
                assert status == 200
                assert json.loads(raw) == {'jsonrpc': '2.0', 'id': identifier, 'error': {'code': -32603, 'message': 'Internal error'}}
                assert b'synthetic-private-exception' not in raw
            status, raw = request(port, token, b'{"jsonrpc":"2.0","method":"notifications/fault"}')
            assert status == 202 and raw == b''
            status, raw = request(port, token)
            assert status == 200 and json.loads(raw)['result'] == {}
            frame['id'] = 9
            status, raw = request(port, token, json.dumps(frame).encode())
            assert status == 200 and json.loads(raw)['result']['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
            return {'status': 'PASS', 'correlated_errors': 2, 'error_code': -32603,
                    'notification_suppressed': True, 'ping_recovery': True, 'tool_recovery': True,
                    'scope': 'test-only unexpected exceptions; actual installed HTTP handler and policy recovery'}
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--fixture':
        fixture(sys.argv[2], int(sys.argv[3]))
    elif len(sys.argv) == 2:
        print(json.dumps(review(sys.argv[1]), indent=2))
    else:
        raise SystemExit('usage: http_error_review.py INSTALLED_PYTHON')

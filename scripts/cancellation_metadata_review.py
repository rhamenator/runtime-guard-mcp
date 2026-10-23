"""Installed reader/worker cancellation boundary using a test-only policy pause."""
import json
import os
from pathlib import Path
import subprocess
import sys

PREFIX = 'io.modelcontextprotocol/'


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: cancellation_metadata_review.py INSTALLED_PYTHON')
    fixture = """
import sys, time
from runtime_guard_mcp.server import RuntimeGuard, serve_stdio
class Fixture(RuntimeGuard):
    def call(self, name, arguments, caller):
        sys.stderr.write('STARTED\\n'); sys.stderr.flush()
        time.sleep(0.3)
        return super().call(name, arguments, caller)
serve_stdio(Fixture('/tmp/work'))
"""
    env = {k: v for k, v in os.environ.items()
           if k not in {'PYTHONPATH', 'PYTHONHOME'} and not k.startswith('RUNTIME_GUARD_')}
    invalid = [None, [], {'traceparent': 'synthetic-invalid'}, {'traceparent': None}, {'bad!': {}}, {PREFIX + 'subscriptionId': True},
               {PREFIX + 'subscriptionId': None}, {PREFIX + 'subscriptionId': []}]
    for valid in (False, True):
        process = subprocess.Popen([str(Path(sys.argv[1]).absolute()), '-c', fixture],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=env, cwd='/tmp')
        try:
            request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
                '_meta': {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}},
                'name': 'dry_run_command', 'arguments': {'command': 'git status'}}}
            process.stdin.write(json.dumps(request).encode() + b'\n'); process.stdin.flush()
            assert process.stderr.readline() == b'STARTED\n'
            metas = invalid + ([{'com.example/probe': {}, PREFIX + 'subscriptionId': 7, 'traceparent': '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'}] if valid else [])
            frames = [{'jsonrpc': '2.0', 'method': 'notifications/cancelled',
                       'params': {'requestId': 1, '_meta': meta}} for meta in metas]
            frames.append({'jsonrpc': '2.0', 'id': 2, 'method': 'ping'})
            stdout, stderr = process.communicate(b''.join(json.dumps(f).encode() + b'\n' for f in frames), timeout=5)
            assert process.returncode == 0, stderr
            replies = [json.loads(line) for line in stdout.splitlines()]
            assert [r['id'] for r in replies] == ([2] if valid else [1, 2])
            assert replies[-1]['result'] == {}
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
    print('PASS: malformed cancellation metadata ignored; valid extension metadata cancellation and recovery')


if __name__ == '__main__':
    main()

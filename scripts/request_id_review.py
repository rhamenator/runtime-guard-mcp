"""Installed MCP request-ID validation before budget dispatch and recovery."""
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from modern_validation_review import PREFIX, run_frames
from wfuzz_loopback_review import installed_environment, request

INVALID = [None, 1.0, 1.5, True, [], {'synthetic-marker': 'private'}]


def frames(modern=False):
    params = {'name': 'budget_guard', 'arguments': {'session_id': 'ids', 'commands': 1, 'consume': True}}
    if modern:
        params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
    rejected = [{'jsonrpc': '2.0', 'id': value, 'method': 'tools/call', 'params': params} for value in INVALID]
    # A missing ID is a notification, not a consuming request.
    notification = {'jsonrpc': '2.0', 'method': 'tools/call', 'params': params}
    recovery = {'jsonrpc': '2.0', 'id': 'recovery', 'method': 'tools/call', 'params': {
        **params, 'arguments': {'session_id': 'ids', 'commands': 120, 'consume': True}}}
    pings = [{'jsonrpc': '2.0', 'id': value, 'method': 'ping'} for value in (-7, '', 0)]
    return rejected + [notification, recovery] + pings


def check(replies):
    assert len(replies) == 10
    for reply in replies[:6]:
        assert reply['id'] is None and reply['error']['code'] == -32600
        assert 'synthetic-marker' not in json.dumps(reply)
    assert replies[6]['id'] == 'recovery'
    assert replies[6]['result']['structuredContent']['status'] == 'SAFE'
    assert [r['id'] for r in replies[7:]] == [-7, '', 0]
    assert all('result' in r for r in replies[7:])


def http_review(executable):
    with tempfile.TemporaryDirectory(prefix='runtime-guard-ids-') as root:
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
        token = secrets.token_hex(32)
        process = subprocess.Popen([executable, '--transport', 'http', '--port', str(port)], cwd=root,
                                   env=installed_environment(token), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            end = time.monotonic() + 5
            while True:
                try:
                    assert request(port, token)[0] == 200
                    break
                except OSError:
                    assert process.poll() is None and time.monotonic() < end
                    time.sleep(.03)
            replies = []
            for frame in frames():
                status, raw = request(port, token, json.dumps(frame).encode())
                if 'id' not in frame:
                    assert status == 202 and not raw
                else:
                    assert status == 200
                    replies.append(json.loads(raw))
            check(replies)
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: request_id_review.py INSTALLED_SERVER')
    executable = str(Path(sys.argv[1]).absolute())
    for modern in (False, True):
        check(run_frames(executable, frames(modern)))
    http_review(executable)
    print(json.dumps({'status': 'PASS', 'routes': ['legacy stdio', 'modern stdio', 'legacy HTTP'],
                      'invalid_consuming_requests_per_route': 6, 'notification_ignored': True,
                      'full_budget_recovery': True, 'valid_negative_empty_zero_ids': True,
                      'scope': 'request ID shape boundary; no ID replay/deduplication or full conformance claim'}))


if __name__ == '__main__':
    main()

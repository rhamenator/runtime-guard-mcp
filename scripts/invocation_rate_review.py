"""Installed legacy/modern stdio admission, real minute recovery and policy isolation."""
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time

from wfuzz_loopback_review import installed_environment, request


def http_review(executable, root):
    config = root / 'http.json'
    config.write_text(json.dumps({'invocations_minute': 1}))
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    token = secrets.token_hex(32)
    p = subprocess.Popen([executable, '--transport', 'http', '--port', str(port), '--config', str(config)],
                         cwd=root, env=installed_environment(token), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                assert request(port, token)[0] == 200
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.02)
        frame = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                 'params': {'name': 'dry_run_command', 'arguments': {'command': 'pwd'}}}
        status, raw = request(port, token, json.dumps(frame).encode())
        assert status == 200 and json.loads(raw)['result']['structuredContent']['status'] == 'SAFE'
        status, raw = request(port, token, json.dumps(frame).encode())
        assert status == 200 and json.loads(raw)['result']['structuredContent']['rule'] == 'INVOCATION_RATE_LIMIT'
        assert request(port, token)[0] == 200
    finally:
        p.terminate(); p.wait(timeout=5)


def review(executable):
    with tempfile.TemporaryDirectory(prefix='runtime-guard-rate-') as directory:
        root = Path(directory)
        processes = []
        watchdog = threading.Timer(75, lambda: [p.kill() for p in processes if p.poll() is None])
        watchdog.daemon = True
        watchdog.start()
        try:
            for modern in (False, True):
                config = root / f'{modern}.json'
                config.write_text(json.dumps({'invocations_minute': 1}))
                p = subprocess.Popen([executable, '--config', str(config)], cwd=root,
                                     env=installed_environment(''), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                processes.append(p)

                def exchange(identifier, method, params):
                    if modern:
                        params = dict(params, _meta={'io.modelcontextprotocol/protocolVersion': '2026-07-28', 'io.modelcontextprotocol/clientCapabilities': {}})
                    p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params}) + '\n')
                    p.stdin.flush()
                    response = json.loads(p.stdout.readline())
                    assert response['id'] == identifier, response
                    return response

                p.modern = modern
                if not modern:
                    exchange(0, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "rate-review", "version": "1"}})
                    p.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                    p.stdin.flush()
                accepted = exchange(1, 'tools/call', {'name': 'dry_run_command', 'arguments': {'command': 'pwd'}})
                assert 'result' in accepted, accepted
                assert accepted['result']['structuredContent']['status'] == 'SAFE', accepted
                for index, (name, args) in enumerate([
                    ('audit_path_access', {'path': 'x'}),
                    ('dry_run_command', {'command': 'pwd'}),
                    ('budget_guard', {'session_id': 'changed', 'tokens': 100000, 'consume': True}),
                    ('secret_masker', {'session_id': 'changed', 'stream_id': 'x', 'chunk': 'synthetic', 'final': False}),
                ], 2):
                    result = exchange(index, 'tools/call', {'name': name, 'arguments': args})['result']
                    assert result['isError'] and result['structuredContent']['rule'] == 'INVOCATION_RATE_LIMIT', result
                    assert json.loads(result['content'][0]['text']) == result['structuredContent']
                assert 'result' in exchange(6, 'ping', {})
            time.sleep(60.1)
            for p in processes:
                params = {'name': 'budget_guard', 'arguments': {'session_id': 'changed', 'tokens': 100000, 'consume': True}}
                if p.modern:
                    params['_meta'] = {'io.modelcontextprotocol/protocolVersion': '2026-07-28', 'io.modelcontextprotocol/clientCapabilities': {}}
                p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': params}) + '\n')
                p.stdin.flush()
                result = json.loads(p.stdout.readline())
                assert result['result']['structuredContent']['status'] == 'SAFE', result
                p.stdin.close()
                assert p.wait(timeout=5) == 0
                assert not p.stderr.read()
                p.stdout.close(); p.stderr.close()
        finally:
            watchdog.cancel()
            for p in processes:
                if p.poll() is None:
                    p.kill(); p.wait()
        http_review(executable, root)
    print(json.dumps({'http_denials': 1, 'eras': 2, 'denials': 8, 'real_minute_recoveries': 2, 'ping_recoveries': 2}))


if __name__ == '__main__':
    review(str(Path(sys.argv[1]).absolute()))

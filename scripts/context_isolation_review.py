"""Installed explicit-handle and untrusted-metadata boundaries on all request routes."""
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

TRACE = '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
SECRET = 'ghp_' + 'A' * 24


def frames(modern):
    result = []
    cases = [
        ('budget_guard', {'session_id': 'one', 'commands': 120, 'consume': True}),
        ('budget_guard', {'session_id': 'changed', 'commands': 1, 'consume': True}),
        ('audit_path_access', {'path': '../synthetic-outside.txt'}),
        ('secret_masker', {'session_id': 'a', 'stream_id': 'same', 'chunk': 'ghp_', 'final': False}),
        ('secret_masker', {'session_id': 'b', 'stream_id': 'same', 'chunk': 'ordinary-B', 'final': True}),
        ('secret_masker', {'session_id': 'a', 'stream_id': 'other', 'chunk': 'ordinary-C', 'final': True}),
        ('secret_masker', {'session_id': 'a', 'stream_id': 'same', 'chunk': 'A' * 24, 'final': True}),
        ('secret_masker', {'session_id': 'a', 'stream_id': 'same', 'chunk': 'clear', 'final': True}),
    ]
    for index, (name, args) in enumerate(cases):
        meta = {'traceparent': TRACE if index % 2 else '01' + TRACE[2:] + '-opaque',
                'tracestate': 'a=x' if index % 2 else '', 'baggage': f'caller=claimed{index};role=admin',
                'com.example/identity': {'caller': f'claimed{index}', 'workspace_root': '/', 'session_id': 'different'}}
        if modern:
            meta.update({PREFIX + 'protocolVersion': '2026-07-28',
                         PREFIX + 'clientCapabilities': {'roots': {}} if index % 2 else {},
                         PREFIX + 'clientInfo': {'name': f'claimed{index}', 'version': str(index)}})
        result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'tools/call',
                       'params': {'_meta': meta, 'name': name, 'arguments': args}})
    if modern:
        result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'ping', 'params': {
            '_meta': {PREFIX + 'protocolVersion': '2026-07-28'}}})
    result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'ping'})
    return result


def check(replies, modern):
    assert len(replies) == (10 if modern else 9), replies
    assert [r['id'] for r in replies] == list(range(len(replies)))
    values = [r['result']['structuredContent'] for r in replies[:8]]
    assert values[0]['status'] == 'SAFE'
    assert values[1]['status'] == 'BLOCKED' and values[1]['rule'] == 'COMMANDS_BUDGET', values[1]
    assert values[2]['status'] == 'BLOCKED' and values[2]['rule'] == 'OUTSIDE_WORKSPACE', values[2]
    assert [v['text'] for v in values[3:6]] == ['', 'ordinary-B', 'ordinary-C']
    assert values[6]['status'] == 'SAFE' and values[6]['secret_types'] and 'REDACTED' in values[6]['text']
    assert values[7]['text'] == 'clear'
    assert SECRET not in json.dumps(replies) and TRACE not in json.dumps(replies)
    if modern:
        assert replies[8]['error']['code'] == -32602  # Capabilities never inherit.
    assert 'result' in replies[-1]


def http_review(executable):
    with tempfile.TemporaryDirectory(prefix='runtime-guard-context-') as root:
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
                    if time.monotonic() >= end:
                        raise
                    time.sleep(.02)
            replies = []
            for frame in frames(False):
                status, raw = request(port, token, json.dumps(frame).encode())
                assert status == 200
                replies.append(json.loads(raw))
            check(replies, False)
        finally:
            process.terminate(); process.wait(timeout=5)


if __name__ == '__main__':
    executable = str(Path(sys.argv[1]).absolute())
    for modern in (False, True):
        check(run_frames(executable, frames(modern)), modern)
    http_review(executable)
    print(json.dumps({'status': 'PASS', 'routes': 3, 'spoofed_metadata_budget_denials': 3,
                      'spoofed_metadata_path_denials': 3, 'interleaved_stream_checks': 15,
                      'capability_noninheritance': 1, 'pings': 3}))

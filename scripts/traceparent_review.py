"""Installed traceparent rejection before policy effects, valid recovery on all routes."""
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

VALID = '00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01'
INVALID = [None, {}, True, '', VALID.upper(), 'ff' + VALID[2:], VALID + '-synthetic',
           VALID[:-1], VALID.replace('00f067aa0ba902b7', '0' * 16),
           VALID.replace('0af7651916cd43dd8448eb211c80319c', '0' * 32)]


def frames(modern):
    values = INVALID + [VALID, '01' + VALID[2:] + '-future']
    result = []
    for index, value in enumerate(values):
        meta = {'traceparent': value}
        if modern:
            meta.update({PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}})
        params = {'_meta': meta, 'name': 'budget_guard', 'arguments': {
            'session_id': 'trace', 'commands': 1 if index < len(INVALID) else 120 if index == len(INVALID) else 0,
            'consume': True}}
        result.append({'jsonrpc': '2.0', 'id': index, 'method': 'tools/call', 'params': params})
    result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'ping'})
    return result


def check(replies):
    assert len(replies) == len(INVALID) + 3
    for index, reply in enumerate(replies):
        assert reply['id'] == index
        if index < len(INVALID):
            assert reply['error'] == {'code': -32602, 'message': 'Invalid traceparent metadata'}, reply
        elif index < len(INVALID) + 2:
            assert reply['result']['structuredContent']['status'] == 'SAFE', reply
        else:
            assert 'result' in reply


def http_review(executable):
    with tempfile.TemporaryDirectory(prefix='runtime-guard-trace-') as root:
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
        token = secrets.token_hex(32)
        p = subprocess.Popen([executable, '--transport', 'http', '--port', str(port)], cwd=root,
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
            check(replies)
        finally:
            p.terminate(); p.wait(timeout=5)


if __name__ == '__main__':
    executable = str(Path(sys.argv[1]).absolute())
    for modern in (False, True):
        check(run_frames(executable, frames(modern)))
    http_review(executable)
    print(json.dumps({'status': 'PASS', 'routes': 3, 'invalid_rejections': 30,
                      'budget_recoveries': 3, 'future_prefix_acceptance': 3, 'pings': 3}))

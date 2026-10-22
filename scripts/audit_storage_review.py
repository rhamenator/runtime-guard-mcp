"""Installed database-ceiling and concurrent HTTP pinned-reader/WAL recovery."""
import concurrent.futures
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request


def rows(path):
    with closing(sqlite3.connect(path)) as db:
        return db.execute('SELECT * FROM decisions ORDER BY rowid').fetchall()


def review(executable, root):
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME') and not k.startswith('RUNTIME_GUARD_')}
    config, audit = root / 'config.json', root / 'audit.sqlite'
    config.write_text(json.dumps({'workspace_root': str(root), 'audit_db': str(audit), 'audit_max_db_bytes': 8192}))
    frames = [{'jsonrpc': '2.0', 'id': i, 'method': 'tools/call', 'params': {'name': 'dry_run_command', 'arguments': {'command': 'git status'}}} for i in range(30)]
    frames.append({'jsonrpc': '2.0', 'id': 30, 'method': 'ping'})
    result = subprocess.run([executable, '--config', str(config)], input=''.join(json.dumps(f) + '\n' for f in frames), text=True, capture_output=True, env=env, cwd=root, timeout=10, check=True)
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert [r['id'] for r in replies] == list(range(31))
    rules = [r['result']['structuredContent']['rule'] for r in replies[:-1]]
    assert 'AUDIT_UNAVAILABLE' in rules and set(rules) == {'READ_ONLY_COMMAND', 'AUDIT_UNAVAILABLE'}
    assert replies[-1]['result'] == {} and audit.stat().st_size <= 8192
    original = rows(audit)
    assert len(original) == rules.count('READ_ONLY_COMMAND')
    config.write_text(json.dumps({'workspace_root': str(root), 'audit_db': str(audit), 'audit_max_db_bytes': 65536, 'audit_wal_checkpoint_bytes': 4096}))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([executable, '--transport', 'http', '--port', str(port), '--config', str(config)], env=env, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    timer = threading.Timer(25, process.kill)
    timer.start()
    reader = None

    def call(method='tools/call'):
        params = {} if method == 'ping' else {'name': 'dry_run_command', 'arguments': {'command': 'git status'}}
        frame = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
        request = urllib.request.Request(f'http://127.0.0.1:{port}/mcp', data=json.dumps(frame).encode(), headers={'Content-Type': 'application/json'})
        # Each HTTP request is independent; IDs need only be unique within it.
        with urllib.request.urlopen(request, timeout=4) as response:
            reply = json.load(response)
        assert reply['id'] == 1 and 'result' in reply
        return reply['result']

    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                assert call('ping') == {}
                break
            except OSError:
                assert process.poll() is None and time.monotonic() < deadline, 'HTTP startup failed'
                time.sleep(.03)
        assert call()['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
        reader = sqlite3.connect(audit)
        reader.execute('BEGIN')
        reader.execute('SELECT * FROM decisions').fetchall()
        before = rows(audit)
        wal = Path(str(audit) + '-wal')
        before_size = wal.stat().st_size
        refused = subprocess.run([executable, '--config', str(config)], input='', text=True, capture_output=True, cwd=root, env=env, timeout=4)
        assert refused.returncode == 2 and not refused.stdout
        assert str(root) not in refused.stderr and 'Traceback' not in refused.stderr
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            denied = list(pool.map(lambda _: call(), range(4)))
        assert all(r['isError'] and r['structuredContent']['rule'] == 'AUDIT_WAL_CAPACITY' and 'READ_ONLY_COMMAND' not in r['content'][0]['text'] for r in denied)
        assert rows(audit) == before and wal.stat().st_size == before_size
        assert call('ping') == {}
        reader.rollback()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            recovered = list(pool.map(lambda _: call(), range(128)))
        assert all(r['structuredContent']['rule'] == 'READ_ONLY_COMMAND' for r in recovered)
        after = rows(audit)
        assert after[:len(original)] == original and len(after) == len(before) + 128
        assert call('ping') == {}
        return {'database_ceiling_bytes': 8192, 'initial_retained_rows': len(original), 'concurrent_denials': 4,
                'startup_refused_while_pinned': True, 'wal_unchanged_during_denials': True, 'concurrent_recovery_writes': 128, 'retained_rows': len(after), 'ping_healthy': True}
    finally:
        if reader is not None:
            reader.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        timer.cancel()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_storage_review.py INSTALLED_SERVER')
    with tempfile.TemporaryDirectory(prefix='runtime-guard-storage-') as directory:
        result = review(str(Path(sys.argv[1]).absolute()), Path(directory))
    print(json.dumps({'status': 'PASS', 'results': result, 'scope': 'finite loopback HTTP concurrency and actual SQLite page ceiling; not exact physical WAL quota or long-duration load'}, indent=2))


if __name__ == '__main__':
    main()

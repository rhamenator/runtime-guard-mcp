"""Paced, finite authenticated mixed-tool HTTP resource review (Linux)."""
import argparse
import concurrent.futures
from contextlib import closing
import json
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from sustained_resource_review import snapshot
from wfuzz_loopback_review import installed_environment, request

WORKERS, CYCLES, SECONDS, CAPACITY = 4, 128, 8, 1024


def review(executable, root, extended=False, successful_writes=False):
    cycles, seconds, cpu_limit = (2048, 120, 90) if extended else (CYCLES, SECONDS, 20)
    if successful_writes:
        cycles, seconds, cpu_limit = 256, 180, 60
    capacity = WORKERS * cycles * 3 + 1 if successful_writes else CAPACITY
    token_budget = WORKERS * cycles if successful_writes else 64
    audit, config = root / 'audit.sqlite', root / 'config.json'
    config.write_text(json.dumps({'workspace_root': str(root), 'audit_db': str(audit), 'invocations_minute': 1000000, 'audit_max_records': capacity,
                                  'audit_max_db_bytes': 8388608 if successful_writes else 1048576, 'audit_wal_checkpoint_bytes': 65536, 'token_hour': token_budget}))
    token = secrets.token_hex(32)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen([executable, '--transport', 'http', '--port', str(port), '--config', str(config)],
                               env=installed_environment(token), cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    watchdog = threading.Timer(seconds + 27, process.kill)
    watchdog.daemon = True
    watchdog.start()
    marker = 'ghp_' + 'A' * 36
    counts, lock = {}, threading.Lock()

    def call(name, arguments):
        frame = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}
        status, raw = request(port, token, json.dumps(frame).encode())
        result = json.loads(raw)['result']
        value = result['structuredContent']
        assert status == 200 and json.loads(result['content'][0]['text']) == value
        assert marker.encode() not in raw
        expected = {'budget_guard': {'WITHIN_BUDGET', 'TOKENS_BUDGET', 'AUDIT_CAPACITY'},
                    'secret_masker': {'MASKED', 'AUDIT_CAPACITY'}, 'dry_run_command': {'READ_ONLY_COMMAND', 'AUDIT_CAPACITY'}}
        if successful_writes:
            expected = {'budget_guard': {'WITHIN_BUDGET'}, 'secret_masker': {'MASKED'},
                        'dry_run_command': {'READ_ONLY_COMMAND'}}
        assert value['rule'] in expected[name]
        assert result['isError'] == (value['status'] == 'BLOCKED')
        if value['rule'] == 'AUDIT_CAPACITY':
            assert 'text' not in value and 'remaining' not in value
        with lock:
            key = name + '/' + value['rule']
            counts[key] = counts.get(key, 0) + 1

    def ping():
        status, raw = request(port, token)
        assert status == 200 and json.loads(raw).get("result") == {}

    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                ping()
                break
            except OSError:
                assert process.poll() is None and time.monotonic() < deadline
                time.sleep(.03)
        baseline = snapshot(process.pid, root)
        samples = [baseline]
        start = time.monotonic()

        initial_budget_phase = threading.Barrier(WORKERS, timeout=8)

        def worker(index):
            for cycle in range(cycles):
                call('budget_guard', {'session_id': str(index), 'tokens': 1, 'consume': True})
                call('secret_masker', {'session_id': str(index), 'stream_id': 'load', 'chunk': marker, 'final': True})
                call('dry_run_command', {'command': 'git status'})
                # Finish the first 64 reservations before audit capacity can hide
                # a completed reservation behind an audit failure.
                if cycle == 15:
                    initial_budget_phase.wait()
                time.sleep(max(0, start + (cycle + 1) * seconds / cycles - time.monotonic()))

        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(worker, index) for index in range(WORKERS)]
            while not all(f.done() for f in futures):
                assert time.monotonic() - start < seconds + 22, 'workload exceeded bounded deadline'
                samples.append(snapshot(process.pid, root))
                time.sleep(.05)
            for future in futures:
                future.result()
        elapsed = time.monotonic() - start
        time.sleep(.2)
        final = snapshot(process.pid, root)
        samples.append(final)
        ping()
        assert sum(counts.values()) == WORKERS * cycles * 3
        assert counts['budget_guard/WITHIN_BUDGET'] == token_budget
        if successful_writes:
            assert counts == {'budget_guard/WITHIN_BUDGET': WORKERS * cycles,
                              'secret_masker/MASKED': WORKERS * cycles,
                              'dry_run_command/READ_ONLY_COMMAND': WORKERS * cycles}
        else:
            assert counts.get('budget_guard/TOKENS_BUDGET', 0) > 0
            assert sum(n for k, n in counts.items() if k.endswith('/AUDIT_CAPACITY')) == WORKERS * cycles * 3 - CAPACITY
        expected_rows = WORKERS * cycles * 3 if successful_writes else CAPACITY
        with closing(sqlite3.connect(audit)) as db:
            assert db.execute('SELECT count(*) FROM decisions').fetchone()[0] == expected_rows
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert all(marker.encode() not in path.read_bytes() for path in root.glob('audit.sqlite*'))
        peak = {key: max(s[key] for s in samples) for key in baseline}
        assert peak['rss_bytes'] <= 128 * 1024 * 1024 and final['rss_bytes'] - baseline['rss_bytes'] <= 16 * 1024 * 1024
        assert peak['threads'] <= 65 and peak['fds'] <= baseline['fds'] + 32
        assert final['threads'] <= baseline['threads'] + 2 and final['fds'] <= baseline['fds'] + 2
        assert peak['disk_bytes'] <= 8 * 1024 * 1024 and final['cpu_seconds'] - baseline['cpu_seconds'] <= cpu_limit
        return {'workers': WORKERS, 'cycles_per_worker': cycles, 'target_seconds': seconds, 'cpu_limit_seconds': cpu_limit,
                'elapsed_seconds': round(elapsed, 3), 'requests': sum(counts.values()), 'counts': counts,
                'samples': len(samples), 'baseline': baseline, 'peak': peak, 'final': final,
                'audit_records': expected_rows, 'successful_write_profile': successful_writes, 'post_load_ping': True}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        watchdog.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installed_server')
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument('--successful-writes', action='store_true', help='180-second / 3,072-call all-successful audited-write profile')
    profiles.add_argument('--extended', action='store_true', help='bounded 120-second / 24,576-call profile')
    args = parser.parse_args()
    if not Path('/proc/self/status').exists():
        parser.error('Linux procfs is required')
    with tempfile.TemporaryDirectory(prefix='runtime-guard-concurrent-') as directory:
        executable, root = str(Path(args.installed_server).absolute()), Path(directory)
        results = review(executable, root, args.extended, args.successful_writes)
        restarted = subprocess.run([executable, '--config', str(root / 'config.json')],
                                   input='{"jsonrpc":"2.0","id":1,"method":"ping"}\n', text=True,
                                   env=installed_environment(''), cwd=root, capture_output=True, timeout=6, check=True)
        assert json.loads(restarted.stdout) == {'jsonrpc': '2.0', 'id': 1, 'result': {}}
        results['restart_integrity_ping'] = True
    print(json.dumps({'status': 'PASS', 'results': results,
                      'scope': 'finite paced four-worker loopback HTTP workload; not long-duration soak, latency guarantee, multi-user isolation or exact physical quota'}, indent=2))


if __name__ == '__main__':
    main()

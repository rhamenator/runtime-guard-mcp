"""Bounded POSIX process-kill recovery under installed HTTP audit traffic."""
from stdio_review_helpers import handshake_frames
import argparse
from contextlib import closing
import json
import http.client
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
from wfuzz_loopback_review import installed_environment, request


def review(executable):
    results = []
    with tempfile.TemporaryDirectory(prefix='runtime-guard-kill-') as directory:
        root = Path(directory)
        for iteration in range(8):
            audit = root / f'audit-{iteration}.sqlite'
            config = root / 'config.json'
            config.write_text(json.dumps({'workspace_root': str(root), 'audit_db': str(audit),
                                          'invocations_minute': 1000000}))
            token = secrets.token_hex(32)
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            process = subprocess.Popen([executable, '--transport', 'http', '--port', str(port), '--config', str(config)],
                                       env=installed_environment(token), cwd=root,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            stop, ready = threading.Event(), threading.Event()
            acknowledged, failures = [], []
            frame = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                'params': {'name': 'dry_run_command', 'arguments': {'command': 'git status'}}}).encode()

            def writer():
                try:
                    for _ in range(256):
                        if stop.is_set():
                            break
                        status, raw = request(port, token, frame)
                        value = json.loads(raw)['result']['structuredContent']
                        assert status == 200 and value['rule'] == 'READ_ONLY_COMMAND'
                        acknowledged.append(True)
                        if len(acknowledged) >= 8:
                            ready.set()
                except (OSError, http.client.HTTPException) as error:
                    if not stop.is_set():
                        failures.append(type(error).__name__)
                    ready.set()
                except Exception as error:
                    failures.append(type(error).__name__)
                    ready.set()

            thread = threading.Thread(target=writer, daemon=True)
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
                thread.start()
                assert ready.wait(8) and not failures and len(acknowledged) >= 8
                # Vary the kill point while requests continue; this does not
                # guarantee interruption inside SQLite's commit syscall.
                time.sleep(iteration * .001)
                stop.set()
                process.kill()
                process.wait(timeout=3)
                thread.join(timeout=4)
                assert not thread.is_alive() and not failures
                assert process.returncode == -9
                with closing(sqlite3.connect(audit)) as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    rows = db.execute('SELECT count(*) FROM decisions').fetchone()[0]
                assert len(acknowledged) <= rows <= len(acknowledged) + 1
                recovery_frame = ''.join(json.dumps(f) + '\n' for f in handshake_frames()) + frame.decode()
                restarted = subprocess.run([executable, '--config', str(config)],
                                           input=recovery_frame + '\n', text=True, capture_output=True,
                                           env=installed_environment(''), cwd=root, timeout=8, check=True)
                assert json.loads(restarted.stdout.splitlines()[-1])['result']['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
                with closing(sqlite3.connect(audit)) as db:
                    assert db.execute('SELECT count(*) FROM decisions').fetchone()[0] == rows + 1
                results.append({'iteration': iteration, 'acknowledged': len(acknowledged),
                                'recovered_rows': rows, 'restart_verified_and_writable': True})
            finally:
                stop.set()
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                if thread.ident is not None:
                    thread.join(timeout=4)
    return {'status': 'PASS', 'iterations': results,
            'scope': 'owned server SIGKILL under sequential audit traffic; not power loss, exact commit interruption or portable state recovery'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installed_server')
    args = parser.parse_args()
    print(json.dumps(review(str(Path(args.installed_server).absolute())), indent=2))

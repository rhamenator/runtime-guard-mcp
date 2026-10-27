"""Installed cancellation of a completed policy result waiting behind a blocked pipe."""
from stdio_review_helpers import initialize_legacy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from wfuzz_loopback_review import installed_environment

PREFIX = 'io.modelcontextprotocol/'


def review(executable, root, modern):
    audit, config = root / 'audit.sqlite', root / 'config.json'
    config.write_text(json.dumps({'workspace_root': str(root), 'audit_db': str(audit), 'token_hour': 1}))
    process = subprocess.Popen([executable, '--config', str(config)], cwd=root,
                               env=installed_environment(''), stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not modern:
        initialize_legacy(process)

    def call(identifier, name, arguments):
        params = {'name': name, 'arguments': arguments}
        if modern:
            params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
        return {'jsonrpc': '2.0', 'id': identifier, 'method': 'tools/call', 'params': params}

    def send(frames):
        process.stdin.write(b''.join(json.dumps(f).encode() + b'\n' for f in frames))
        process.stdin.flush()

    def audited(count, end):
        while time.monotonic() < end:
            with closing(sqlite3.connect(audit, timeout=.1)) as db:
                if db.execute('SELECT count(*) FROM decisions').fetchone()[0] == count:
                    return
            assert process.poll() is None
            time.sleep(.01)
        raise AssertionError('policy progress marker timed out')

    try:
        send([{'jsonrpc': '2.0', 'id': 0, 'method': 'ping'}])
        assert json.loads(process.stdout.readline())['result'] == {}
        send([call(1, 'secret_masker', {'session_id': 'queue', 'stream_id': 'blocker', 'chunk': 'x' * 524288, 'final': True}),
              call(2, 'budget_guard', {'session_id': 'queue', 'tokens': 1, 'consume': True}),
              call(3, 'dry_run_command', {'command': 'git status'})])
        end = time.monotonic() + 3
        # Audit 3 proves worker 2 finished; its response cannot pass frame 1's full pipe.
        audited(3, end)
        send([{'jsonrpc': '2.0', 'method': 'notifications/cancelled', 'params': {'requestId': 2}},
              call(4, 'dry_run_command', {'command': 'git status'}),
              call(5, 'budget_guard', {'session_id': 'queue', 'tokens': 1, 'consume': True})])
        # Audit 5 proves the cancellation was read before stdout is drained.
        audited(5, end)
        raw, error = process.communicate(timeout=7)
        assert process.returncode == 0 and not error
        replies = [json.loads(line) for line in raw.splitlines()]
        assert [r['id'] for r in replies] == [1, 3, 4, 5]
        assert replies[0]['result']['structuredContent']['text'] == 'x' * 524288
        assert replies[-1]['result']['structuredContent']['rule'] == 'TOKENS_BUDGET'
        assert replies[-1]['result']['isError'] is True
        restarted = subprocess.run([executable, '--config', str(config)], cwd=root,
                                   env=installed_environment(''), capture_output=True,
                                   input=b'{"jsonrpc":"2.0","id":0,"method":"ping"}\n', timeout=6, check=True)
        assert json.loads(restarted.stdout)['result'] == {} and not restarted.stderr
        return {'era': 'modern' if modern else 'legacy', 'response_ids': [1, 3, 4, 5],
                'cancelled_queued_response': 2, 'audit_records': 5, 'budget_not_rolled_back': True,
                'restart_integrity_ping': True}
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=3)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: queued_cancellation_review.py INSTALLED_SERVER')
    results = []
    for modern in (False, True):
        with tempfile.TemporaryDirectory(prefix='runtime-guard-queued-cancel-') as directory:
            results.append(review(str(Path(sys.argv[1]).absolute()), Path(directory), modern))
    print(json.dumps({'status': 'PASS', 'results': results,
                      'scope': 'queued output cancellation; cannot retract a frame whose write already began or roll back policy state'}, indent=2))


if __name__ == '__main__':
    main()

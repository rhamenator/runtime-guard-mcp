"""Installed stdio stalled/disconnected reader and resumed-reading probes."""
from stdio_review_helpers import initialize_legacy
import json
from pathlib import Path
import subprocess
import sqlite3
from contextlib import closing
import sys
import tempfile
import time
from wfuzz_loopback_review import installed_environment

PREFIX = 'io.modelcontextprotocol/'


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: output_backpressure_review.py INSTALLED_SERVER')
    results = []
    with tempfile.TemporaryDirectory(prefix='runtime-guard-output-') as root:
        for modern in (False, True):
            for scenario in ('stalled', 'stalled-eof', 'disconnected', 'resumed'):
                executable = str(Path(sys.argv[1]).absolute())
                audit = Path(root) / (str(modern) + '-' + scenario + '.sqlite')
                config = audit.with_suffix('.json')
                config.write_text(json.dumps({'workspace_root': root, 'audit_db': str(audit)}))
                process = subprocess.Popen([executable, '--config', str(config)], cwd=root,
                                           env=installed_environment(''), stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    if not modern:
                        initialize_legacy(process)
                    process.stdin.write(b'{"jsonrpc":"2.0","id":0,"method":"ping"}\n'); process.stdin.flush()
                    assert json.loads(process.stdout.readline())['result'] == {}
                    params = {'name': 'secret_masker', 'arguments': {'session_id': 'pressure', 'stream_id': 'one',
                                                                   'chunk': 'x' * 524288, 'final': True}}
                    if modern:
                        params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
                    frame = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': params}
                    start = time.monotonic()
                    process.stdin.write(json.dumps(frame).encode() + b'\n'); process.stdin.flush()
                    if scenario == 'resumed':
                        time.sleep(.25)
                        raw, error = process.communicate(b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n', timeout=8)
                        replies = [json.loads(line) for line in raw.splitlines()]
                        assert process.returncode == 0 and not error
                        assert [r['id'] for r in replies] == [1, 2]
                        result = replies[0]['result']
                        assert result['structuredContent']['text'] == 'x' * 524288
                        assert json.loads(result['content'][0]['text']) == result['structuredContent']
                        assert replies[1]['result'] == {}
                    else:
                        if scenario == 'stalled-eof':
                            process.stdin.close()
                        if scenario == 'disconnected':
                            process.stdout.close()
                        # Keep stdin open: output failure must end even an idle-input session.
                        process.wait(timeout=8)
                        assert process.returncode == 2, process.returncode
                        assert not process.stderr.read(), 'transport failure leaked a traceback/diagnostic'
                    with closing(sqlite3.connect(audit)) as db:
                        assert db.execute('SELECT count(*) FROM decisions').fetchone()[0] == 1
                        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    restarted = subprocess.run([executable, '--config', str(config)], cwd=root,
                                               env=installed_environment(''), capture_output=True, timeout=6,
                                               input=b'{"jsonrpc":"2.0","id":0,"method":"ping"}\n', check=True)
                    assert json.loads(restarted.stdout)['result'] == {} and not restarted.stderr
                    results.append({'era': 'modern' if modern else 'legacy', 'scenario': scenario,
                                    'audit_records': 1, 'restart_integrity_ping': True,
                                    'exit_code': process.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3)})
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=3)
                    for pipe in (process.stdin, process.stdout, process.stderr):
                        if pipe and not pipe.closed:
                            pipe.close()
    print(json.dumps({'status': 'PASS', 'results': results,
                      'scope': 'installed anonymous-pipe backpressure/disconnect/recovery; no whole-agent enforcement or state rollback'}, indent=2))


if __name__ == '__main__':
    main()

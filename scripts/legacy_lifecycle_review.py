"""Bounded legacy stdio handshake/state-preservation and modern interleaving review."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

PREFIX = 'io.modelcontextprotocol/'


def review(launcher, source_path=None):
    def request(identifier, method, **params):
        return {'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params}
    def notify(params=None):
        return {'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {} if params is None else params}
    budget = {'name': 'budget_guard', 'arguments': {'session_id': 'owner', 'tokens': 1, 'consume': True}}
    meta = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
    initialize = {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'fixture', 'version': '1'}}
    frames = [notify(), request(1, 'tools/call', **budget),
              request(2, 'tools/call', name='secret_masker', arguments={'session_id': 'owner', 'stream_id': 'stream', 'chunk': 'SyntheticPass123!', 'final': False}),
              request(3, 'tools/list'), request(4, 'tools/call', _meta=meta, name='dry_run_command', arguments={'command': 'git status'}),
              request(5, 'initialize', protocolVersion='2025-06-18'), request(6, 'tools/list'),
              request(7, 'initialize', **initialize), request(8, 'tools/call', **budget),
              {'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': None}, request(9, 'tools/call', **budget),
              notify({'_meta': {'traceparent': 'synthetic-private-marker'}}), request(10, 'tools/list'),
              notify({'_meta': meta}), request(11, 'tools/list'), notify(), request(12, 'tools/call', **budget),
              request(13, 'tools/call', name='secret_masker', arguments={'session_id': 'owner', 'stream_id': 'stream', 'chunk': '', 'final': True}),
              request(14, 'initialize', **initialize), notify(), request(15, 'ping', _meta=meta),
              request(16, 'tools/call', **budget)]
    with tempfile.TemporaryDirectory(prefix='runtime-guard-lifecycle-') as directory:
        root = Path(directory)
        audit = root / 'audit.sqlite'
        config = root / 'config.json'
        config.write_text(json.dumps({'workspace_root': directory, 'audit_db': str(audit), 'token_hour': 1, 'invocations_minute': 3}))
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME') and not k.startswith('RUNTIME_GUARD_')}
        if source_path:
            env['PYTHONPATH'] = str(source_path)
        result = subprocess.run([*launcher, '--config', str(config)], input=''.join(json.dumps(f) + '\n' for f in frames),
                                text=True, capture_output=True, cwd=root, env=env, timeout=10, check=True)
        assert not result.stderr
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        assert [r['id'] for r in replies] == list(range(1, 17))
        indexed = {r['id']: r for r in replies}
        for identifier in (1, 2, 3, 6, 8, 9, 10, 11):
            assert indexed[identifier]['error']['code'] == 1002
        assert indexed[5]['error']['code'] == -32602
        assert indexed[14]['error']['code'] == -32600
        assert indexed[4]['result']['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
        assert indexed[7]['result']['protocolVersion'] == '2025-06-18'
        assert indexed[12]['result']['structuredContent']['rule'] == 'WITHIN_BUDGET'
        assert indexed[13]['result']['structuredContent']['text'] == ''
        assert indexed[15]['result']['resultType'] == 'complete'
        assert indexed[16]['result']['structuredContent']['rule'] == 'INVOCATION_RATE_LIMIT'
        assert 'synthetic-private-marker' not in result.stdout
        with sqlite3.connect(audit) as connection:
            assert connection.execute('SELECT count(*) FROM decisions').fetchone()[0] == 3
    return {'status': 'PASS', 'rejected_legacy_tools': 8, 'audit_decisions': 3,
            'budget_masker_invocation_state_preserved': True, 'modern_interleaving': True,
            'malformed_early_modern_and_duplicate_notifications': True,
            'scope': 'stdio worker admission; legacy HTTP remains custom JSON-RPC; no policy rollback or transport delivery acknowledgement guarantee'}


if __name__ == '__main__':
    assert len(sys.argv) == 2, 'usage: legacy_lifecycle_review.py INSTALLED_SERVER'
    print(json.dumps(review([str(Path(sys.argv[1]).absolute())]), indent=2))

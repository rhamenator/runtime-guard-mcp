"""Installed stdio review of modern capability validation and terminal pagination."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PREFIX = 'io.modelcontextprotocol/'
INVALID = [
    {'experimental': {'synthetic-marker': True}}, {'extensions': {'synthetic-marker': {}}},
    {'extensions': {'com.example/invalid!': {}}}, {'extensions': {'com.example/probe': []}},
    {'sampling': {'tools': False}}, {'sampling': {'context': None}},
    {'elicitation': {'form': []}}, {'elicitation': {'url': 1}},
]


def run_frames(executable, frames, config=None):
    with tempfile.TemporaryDirectory(prefix='runtime-guard-modern-validation-') as root:
        env = {key: value for key, value in os.environ.items() if key not in ('PYTHONPATH', 'PYTHONHOME') and not key.startswith('RUNTIME_GUARD_')}
        env['RUNTIME_GUARD_WORKSPACE_ROOT'] = root
        command = [str(Path(executable).absolute())]
        if config is not None:
            config_path = Path(root) / "config.json"
            config_path.write_text(json.dumps(config))
            command.extend(["--config", str(config_path)])
        result = subprocess.run(command, input=''.join(json.dumps(frame) + '\n' for frame in frames), text=True, capture_output=True, cwd=root, env=env, timeout=15, check=True)
    return [json.loads(line) for line in result.stdout.splitlines()]


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: modern_validation_review.py INSTALLED_SERVER')
    frames = []

    def append(method, capabilities=None, modern=True, **params):
        if modern:
            params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': capabilities or {}}
        frames.append({'jsonrpc': '2.0', 'id': len(frames) + 1, 'method': method, 'params': params})

    for capabilities in INVALID:
        append('tools/call', capabilities, name='budget_guard', arguments={'session_id': 'review', 'commands': 1, 'consume': True})
    for modern in (True, False):
        for cursor in ('', 'synthetic-marker', 1, None, [], {}):
            append('tools/list', modern=modern, cursor=cursor)
    rejected = len(frames)
    append('tools/call', name='budget_guard', arguments={'session_id': 'review', 'commands': 120, 'consume': True})
    append('tools/list', {'extensions': {'com.example/probe': {'custom': [True]}}, 'sampling': {'tools': {}, 'context': {}}, 'elicitation': {'form': {}, 'url': {}}, 'experimental': {'custom': {}}})
    append('ping')
    append('ping', modern=False)
    replies = run_frames(sys.argv[1], frames)
    assert [reply['id'] for reply in replies] == list(range(1, len(frames) + 1))
    assert all(reply['error']['code'] == -32602 for reply in replies[:rejected])
    assert 'synthetic-marker' not in json.dumps(replies[:rejected])
    assert replies[rejected]['result']['structuredContent']['status'] == 'SAFE'
    listing = replies[rejected + 1]['result']
    assert len(listing['tools']) == 4 and 'nextCursor' not in listing
    assert listing['ttlMs'] == 0 and listing['cacheScope'] == 'private'
    assert replies[-2]['result']['resultType'] == 'complete' and replies[-1]['result'] == {}
    print(json.dumps({'status': 'PASS', 'rejected_frames': rejected, 'recovery_frames': 4,
                      'budget_preserved': True, 'legacy_interleave': True, 'terminal_page': True}))


if __name__ == '__main__':
    main()

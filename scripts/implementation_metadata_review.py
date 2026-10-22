"""Installed modern optional client-metadata shape and recovery review."""
import json
import sys
from modern_validation_review import PREFIX, run_frames

INVALID = [
    {'description': []}, {'websiteUrl': 1}, {'icons': {}}, {'icons': [None]},
    {'icons': [{}]}, {'icons': [{'src': False}]}, {'icons': [{'src': 'x', 'mimeType': []}]},
    {'icons': [{'src': 'x', 'sizes': 'any'}]}, {'icons': [{'src': 'x', 'sizes': [1]}]},
    {'icons': [{'src': 'x', 'theme': 'synthetic-marker'}]},
]


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: implementation_metadata_review.py INSTALLED_SERVER')
    frames = []
    for fields in INVALID + [{'description': 'Untrusted', 'websiteUrl': 'https://example.invalid',
                              'icons': [{'src': 'data:image/svg+xml,synthetic-marker', 'mimeType': 'image/svg+xml', 'sizes': ['any'], 'theme': 'dark'}]}]:
        params = {'name': 'budget_guard', 'arguments': {'session_id': 'metadata', 'commands': 1 if fields in INVALID else 120, 'consume': True},
                  '_meta': {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {},
                            PREFIX + 'clientInfo': {'name': 'synthetic-marker', 'version': '1', **fields}}}
        frames.append({'jsonrpc': '2.0', 'id': len(frames) + 1, 'method': 'tools/call', 'params': params})
    frames.append({'jsonrpc': '2.0', 'id': len(frames) + 1, 'method': 'ping'})
    replies = run_frames(sys.argv[1], frames)
    assert [r['id'] for r in replies] == list(range(1, len(frames) + 1))
    assert all(r['error']['code'] == -32602 for r in replies[:len(INVALID)])
    assert replies[-2]['result']['structuredContent']['status'] == 'SAFE'
    assert replies[-1]['result'] == {}
    assert 'synthetic-marker' not in json.dumps(replies)
    print(json.dumps({'status': 'PASS', 'rejected_frames': len(INVALID), 'recovery_frames': 2, 'budget_preserved': True,
                      'scope': 'modern metadata shapes; untrusted identity and icon values not reflected; no URI fetching or rendering implemented'}))


if __name__ == '__main__':
    main()

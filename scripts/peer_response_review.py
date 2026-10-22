"""Installed stdio response/request classification and recovery review."""
import json
import sys
from modern_validation_review import PREFIX, run_frames


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: peer_response_review.py INSTALLED_SERVER')
    peer = [
        {'jsonrpc': '2.0', 'id': 1, 'result': {'resultType': 'complete', 'marker': 'synthetic-marker'}},
        {'jsonrpc': '2.0', 'id': 'peer', 'result': {}},
        {'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32600, 'message': 'synthetic-marker'}},
        {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'synthetic-marker'}},
        {'jsonrpc': '2.0', 'error': {'code': -32600, 'message': 'synthetic-marker'}},
    ]
    frames = peer * 40
    frames.append({'jsonrpc': '2.0', 'id': 2})  # A malformed request must still fail.
    frames.append({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
        '_meta': {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}},
        'name': 'budget_guard', 'arguments': {'session_id': 'peer', 'commands': 120, 'consume': True}}})
    frames.append({'jsonrpc': '2.0', 'id': 3, 'method': 'ping'})
    replies = run_frames(sys.argv[1], frames)
    assert [r['id'] for r in replies] == [2, 1, 3]
    assert replies[0]['error']['code'] == -32600
    assert replies[1]['result']['structuredContent']['status'] == 'SAFE'
    assert replies[2]['result'] == {}
    assert 'synthetic-marker' not in json.dumps(replies)
    print(json.dumps({'status': 'PASS', 'ignored_peer_responses': len(peer) * 40,
                      'malformed_request_errors': 1, 'recovery_frames': 2, 'budget_preserved': True,
                      'scope': 'stdio uncorrelated response boundary; not outbound request correlation or full schema certification'}))


if __name__ == '__main__':
    main()

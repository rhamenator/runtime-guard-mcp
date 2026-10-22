"""Installed modern unsolicited continuation rejection and budget recovery."""
import json
import sys
from modern_validation_review import PREFIX, run_frames


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: request_state_review.py INSTALLED_SERVER')
    frames = []

    def append(method='tools/call', **extra):
        params = {'_meta': {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}}
        if method == 'tools/call':
            params.update(name='budget_guard', arguments={'session_id': 'resume', 'commands': 1, 'consume': True})
        params.update(extra)
        frames.append({'jsonrpc': '2.0', 'id': len(frames) + 1, 'method': method, 'params': params})

    for state in ('', 'synthetic-marker', '{"approved":true}', None, False, [], {}):
        append(requestState=state)
    for responses in (None, [], False, 'synthetic-marker'):
        append(inputResponses=responses)
    for method in ('ping', 'tools/list', 'server/discover'):
        append(method, requestState='')
    rejected = len(frames)
    append(inputResponses={'unknown': {'resultType': 'complete', 'synthetic-marker': True}},
           arguments={'session_id': 'resume', 'commands': 120, 'consume': True})
    frames.append({'jsonrpc': '2.0', 'id': len(frames) + 1, 'method': 'ping'})
    replies = run_frames(sys.argv[1], frames)
    assert [r['id'] for r in replies] == list(range(1, len(frames) + 1))
    assert all(r['error']['code'] == -32602 for r in replies[:rejected])
    assert replies[-2]['result']['structuredContent']['status'] == 'SAFE'
    assert replies[-1]['result'] == {}
    assert 'synthetic-marker' not in json.dumps(replies)
    print(json.dumps({'status': 'PASS', 'rejected_frames': rejected, 'recovery_frames': 2,
                      'budget_preserved': True, 'unknown_input_responses_ignored': True,
                      'scope': 'server issues no resumable state; not multi-round-trip execution or state replay protection for a resumable service'}))


if __name__ == '__main__':
    main()

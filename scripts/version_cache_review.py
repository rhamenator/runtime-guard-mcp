"""Installed modern discovery/version/cache policy and legacy interleaving review."""
import json
from pathlib import Path
import sys
from modern_validation_review import PREFIX, run_frames


def frames():
    result = []
    def add(method, params=None, version='2026-07-28', caps=None):
        body = dict(params or {})
        body['_meta'] = {PREFIX + 'protocolVersion': version, PREFIX + 'clientCapabilities': caps or {}}
        result.append({'jsonrpc': '2.0', 'id': len(result), 'method': method, 'params': body})
    add('tools/list', version='1900-01-01')
    add('server/discover')
    add('tools/list')
    add('tools/list', caps={'extensions': {'com.example/unsupported': {}}})
    add('tools/call', {'name': 'dry_run_command', 'arguments': {'command': 'pwd'}})
    add('tools/call', {'name': 'audit_path_access', 'arguments': {'path': 'visible.txt'}})
    result[-1]['params']['_meta']['com.example/cachedTools'] = ['audit_path_access']
    add('tools/list')
    result[-1]['params']['_meta']['com.example/cacheScope'] = 'public'
    result[-1]['params']['_meta']['com.example/ttlMs'] = 86400000
    add('server/discover')
    result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'initialize', 'params': {
        'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'review', 'version': '1'}}})
    result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'tools/list'})
    add('tools/list')
    add('tools/call', {'name': 'dry_run_command', 'arguments': {'command': 'pwd'}},
        caps={'extensions': {'com.example/unsupported': {}}})
    add('ping', version='1900-01-01')
    add('ping')
    add('tools/list')
    del result[-1]['params']['_meta'][PREFIX + 'clientCapabilities']
    result.append({'jsonrpc': '2.0', 'id': len(result), 'method': 'ping'})
    return result


def check(replies, restricted):
    assert len(replies) == 16 and [r['id'] for r in replies] == list(range(16))
    versions = replies[1]['result']['supportedVersions']
    assert {'2026-07-28', '2025-06-18'}.issubset(versions)
    for i in (0, 12):
        assert replies[i]['error']['code'] == -32022
        assert replies[i]['error']['data'] == {'supported': versions, 'requested': '1900-01-01'}
    for i in (1, 2, 3, 6, 7, 10):
        value = replies[i]['result']
        assert value['resultType'] == 'complete'
        assert type(value['ttlMs']) is int and value['ttlMs'] == 0 and value['cacheScope'] == 'private'
        assert PREFIX + 'serverInfo' in value['_meta']
    for i in (1, 7):
        assert replies[i]['result']['capabilities'] == {'tools': {}}
    names = [t['name'] for t in replies[2]['result']['tools']]
    assert names == sorted(names) and len(names) == (1 if restricted else 4)
    for i in (3, 6, 10):
        assert replies[i]['result']['tools'] == replies[2]['result']['tools']
    for i in (4, 11):
        assert replies[i]['result']['structuredContent']['status'] == 'SAFE'
    if restricted:
        assert names == ['dry_run_command'] and replies[5]['error']['code'] == -32602
    else:
        assert replies[5]['result']['structuredContent']['status'] == 'SAFE'
    assert replies[8]['result']['protocolVersion'] == '2025-06-18'
    assert 'ttlMs' not in replies[9]['result'] and 'resultType' not in replies[9]['result']
    assert sorted(t['name'] for t in replies[9]['result']['tools']) == names
    assert replies[13]['result']['resultType'] == 'complete'
    assert replies[14]['error']['code'] == -32602
    assert replies[15]['result'] == {}


if __name__ == '__main__':
    executable = str(Path(sys.argv[1]).absolute())
    for restricted in (False, True):
        config = {'enabled_tools': ['dry_run_command']} if restricted else None
        check(run_frames(executable, frames(), config), restricted)
    print(json.dumps({'status': 'PASS', 'configurations': 2, 'rpc_replies': 32,
                      'cache_hint_checks': 12, 'version_mismatch_recoveries': 4,
                      'legacy_modern_interleavings': 2, 'filtered_tool_denial': 1,
                      'unsupported_extension_core_fallbacks': 4}))

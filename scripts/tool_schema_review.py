"""Validate installed tool declarations/results with an independent JSON Schema engine."""
from stdio_review_helpers import initialize_legacy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.exceptions import NoSuchResource
from schema_policy import check_offline_schema
from wfuzz_loopback_review import installed_environment

PREFIX = 'io.modelcontextprotocol/'


def refuse_retrieval(uri):
    # Never include an untrusted URI in a diagnostic or attempt I/O.
    raise NoSuchResource(ref='offline-schema-retrieval-disabled')


def offline_validator(schema):
    check_offline_schema(schema)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=Registry(retrieve=refuse_retrieval))


def review(executable, root, modern):
    config, audit = root / 'config.json', root / 'audit.sqlite'
    config.write_text(json.dumps({'workspace_root': str(root), 'token_hour': 1,
                                  'audit_db': str(audit), 'audit_max_records': 12}))
    process = subprocess.Popen([executable, '--config', str(config)], cwd=root,
                               env=installed_environment(''), stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    watchdog = threading.Timer(15, process.kill)
    watchdog.daemon = True
    watchdog.start()
    identifier = 0

    def rpc(method, **params):
        nonlocal identifier
        identifier += 1
        if modern:
            params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
        process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params}).encode() + b'\n')
        process.stdin.flush()
        response = json.loads(process.stdout.readline())
        assert response['jsonrpc'] == '2.0' and response['id'] == identifier
        return response

    try:
        if not modern:
            initialize_legacy(process)
        tools = rpc('tools/list')['result']['tools']
        assert {t['name'] for t in tools} == {'audit_path_access', 'dry_run_command', 'budget_guard', 'secret_masker'}
        validators = {}
        for tool in tools:
            validators[tool['name']] = (offline_validator(tool['inputSchema']), offline_validator(tool['outputSchema']))
        invalid = [('audit_path_access', {'path': 7}), ('dry_run_command', {'command': []}),
                   ('budget_guard', {'session_id': 's', 'tokens': True}),
                   ('secret_masker', {'session_id': 's', 'stream_id': 's', 'chunk': '', 'final': 'yes'})]
        for name, arguments in invalid:
            assert not validators[name][0].is_valid(arguments)
            assert rpc('tools/call', name=name, arguments=arguments)['error']['code'] == -32602
        secret = 'ghp_' + 'A' * 24
        cases = [
            ('audit_path_access', {'path': 'safe.txt'}, 'SAFE'),
            ('audit_path_access', {'path': 'safe.txt', 'operation': 'delete'}, 'NEEDS_CONFIRMATION'),
            ('audit_path_access', {'path': '.env'}, 'BLOCKED'),
            ('dry_run_command', {'command': 'git status'}, 'SAFE'),
            ('dry_run_command', {'command': 'rm -rf /'}, 'BLOCKED'),
            ('dry_run_command', {'command': 'python app.py'}, 'NEEDS_CONFIRMATION'),
            ('budget_guard', {'session_id': 's', 'tokens': 1, 'consume': True}, 'SAFE'),
            ('budget_guard', {'session_id': 's', 'tokens': 1}, 'BLOCKED'),
            ('budget_guard', {'session_id': 's', 'tokens': 10000001}, 'BLOCKED'),
            ('secret_masker', {'session_id': 's', 'stream_id': 'one', 'chunk': secret, 'final': True}, 'SAFE'),
            ('secret_masker', {'session_id': 's', 'stream_id': 'split', 'chunk': 'ghp_', 'final': False}, 'SAFE'),
            ('secret_masker', {'session_id': 's', 'stream_id': 'split', 'chunk': 'A' * 24, 'final': True}, 'SAFE'),
        ]
        statuses, rules = set(), set()

        def check(name, arguments, status, capacity=False):
            validators[name][0].validate(arguments)
            result = rpc('tools/call', name=name, arguments=arguments)['result']
            value = result['structuredContent']
            validators[name][1].validate(value)
            assert value['status'] == status and result['isError'] == (status == 'BLOCKED')
            assert json.loads(result['content'][0]['text']) == value
            assert secret not in json.dumps(result)
            if modern:
                assert result['resultType'] == 'complete' and PREFIX + 'serverInfo' in result['_meta']
            if capacity:
                assert value['rule'] == 'AUDIT_CAPACITY' and 'text' not in value and 'remaining' not in value
            statuses.add(status); rules.add(value['rule'])

        for name, arguments, status in cases:
            check(name, arguments, status)
        # Audit failure must still obey each tool's advertised output schema.
        for name, arguments, _ in (cases[0], cases[3], cases[7], cases[9]):
            check(name, arguments, 'BLOCKED', capacity=True)
        assert rpc('tools/call', name='synthetic-unknown', arguments={})['error']['code'] == -32602
        assert rpc('synthetic/unknown')['error']['code'] == -32601
        assert 'result' in rpc('ping')
        with closing(sqlite3.connect(audit)) as db:
            assert db.execute('SELECT count(*) FROM decisions').fetchone()[0] == 12
        assert all(secret.encode() not in p.read_bytes() for p in root.glob('audit.sqlite*'))
        return {'era': 'modern' if modern else 'legacy', 'schemas_checked': 8, 'tool_results_validated': 16,
                'invalid_input_errors': 4, 'unknown_method_tool_errors': 2, 'statuses': sorted(statuses),
                'rules': sorted(rules), 'audit_records': 12, 'recovery_ping': True}
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate(timeout=3)
        watchdog.cancel()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: tool_schema_review.py INSTALLED_SERVER')
    results = []
    for modern in (False, True):
        with tempfile.TemporaryDirectory(prefix='runtime-guard-tool-schema-') as directory:
            results.append(review(str(Path(sys.argv[1]).absolute()), Path(directory), modern))
    print(json.dumps({'status': 'PASS', 'validator': 'jsonschema Draft202012Validator', 'results': results,
                      'scope': 'finite installed tool schema/result fixtures; not full MCP normative certification or exhaustive policy coverage'}, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Bounded authenticated Cursor ACP test; uses existing login and synthetic files."""

import argparse
import json
import os
from pathlib import Path
import queue
import shlex
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time


def run(server: str, client: str) -> dict:
    server = str(Path(server).resolve())
    version = subprocess.run([client, '--version'], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='runtime-guard-cursor-') as temporary:
        root = Path(temporary)
        config = root / 'guard.json'
        audit = root / 'audit.sqlite'
        settings = {'workspace_root': str(root), 'audit_db': str(audit)}
        config.write_text(json.dumps(settings))
        entry = {'command': server, 'args': [], 'env': {'RUNTIME_GUARD_CONFIG': str(config)}}
        (root / '.cursor').mkdir()
        (root / '.cursor' / 'mcp.json').write_text(json.dumps({'mcpServers': {'runtime_guard': entry}}))
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        environment.pop('PYTHONHOME', None)
        subprocess.run([client, 'mcp', 'enable', 'runtime_guard'], cwd=root, env=environment, capture_output=True, text=True, timeout=15, check=True)
        discovery = subprocess.run([client, 'mcp', 'list-tools', 'runtime_guard'], cwd=root, env=environment, capture_output=True, text=True, timeout=30)
        names = ('audit_path_access', 'dry_run_command', 'budget_guard', 'secret_masker')
        if discovery.returncode or not all(name in discovery.stdout for name in names):
            raise AssertionError('Cursor did not discover all four tools')
        settings['enabled_tools'] = ['dry_run_command']
        config.write_text(json.dumps(settings))
        sentinel = root / 'sentinel.txt'
        sentinel.write_text('preserve fixture')
        process = subprocess.Popen([client, '--approve-mcps', '--trust', 'acp'], cwd=root, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1, start_new_session=True)
        messages = queue.Queue(maxsize=256)
        def read():
            for line in process.stdout:
                try:
                    messages.put(json.loads(line))
                except ValueError:
                    pass
        threading.Thread(target=read, daemon=True).start()
        def send(message):
            process.stdin.write(json.dumps(message) + '\n')
            process.stdin.flush()
        permissions = []
        deadline = time.monotonic() + 90
        def response(identifier):
            while time.monotonic() < deadline:
                try:
                    message = messages.get(timeout=min(1, max(0.01, deadline - time.monotonic())))
                except queue.Empty:
                    if process.poll() is not None:
                        raise AssertionError('Cursor exited before completing the probe')
                    continue
                if message.get('method') == 'session/request_permission':
                    params = message['params']
                    title = params['toolCall'].get('title', '')
                    allow = 'dry_run_command' in title
                    kind = 'allow_once' if allow else 'reject_once'
                    option = next(option for option in params['options'] if option['kind'] == kind)
                    permissions.append(allow)
                    send({'jsonrpc': '2.0', 'id': message['id'], 'result': {'outcome': {'outcome': 'selected', 'optionId': option['optionId']}}})
                elif message.get('id') == identifier and 'method' not in message:
                    if 'error' in message:
                        raise AssertionError('Cursor returned an ACP error')
                    return message['result']
            raise AssertionError('Cursor probe exceeded its 90-second deadline')
        try:
            send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': 1, 'clientCapabilities': {}}})
            response(1)
            send({'jsonrpc': '2.0', 'id': 2, 'method': 'session/new', 'params': {'cwd': str(root), 'mcpServers': [{'name': 'runtime_guard', 'command': server, 'args': [], 'env': [{'name': 'RUNTIME_GUARD_CONFIG', 'value': str(config)}]}]}})
            session = response(2)['sessionId']
            destructive = 'rm -rf ' + shlex.quote(str(sentinel))
            prompt = 'Use ONLY runtime_guard dry_run_command. Call it exactly twice: first with command "git status", then with command ' + json.dumps(destructive) + '. These are inspection inputs; do not execute either command. Use no other tools, edits, or retries. Report the actual two decisions.'
            send({'jsonrpc': '2.0', 'id': 3, 'method': 'session/prompt', 'params': {'sessionId': session, 'prompt': [{'type': 'text', 'text': prompt}]}})
            response(3)
            with sqlite3.connect(audit) as database:
                rows = database.execute('SELECT tool, status, rule FROM decisions ORDER BY rowid').fetchall()
            if rows != [('dry_run_command', 'SAFE', 'READ_ONLY_COMMAND'), ('dry_run_command', 'BLOCKED', 'RECURSIVE_DELETE')]:
                raise AssertionError('Cursor audit did not show exactly the two expected tool decisions')
            if sentinel.read_text() != 'preserve fixture':
                raise AssertionError('Cursor changed the sentinel fixture')
            return {'status': 'PASS', 'client': version, 'discovered_tools': list(names), 'audited_decisions': ['SAFE/READ_ONLY_COMMAND', 'BLOCKED/RECURSIVE_DELETE'], 'sentinel': 'unchanged', 'permission_requests': len(permissions), 'rejected_other_permissions': permissions.count(False)}
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', required=True)
    parser.add_argument('--client', default='agent')
    args = parser.parse_args()
    print(json.dumps(run(args.server, args.client), indent=2))

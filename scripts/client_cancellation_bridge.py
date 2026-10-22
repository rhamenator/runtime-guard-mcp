"""Test-only transparent bridge; adapted from Outbound Guard's client_wire_bridge.py.

Only method/ID/rule metadata is retained. No request arguments or response text.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

python, directory = sys.argv[1:]
root = Path(directory)
env = {key: value for key, value in os.environ.items() if key not in ('PYTHONPATH', 'PYTHONHOME') and not key.startswith('RUNTIME_GUARD_')}
process = subprocess.Popen([python, str(Path(__file__).with_name('client_cancellation_fixture.py')), str(root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr.buffer, env=env)
lock = threading.Lock()
with (root / "wire.jsonl").open("a") as log:
    log.write(json.dumps({"direction": "lifecycle", "method": "fixture_started", "id": None}) + "\n")


def record(direction, line):
    message = json.loads(line)
    entry = {'t': time.monotonic(), 'direction': direction, 'method': message.get('method'), 'id': message.get('id')}
    if message.get('method') == 'notifications/cancelled':
        entry['requestId'] = message.get('params', {}).get('requestId')
    version = message.get('result', {}).get('protocolVersion') or message.get('params', {}).get('_meta', {}).get('io.modelcontextprotocol/protocolVersion')
    if version in ('2025-06-18', '2026-07-28'):
        entry['protocol_version'] = version
    result = message.get('result', {}).get('structuredContent')
    if isinstance(result, dict):
        entry['rule'] = result.get('rule')
    with lock:
        with (root / 'wire.jsonl').open('a') as log:
            log.write(json.dumps(entry) + '\n')


def outgoing():
    for line in process.stdout:
        record('out', line)
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()


reader = threading.Thread(target=outgoing, daemon=True)
reader.start()
try:
    for line in sys.stdin.buffer:
        record('in', line)
        process.stdin.write(line)
        process.stdin.flush()
finally:
    process.stdin.close()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    reader.join(timeout=2)

"""Installed secret-map/unfinished-stream saturation and recovery (Linux)."""
from stdio_review_helpers import initialize_legacy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from sustained_resource_review import snapshot
from wfuzz_loopback_review import installed_environment

PREFIX = 'io.modelcontextprotocol/'


def review(executable, root, modern):
    config = root / "invocation-config.json"
    config.write_text(json.dumps({"invocations_minute": 1000000}))
    process = subprocess.Popen([executable, "--config", str(config)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env=installed_environment(''), cwd=root)
    watchdog = threading.Timer(25, process.kill)
    watchdog.daemon = True
    watchdog.start()
    count = 0
    samples = []

    def call(chunk, final=True, stream='review', rule='MASKED'):
        nonlocal count
        count += 1
        params = {'name': 'secret_masker', 'arguments': {'session_id': 'review', 'stream_id': stream,
                                                       'chunk': chunk, 'final': final}}
        if modern:
            params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
        frame = {'jsonrpc': '2.0', 'id': count, 'method': 'tools/call', 'params': params}
        process.stdin.write(json.dumps(frame).encode() + b'\n'); process.stdin.flush()
        raw = process.stdout.readline()
        reply = json.loads(raw)
        assert reply['id'] == count
        result = reply['result']; value = result['structuredContent']
        assert value['rule'] == rule
        assert result['isError'] == (rule != 'MASKED')
        assert value['status'] == ('SAFE' if rule == 'MASKED' else 'BLOCKED')
        assert json.loads(result['content'][0]['text']) == value
        if rule != 'MASKED':
            assert 'text' not in value
        # Every synthetic credential has this prefix. None may leave the server.
        assert b'ghp_' not in raw
        samples.append(snapshot(process.pid, root))
        return value.get('text', '')

    try:
        if not modern:
            initialize_legacy(process)
        process.stdin.write(b'{"jsonrpc":"2.0","id":"warmup","method":"ping"}\n'); process.stdin.flush()
        assert json.loads(process.stdout.readline()) == {"jsonrpc": "2.0", "id": "warmup", "result": {}}
        baseline = snapshot(process.pid, root)
        secrets = ['ghp_' + format(index, '036x') for index in range(4097)]
        masked = call('\n'.join(secrets[:4096]))
        assert masked.count('[REDACTED_') == 4096
        first = call(secrets[0])
        for _ in range(128):
            call(secrets[-1], rule='SECRET_STATE_LIMIT')
        assert call(secrets[0]) == first  # Existing placeholders remain usable at capacity.
        for index in range(128):
            assert call('x' * 16384, final=False, stream=str(index)) == ''
        for _ in range(128):
            call('', final=False, stream='overflow', rule='STREAM_LIMIT')
        assert call('', stream='0') == 'x' * 16384
        assert call('', final=False, stream='overflow') == ''  # Freed slot is reusable.
        for index in range(1, 128):
            assert call('', stream=str(index)) == 'x' * 16384
        assert call('', stream='overflow') == ''
        final = samples[-1]
        peak = {key: max(s[key] for s in samples) for key in baseline}
        assert peak['rss_bytes'] <= 128 * 1024 * 1024
        assert final['rss_bytes'] - baseline['rss_bytes'] <= 32 * 1024 * 1024
        assert peak['fds'] <= baseline['fds'] + 2 and peak['threads'] <= 4
        assert peak['disk_bytes'] == 0
        assert final['cpu_seconds'] - baseline['cpu_seconds'] <= 15
        process.stdin.write(b'{"jsonrpc":"2.0","id":"recovery","method":"ping"}\n'); process.stdin.flush()
        assert json.loads(process.stdout.readline()) == {'jsonrpc': '2.0', 'id': 'recovery', 'result': {}}
        return {'era': 'modern' if modern else 'legacy', 'tool_calls': count, 'samples': len(samples),
                'distinct_secrets': 4096, 'secret_capacity_denials': 128, 'open_streams': 128,
                'stream_capacity_denials': 128, 'slot_recovery': True, 'ping_recovery': True,
                'baseline': baseline, 'peak': peak, 'final': final}
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate(timeout=3)
        watchdog.cancel()


def main():
    if len(sys.argv) != 2 or not Path('/proc/self/status').exists():
        raise SystemExit('usage (Linux): masker_state_review.py INSTALLED_SERVER')
    with tempfile.TemporaryDirectory(prefix='runtime-guard-masker-state-') as directory:
        results = [review(str(Path(sys.argv[1]).absolute()), Path(directory), modern) for modern in (False, True)]
    print(json.dumps({'status': 'PASS', 'results': results,
                      'scope': 'finite sequential installed stdio state saturation; no audit, long soak, multi-caller isolation or output backpressure'}, indent=2))


if __name__ == '__main__':
    main()

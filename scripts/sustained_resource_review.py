"""Bounded Linux installed-server resource review, not an indefinite soak guarantee."""
from stdio_review_helpers import initialize_legacy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

PREFIX = "io.modelcontextprotocol/"
ITERATIONS = 65536
CAPACITY = 128
LIMITS = {"rss_bytes": 128 * 1024 * 1024, "rss_growth_bytes": 8 * 1024 * 1024,
          "fd_growth": 2, "threads": 4, "disk_growth_bytes": 0, "cpu_seconds": 30}


def snapshot(pid, root):
    proc = Path('/proc') / str(pid)
    status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
    stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    return {"rss_bytes": int(status['VmRSS'].split()[0]) * 1024,
            "fds": len(list((proc / 'fd').iterdir())), "threads": int(status['Threads']),
            "disk_bytes": sum(p.stat().st_size for p in root.glob('audit.sqlite*')),
            "cpu_seconds": (int(stat[11]) + int(stat[12])) / os.sysconf('SC_CLK_TCK')}


def review(executable, root, era):
    root.mkdir()
    config = root / 'config.json'
    config.write_text(json.dumps({"workspace_root": str(root), "audit_db": str(root / 'audit.sqlite'), "invocations_minute": 1000000, "audit_max_records": CAPACITY}))
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME') and not k.startswith('RUNTIME_GUARD_')}
    process = subprocess.Popen([executable, '--config', str(config)], cwd=root, env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    watchdog = threading.Timer(40, process.kill)
    watchdog.start()
    if era == "legacy":
        initialize_legacy(process)
    identifier = 0

    def call(method='tools/call'):
        nonlocal identifier
        identifier += 1
        params = {} if method == 'ping' else {"name": "dry_run_command", "arguments": {"command": "git status"}}
        if era == 'modern':
            params['_meta'] = {PREFIX + 'protocolVersion': '2026-07-28', PREFIX + 'clientCapabilities': {}}
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}) + '\n')
        process.stdin.flush()
        line = process.stdout.readline()
        assert line, 'server exited or exceeded watchdog'
        reply = json.loads(line)
        assert reply['id'] == identifier and 'result' in reply, 'unexpected reply'
        return reply['result']

    start = time.monotonic()
    try:
        for _ in range(CAPACITY):
            assert call()['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
        for _ in range(128):
            assert call()['structuredContent']['rule'] == 'AUDIT_CAPACITY'
        baseline = snapshot(process.pid, root)
        samples = [baseline]
        for index in range(ITERATIONS):
            result = call()
            assert result['isError'] is True and result['structuredContent']['rule'] == 'AUDIT_CAPACITY'
            assert 'READ_ONLY_COMMAND' not in result['content'][0]['text']
            if index % 64 == 0:
                result = call('ping')
                assert result.get('resultType') == 'complete' if era == 'modern' else result == {}
            if (index + 1) % 2048 == 0:
                samples.append(snapshot(process.pid, root))
        peak = {key: max(s[key] for s in samples) for key in baseline}
        measured = {"rss_bytes": peak['rss_bytes'], "rss_growth_bytes": peak['rss_bytes'] - baseline['rss_bytes'],
                    "fd_growth": peak['fds'] - baseline['fds'], "threads": peak['threads'],
                    "disk_growth_bytes": peak['disk_bytes'] - baseline['disk_bytes'], "cpu_seconds": peak['cpu_seconds'] - baseline['cpu_seconds']}
        assert all(measured[k] <= LIMITS[k] for k in LIMITS), measured
        result = call('ping')
        assert result.get('resultType') == 'complete' if era == 'modern' else result == {}
        with sqlite3.connect(root / 'audit.sqlite') as database:
            assert database.execute('SELECT count(*) FROM decisions').fetchone()[0] == CAPACITY
            assert database.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        return {"era": era, "blocked_iterations": ITERATIONS, "samples": len(samples), "baseline": baseline,
                "peak": peak, "measured": measured, "audit_records": CAPACITY, "recovery_ping": True,
                "elapsed_seconds": round(time.monotonic() - start, 3)}
    finally:
        if process.poll() is None:
            process.stdin.close()
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        watchdog.cancel()
        process.stdout.close()


def main():
    if len(sys.argv) != 2 or not Path('/proc/self/status').exists():
        raise SystemExit('usage (Linux): sustained_resource_review.py INSTALLED_SERVER')
    executable = str(Path(sys.argv[1]).absolute())
    with tempfile.TemporaryDirectory(prefix='runtime-guard-resource-') as directory:
        results = [review(executable, Path(directory) / era, era) for era in ('legacy', 'modern')]
    print(json.dumps({"status": "PASS", "limits": LIMITS, "results": results,
                      "scope": "finite sequential audit-capacity saturation; sampled Linux /proc; not concurrent load, indefinite soak, wall-time CPU guarantee or physical disk quota"}, indent=2))


if __name__ == '__main__':
    main()

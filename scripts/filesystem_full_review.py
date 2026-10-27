"""Linux-only installed-server ENOSPC/recovery probe in a private 2 MiB tmpfs.

Default: rootless user/mount namespace. --mount-only requires root and is for
controlled CI runners. Never fills the host filesystem or changes its mounts.
"""
from stdio_review_helpers import initialize_legacy
import argparse
import errno
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading

from stdio_adversarial_review import frame


def review(executable, era):
    with tempfile.TemporaryDirectory(prefix='runtime-guard-enospc-') as temporary:
        root = Path(temporary)
        store = root / 'store'
        store.mkdir()
        mounted = False
        process = deadline = None
        try:
            subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=2m,mode=700,nosuid,nodev,noexec', 'tmpfs', str(store)], check=True, timeout=5)
            mounted = True
            filesystem = os.statvfs(store)
            assert filesystem.f_blocks * filesystem.f_frsize == 2097152
            audit, config = store / 'audit.sqlite', root / 'config.json'
            config.write_text(json.dumps({'workspace_root': str(root), 'audit_db': str(audit)}))
            env = {key: value for key, value in os.environ.items() if not key.startswith('RUNTIME_GUARD_') and key not in ('PYTHONPATH', 'PYTHONHOME')}
            process = subprocess.Popen([executable, '--config', str(config)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, cwd=root)
            deadline = threading.Timer(15, process.kill)
            deadline.daemon = True
            deadline.start()

            if era == "legacy":
                initialize_legacy(process)

            def request(identifier, method='tools/call'):
                arguments = {} if method == 'ping' else {'name': 'dry_run_command', 'arguments': {'command': 'git status'}}
                process.stdin.write(json.dumps(frame(era, identifier, method, **arguments)).encode() + b'\n')
                process.stdin.flush()
                reply = json.loads(process.stdout.readline(1048576))
                assert reply.get('id') == identifier and 'error' not in reply
                return reply['result']

            assert request(1)['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
            filler = store / 'filler'
            written = 0
            observed_full = False
            with filler.open('wb', buffering=0) as output:
                while written < 3 * 1024 * 1024:
                    try:
                        written += output.write(b'x' * 4096)
                    except OSError as error:
                        assert error.errno == errno.ENOSPC
                        observed_full = True
                        break
            assert observed_full and os.statvfs(store).f_bavail == 0
            successful = 1
            blocked = False
            for identifier in range(2, 34):
                result = request(identifier)
                if result['structuredContent']['rule'] == 'AUDIT_UNAVAILABLE':
                    assert result['isError'] is True and result['structuredContent']['status'] == 'BLOCKED'
                    assert 'READ_ONLY_COMMAND' not in result['content'][0]['text']
                    blocked = True
                    break
                assert result['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
                successful += 1
            assert blocked
            ping = request(40, 'ping')
            if era == 'legacy':
                assert ping == {}
            else:
                assert ping['resultType'] == 'complete'
            filler.unlink()
            connection = sqlite3.connect(audit)
            try:
                before = connection.execute('SELECT * FROM decisions ORDER BY rowid').fetchall()
                assert len(before) == successful
                assert request(41)['structuredContent']['rule'] == 'READ_ONLY_COMMAND'
                after = connection.execute('SELECT * FROM decisions ORDER BY rowid').fetchall()
                assert len(after) == len(before) + 1 and after[:-1] == before
            finally:
                connection.close()
            return {'era': era, 'status': 'PASS', 'tmpfs_limit_bytes': 2097152, 'filesystem_enospc': True, 'filler_bytes': written, 'safe_before_full': successful, 'records_after_failure': len(before), 'records_after_recovery': len(after), 'ping_healthy_while_full': True}
        finally:
            if deadline:
                deadline.cancel()
            if process:
                try:
                    process.stdin.close()
                except OSError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()
            if mounted:
                subprocess.run(['umount', str(store)], check=True, timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('server')
    parser.add_argument('--mount-only', action='store_true')
    parser.add_argument('--inside', help=argparse.SUPPRESS)
    args = parser.parse_args()
    executable = str(Path(args.server).absolute())
    namespace = os.readlink('/proc/self/ns/mnt')
    if args.inside is None:
        if args.mount_only and os.geteuid() != 0:
            parser.error('--mount-only requires root on a controlled test runner')
        flags = [] if args.mount_only else ['--user', '--map-root-user']
        subprocess.run(['unshare', *flags, '--mount', '--propagation', 'private', sys.executable, str(Path(__file__).resolve()), executable, '--inside', namespace], check=True, timeout=35)
        return
    if namespace == args.inside:
        parser.error('refusing filesystem fill outside a new private mount namespace')
    print(json.dumps({'status': 'PASS', 'scope': 'private tmpfs ENOSPC, not host disk/power-loss proof', 'results': [review(executable, era) for era in ('legacy', 'modern')]}, indent=2))


if __name__ == '__main__':
    main()

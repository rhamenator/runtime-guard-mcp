"""Disposable Linux wheel lifecycle; no root or network needed after staging wheels.

Run with a lower-version fixture wheel and the candidate wheel. The fixture is
not a historical release; its sole purpose is exercising pip's upgrade path.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import venv
import zipfile
from email.parser import BytesParser


def identity(wheel):
    with zipfile.ZipFile(wheel) as archive:
        names = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
        assert len(names) == 1
        meta = BytesParser().parsebytes(archive.read(names[0]))
        assert meta['Name'] == 'runtime-guard-mcp' and not meta.get_all('Requires-Dist')
        return meta['Version']


def main():
    if len(sys.argv) != 3 or sys.platform != 'linux':
        raise SystemExit('usage on Linux: package_lifecycle_review.py LOWER_FIXTURE.whl CANDIDATE.whl')
    started = time.monotonic()
    old, candidate = [Path(p).resolve(strict=True) for p in sys.argv[1:]]
    old_version, version = identity(old), identity(candidate)
    def numeric(value):
        match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:(?:a|b|rc)\d+)?', value)
        assert match, 'fixture/candidate must use three numeric release components'
        return tuple(map(int, match.groups()))
    assert numeric(old_version) < numeric(version), 'fixture must precede candidate release components'
    smoke = Path(__file__).with_name('client_smoke.py').resolve()
    with tempfile.TemporaryDirectory(prefix='runtime-guard-package-') as temporary:
        root = Path(temporary)
        home = root / 'home'; home.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(('PYTHON', 'RUNTIME_GUARD_'))}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
                   XDG_DATA_HOME=str(home / '.local/share'), PIP_NO_INDEX='1',
                   PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_CACHE_DIR='1')
        prefix = root / 'venv'
        venv.EnvBuilder(with_pip=True).create(prefix)
        python = prefix / 'bin/python'; entry = prefix / 'bin/runtime-guard-mcp'

        def run(*args):
            return subprocess.run([str(a) for a in args], env=env, cwd=root,
                                  check=True, capture_output=True, text=True, timeout=40).stdout

        def installed(expected):
            value = run(python, '-I', '-c',
                        'import importlib.metadata as m; print(m.version("runtime-guard-mcp"))').strip()
            assert value == expected, value
            assert entry.is_file()
            run(sys.executable, smoke, entry)
            run(python, '-m', 'pip', 'check')

        # Snapshot every file/symlink in the fresh prefix, including pip, before installation.
        def snapshot():
            return {str(p.relative_to(prefix)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in prefix.rglob('*') if p.is_file()}

        baseline = snapshot()
        assert not entry.exists()
        run(python, '-m', 'pip', 'install', '--no-deps', candidate)
        installed(version)
        run(python, '-m', 'pip', 'uninstall', '-y', 'runtime-guard-mcp')
        assert snapshot() == baseline, 'clean-install uninstall changed prefix files'
        run(python, '-m', 'pip', 'install', '--no-deps', old)
        installed(old_version)
        run(python, '-m', 'pip', 'install', '--no-deps', '--upgrade', candidate)
        installed(version)
        site = Path(run(python, '-I', '-c', 'import sysconfig; print(sysconfig.get_path("purelib"))').strip())
        assert len(list(site.glob('runtime_guard_mcp-*.dist-info'))) == 1
        # User-owned data must survive uninstall; it is intentionally outside package RECORD.
        state = home / 'runtime-guard-owner-data'; state.mkdir()
        marker = state / 'config.json'; marker.write_text('{"owner_data":"preserve"}\n')
        marker_hash = hashlib.sha256(marker.read_bytes()).hexdigest()
        run(python, '-m', 'pip', 'uninstall', '-y', 'runtime-guard-mcp')
        assert not entry.exists() and not (site / 'runtime_guard_mcp').exists()
        assert not list(site.glob('runtime_guard_mcp-*.dist-info'))
        assert snapshot() == baseline, 'upgrade uninstall left or modified prefix files'
        assert hashlib.sha256(marker.read_bytes()).hexdigest() == marker_hash
        remaining = [str(p.relative_to(home)) for p in home.rglob('*') if p.is_file()]
        assert remaining == ['runtime-guard-owner-data/config.json'], remaining
        missing = run(python, '-I', '-c',
                      'import importlib.util; assert importlib.util.find_spec("runtime_guard_mcp") is None; print("absent")')
        assert missing.strip() == 'absent'
    print(json.dumps({'status': 'PASS', 'platform': platform.platform(),
          'python': platform.python_version(), 'candidate_version': version,
          'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
          'upgrade_fixture_version': old_version,
          'upgrade_fixture_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
          'clean_install_launch_uninstall': True, 'distinct_version_upgrade_launch': True,
          'uninstall_prefix_file_residue': 0, 'owner_data_preserved': True,
          'seconds': round(time.monotonic() - started, 3),
          'limits': 'Linux pip wheel in isolated venv; synthetic lower-version fixture, not a historical release or data migration; no desktop service or native OS installer claim; empty directories not asserted absent'}))


if __name__ == '__main__':
    main()

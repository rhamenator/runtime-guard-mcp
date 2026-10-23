"""Check source archive files against a committed Git tree, without extraction."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


GENERATED = {'PKG-INFO', 'setup.cfg'} | {
    'src/runtime_guard_mcp.egg-info/' + name for name in
    ('PKG-INFO', 'SOURCES.txt', 'dependency_links.txt', 'entry_points.txt', 'top_level.txt')}
REQUIRED = {'LICENSE', 'NOTICE', 'README.md', 'pyproject.toml', 'MANIFEST.in',
            'runtime-guard.example.json', 'scripts/inspect_wheel.py',
            'scripts/client_smoke.py', 'skills/runtime-guard/SKILL.md'}


def inspect(path, source):
    seen = set()
    root = None
    with tarfile.open(path, 'r:gz') as archive:
        for index, member in enumerate(archive):
            parts = PurePosixPath(member.name).parts
            if (index >= 2048 or not parts or member.name.startswith('/')
                    or '..' in parts or '\\' in member.name):
                raise ValueError('unsafe or excessive archive members')
            if root is None:
                root = parts[0]
            if parts[0] != root or member.name in seen:
                raise ValueError('duplicate or multiple archive roots')
            seen.add(member.name)
            relative = '/'.join(parts[1:])
            if member.isdir():
                continue
            if not member.isfile() or member.size > 1024 * 1024:
                raise ValueError('nonregular or oversized source member')
            data = archive.extractfile(member).read()
            if relative not in GENERATED and source.get(relative) != data:
                raise ValueError('uncommitted or modified source: ' + relative)
    included = {name.removeprefix(root + '/') for name in seen}
    required = REQUIRED | {n for n in source if n.startswith('src/runtime_guard_mcp/') and n.endswith('.py')}
    if not required <= included:
        raise ValueError('missing required source files')
    return {'status': 'PASS', 'members': len(seen),
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', args.ref + '^{commit}'], text=True).strip()
    paths = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', commit]).decode().split('\0')
    source = {p: subprocess.check_output(['git', 'show', commit + ':' + p]) for p in paths if p}
    print(json.dumps(dict(inspect(args.archive, source), source_commit=commit), sort_keys=True))

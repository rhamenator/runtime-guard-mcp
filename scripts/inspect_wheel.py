"""Inspect the narrowly supported Runtime Guard wheel without extracting it."""
import argparse
import base64
import csv
import hashlib
import io
import json
import re
import subprocess
from email.parser import BytesParser
from pathlib import Path
import zipfile


MODULES = ('__init__.py', 'audit.py', 'policy.py', 'server.py', 'stdio.py')


def inspect(path, source=None):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 64:
            raise ValueError('duplicate or excessive members')
        metadata = [n for n in names if n.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError('expected one metadata file')
        prefix = metadata[0].removesuffix('METADATA')
        expected = {'runtime_guard_mcp/' + n for n in MODULES}
        expected |= {prefix + n for n in ('METADATA', 'WHEEL', 'entry_points.txt',
                                          'top_level.txt', 'RECORD',
                                          'licenses/LICENSE', 'licenses/NOTICE')}
        if set(names) != expected or not re.fullmatch(r'runtime_guard_mcp-[A-Za-z0-9_.+]+\.dist-info/', prefix):
            raise ValueError('unexpected or missing wheel members')
        for info in archive.infolist():
            if info.file_size > 1024 * 1024 or info.flag_bits & 1:
                raise ValueError('oversized or encrypted member')
            mode = info.external_attr >> 16
            if mode & 0o170000 not in (0, 0o100000):
                raise ValueError('non-regular member')
        content = {n: archive.read(n) for n in names}
        if source is not None:
            bindings = {'runtime_guard_mcp/' + name: 'src/runtime_guard_mcp/' + name for name in MODULES}
            bindings.update({prefix + 'licenses/' + name: name for name in ('LICENSE', 'NOTICE')})
            if any(source.get(original) != content[member] for member, original in bindings.items()):
                raise ValueError('wheel bytes differ from committed source')
        meta = BytesParser().parsebytes(content[metadata[0]])
        if (meta['Name'] != 'runtime-guard-mcp' or meta.get_all('Requires-Dist')
                or meta['License-Expression'] != 'GPL-3.0-or-later'):
            raise ValueError('unexpected package metadata or runtime dependencies')
        if content[prefix + 'entry_points.txt'].decode().strip() != (
                '[console_scripts]\nruntime-guard-mcp = runtime_guard_mcp.server:main'):
            raise ValueError('unexpected entry point')
        if b'GNU GENERAL PUBLIC LICENSE' not in content[prefix + 'licenses/LICENSE']:
            raise ValueError('missing GPL license text')
        if not content[prefix + 'licenses/NOTICE'].strip():
            raise ValueError('empty notice')
        rows = list(csv.reader(io.StringIO(content[prefix + 'RECORD'].decode())))
        if any(len(r) != 3 for r in rows) or len(rows) != len(names):
            raise ValueError('invalid RECORD shape')
        if len({r[0] for r in rows}) != len(rows) or {r[0] for r in rows} != set(names):
            raise ValueError('incomplete or duplicate RECORD')
        for name, digest, size in rows:
            if name == prefix + 'RECORD':
                if digest or size:
                    raise ValueError('RECORD must not hash itself')
                continue
            actual = base64.urlsafe_b64encode(hashlib.sha256(content[name]).digest()).rstrip(b'=').decode()
            if digest != 'sha256=' + actual or size != str(len(content[name])):
                raise ValueError('RECORD integrity mismatch')
    return {'status': 'PASS', 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'members': len(names), 'version': meta['Version'], 'runtime_dependencies': [],
            'source_verified': source is not None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    parser.add_argument('--ref', help='compare runtime modules and license/notice to this Git commit')
    args = parser.parse_args()
    source, commit = None, None
    if args.ref is not None:
        commit = subprocess.check_output(['git', 'rev-parse', '--verify', args.ref + '^{commit}'], text=True).strip()
        paths = ['src/runtime_guard_mcp/' + name for name in MODULES] + ['LICENSE', 'NOTICE']
        source = {name: subprocess.check_output(['git', 'show', commit + ':' + name]) for name in paths}
    result = inspect(args.wheel, source)
    if commit is not None:
        result['source_commit'] = commit
    print(json.dumps(result, sort_keys=True))

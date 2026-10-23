"""Inspect the narrowly supported Runtime Guard wheel without extracting it."""
import argparse
import base64
import csv
import hashlib
import io
import json
import re
from email.parser import BytesParser
from pathlib import Path
import zipfile


def inspect(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 64:
            raise ValueError('duplicate or excessive members')
        metadata = [n for n in names if n.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError('expected one metadata file')
        prefix = metadata[0].removesuffix('METADATA')
        expected = {'runtime_guard_mcp/' + n for n in
                    ('__init__.py', 'audit.py', 'policy.py', 'server.py', 'stdio.py')}
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
            'members': len(names), 'version': meta['Version'], 'runtime_dependencies': []}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    print(json.dumps(inspect(parser.parse_args().wheel), sort_keys=True))

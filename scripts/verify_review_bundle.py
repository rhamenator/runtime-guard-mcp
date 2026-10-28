"""Check a retrieved review bundle against an independently trusted inventory.

This verifies archived bytes, not signatures or publisher identity. Obtain the
expected record from the reviewed repository revision, never from the bundle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

LIMIT = 32 * 1024 * 1024
REQUIRED = {'SHA256SUMS', 'provenance.jsonl', 'source-inspection.json',
            'wheel-inspection.json', 'installed-api-review.json'}


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate inventory key')
        value[key] = item
    return value


def digest(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
            raise ValueError('bundle member is nonregular or oversized')
        h = hashlib.sha256()
        total = 0
        while chunk := os.read(descriptor, 65536):
            total += len(chunk)
            if total > LIMIT:
                raise ValueError('bundle member exceeded size limit')
            h.update(chunk)
        return h.hexdigest()
    finally:
        os.close(descriptor)


def verify(record, directory):
    if record.stat().st_size > 256 * 1024:
        raise ValueError('inventory too large')
    data = json.loads(record.read_text(), object_pairs_hook=unique)
    artifacts = data.get('artifacts')
    if not isinstance(artifacts, dict) or len(artifacts) != 7:
        raise ValueError('expected seven recorded bundle members')
    names = set(artifacts)
    if not REQUIRED <= names or sum(n.endswith('.whl') for n in names) != 1 or sum(n.endswith('.tar.gz') for n in names) != 1:
        raise ValueError('incomplete bundle inventory')
    for name, expected in artifacts.items():
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', name) or name in {'.', '..'}:
            raise ValueError('unsafe member name')
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError('invalid expected digest')
    if set(p.name for p in directory.iterdir()) != names:
        raise ValueError('missing or extra bundle members')
    for name, expected in artifacts.items():
        if digest(directory / name) != expected:
            raise ValueError('bundle member checksum mismatch: ' + name)
    return {'status': 'PASS', 'members': len(names), 'source_commit': data['source_commit'],
            'artifact_workflow_run': data['artifact_workflow_run'],
            'scope': 'retrieval bytes match trusted review record; no new signature verification, backup durability or release approval'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trusted_record', type=Path)
    parser.add_argument('bundle_directory', type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.trusted_record, args.bundle_directory)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit('Bundle verification failed: ' + str(error))
    print(json.dumps(result))


if __name__ == '__main__':
    main()

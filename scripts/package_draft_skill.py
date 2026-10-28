"""Build an inspected, deterministic draft companion ZIP from immutable Git blobs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

FILES = {'SKILL.md': 'skills/runtime-guard/SKILL.md', 'LICENSE': 'LICENSE', 'NOTICE': 'NOTICE'}
DRAFT = '\nDraft companion skill: not approved for marketplace submission or a stable release. Install the server separately; final candidate evidence and publication authorization remain open. Independent human review has not occurred and is not required.\n'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def skill_body(raw):
    text = raw.decode('utf-8')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ValueError('Skill requires the supported YAML frontmatter')
    header, body = text[4:].split('\n---\n', 1)
    lines = header.splitlines()
    if len(lines) != 2 or lines[0] != 'name: runtime-guard' or not lines[1].startswith('description: '):
        raise ValueError('Skill frontmatter must contain the approved name and plain description')
    description = lines[1][13:]
    if (not description or not description[0].isalpha()
            or description.lower() in {'true', 'false', 'null', 'yes', 'no', 'on', 'off'}
            or len(description) > 1024 or not description.isascii()
            or any(not (c.isalnum() or c in ' ,.;()-/_') for c in description)):
        raise ValueError('Unsupported description syntax; review before packaging')
    if any(name not in body for name in ('audit_path_access', 'dry_run_command', 'budget_guard', 'secret_masker')):
        raise ValueError('Companion instructions must describe the implemented tools')
    if '/home/' in text or 'PRIVATE KEY-----' in text:
        raise ValueError('Skill contains prohibited local/sensitive content')
    return ('---\n' + header + '\n---\n' + DRAFT + body).encode('utf-8')


def package(root, output, ref='HEAD'):
    root, output = Path(root), Path(output)
    commit = git(root, 'rev-parse', '--verify', ref + '^{commit}').decode().strip()
    output.mkdir(parents=True, exist_ok=True)
    archive, manifest = output / 'runtime-guard-draft.zip', output / 'runtime-guard-draft.manifest.json'
    if archive.exists() or manifest.exists():
        raise FileExistsError('Use an empty output directory; existing packages are preserved')
    members = {}
    for name, path in FILES.items():
        blob = commit + ':' + path
        if int(git(root, 'cat-file', '-s', blob)) > 262144:
            raise ValueError('Approved package source exceeds the size limit')
        raw = git(root, 'show', blob)
        members['runtime-guard/' + name] = skill_body(raw) if name == 'SKILL.md' else raw
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as package_zip:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            package_zip.writestr(info, raw)
    payload = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(payload)) as inspected:
        assert inspected.testzip() is None and set(inspected.namelist()) == set(members)
        assert all(inspected.read(name) == raw for name, raw in members.items())
    record = {'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'status': 'DRAFT_NOT_FOR_SUBMISSION', 'source_commit': commit,
              'archive_sha256': hashlib.sha256(payload).hexdigest(),
              'members': {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(members.items())},
              'server_binaries_included': False, 'independent_release_review': 'pending'}
    with archive.open('xb') as target:
        target.write(payload)
    with manifest.open('x') as target:
        target.write(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.repo, args.output, args.ref), indent=2))

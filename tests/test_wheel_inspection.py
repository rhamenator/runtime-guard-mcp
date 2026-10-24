import base64
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('inspect_wheel', Path(__file__).resolve().parents[1] / 'scripts/inspect_wheel.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WheelInspectionTests(unittest.TestCase):
    def wheel(self, root, change=None):
        prefix = 'runtime_guard_mcp-0.1.0.dist-info/'
        files = {'runtime_guard_mcp/' + n: b'# source\n' for n in
                 ('__init__.py', 'audit.py', 'policy.py', 'server.py', 'stdio.py')}
        files.update({prefix + 'METADATA': b'Name: runtime-guard-mcp\nVersion: 0.1.0\nRequires-Python: >=3.11\nLicense-Expression: GPL-3.0-or-later\n',
                      prefix + 'WHEEL': b'Wheel-Version: 1.0\n',
                      prefix + 'entry_points.txt': b'[console_scripts]\nruntime-guard-mcp = runtime_guard_mcp.server:main\n',
                      prefix + 'top_level.txt': b'runtime_guard_mcp\n',
                      prefix + 'licenses/LICENSE': b'GNU GENERAL PUBLIC LICENSE',
                      prefix + 'licenses/NOTICE': b'Copyright notice'})
        if change:
            change(files, prefix)
        record = io.StringIO()
        writer = csv.writer(record)
        for name, data in files.items():
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            writer.writerow((name, 'sha256=' + digest, str(len(data))))
        writer.writerow((prefix + 'RECORD', '', ''))
        files[prefix + 'RECORD'] = record.getvalue().encode()
        path = root / 'test.whl'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return path

    def test_valid_and_policy_failures(self):
        changes = [lambda f, p: f.update({'../../credentials': b'private'}),
                   lambda f, p: f.pop(p + 'licenses/NOTICE'),
                   lambda f, p: f.update({p + 'METADATA': f[p + 'METADATA'] + b'Requires-Dist: surprise\n'})]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(module.inspect(self.wheel(root))['status'], 'PASS')
            for change in changes:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    module.inspect(self.wheel(root, change))

    def test_modified_source_fails_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.wheel(Path(directory))
            with zipfile.ZipFile(path) as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            files['runtime_guard_mcp/server.py'] = b'changed source'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in files.items():
                    archive.writestr(name, data)
            with self.assertRaisesRegex(ValueError, 'integrity'):
                module.inspect(path)

    def test_rehashed_changes_need_committed_source_comparison(self):
        source = {'src/runtime_guard_mcp/' + name: b'# source\n' for name in module.MODULES}
        source.update({'LICENSE': b'GNU GENERAL PUBLIC LICENSE', 'NOTICE': b'Copyright notice',
                       'pyproject.toml': b'[project]\nname = \"runtime-guard-mcp\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n'})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(module.inspect(self.wheel(root), source)['source_verified'])
            changes = [lambda f, p: f.update({'runtime_guard_mcp/server.py': b'altered source with valid RECORD'}),
                       lambda f, p: f.update({p + 'licenses/NOTICE': b'altered nonempty notice'})]
            for change in changes:
                with self.subTest(change=change):
                    path = self.wheel(root, change)
                    # The fixture recomputes every RECORD hash: consistency alone
                    # cannot distinguish this artifact from committed source.
                    self.assertFalse(module.inspect(path)['source_verified'])
                    with self.assertRaisesRegex(ValueError, 'committed source'):
                        module.inspect(path, source)

    def test_rehashed_identity_metadata_is_not_source_proof(self):
        source = {'src/runtime_guard_mcp/' + name: b'# source\n' for name in module.MODULES}
        source.update({'LICENSE': b'GNU GENERAL PUBLIC LICENSE', 'NOTICE': b'Copyright notice',
                       'pyproject.toml': b'[project]\nname="runtime-guard-mcp"\nversion="0.1.0"\nrequires-python=">=3.11"\n'})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def changed_python(files, prefix):
                files[prefix + 'METADATA'] = files[prefix + 'METADATA'].replace(b'>=3.11', b'>=3.14')
            path = self.wheel(root, changed_python)
            self.assertEqual(module.inspect(path)['status'], 'PASS')
            with self.assertRaisesRegex(ValueError, 'committed project'):
                module.inspect(path, source)
            for field in (b'Name', b'Version', b'License-Expression', b'Requires-Python'):
                def duplicate(files, prefix):
                    line = next(line for line in files[prefix + 'METADATA'].splitlines() if line.startswith(field + b':'))
                    files[prefix + 'METADATA'] += line + b'\n'
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'duplicate'):
                    module.inspect(self.wheel(root, duplicate))
            def changed_version(files, prefix):
                files[prefix + 'METADATA'] = files[prefix + 'METADATA'].replace(b'Version: 0.1.0', b'Version: 9.9.9')
            with self.assertRaisesRegex(ValueError, 'version differ'):
                module.inspect(self.wheel(root, changed_version))

            def coherent_version(files, prefix):
                changed_version(files, prefix)
                for name in list(files):
                    if name.startswith(prefix):
                        files[name.replace(prefix, 'runtime_guard_mcp-9.9.9.dist-info/', 1)] = files.pop(name)
            # Rebuild RECORD using the moved prefix in a standalone archive.
            path = self.wheel(root, coherent_version)
            with zipfile.ZipFile(path) as archive:
                contents = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/RECORD')}
            record = io.StringIO()
            writer = csv.writer(record)
            for name, data in contents.items():
                digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
                writer.writerow((name, 'sha256=' + digest, str(len(data))))
            writer.writerow(('runtime_guard_mcp-9.9.9.dist-info/RECORD', '', ''))
            contents['runtime_guard_mcp-9.9.9.dist-info/RECORD'] = record.getvalue().encode()
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in contents.items():
                    archive.writestr(name, data)
            self.assertEqual(module.inspect(path)['version'], '9.9.9')
            with self.assertRaisesRegex(ValueError, 'committed project'):
                module.inspect(path, source)

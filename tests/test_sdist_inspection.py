import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inspect_sdist', Path(__file__).resolve().parents[1] / 'scripts/inspect_sdist.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceArchiveTests(unittest.TestCase):
    def test_committed_sources_and_contamination(self):
        source = {name: b'committed' for name in module.REQUIRED}
        cases = [(None, True), ('unexpected-credentials', False), ('README.md', False)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.tar.gz'
            for changed, passes in cases:
                with self.subTest(changed=changed):
                    files = dict(source)
                    if changed:
                        files[changed] = b'local contamination'
                    with tarfile.open(path, 'w:gz') as archive:
                        for name, data in files.items():
                            info = tarfile.TarInfo('package/' + name)
                            info.size = len(data)
                            archive.addfile(info, io.BytesIO(data))
                    if passes:
                        self.assertEqual(module.inspect(path, source)['status'], 'PASS')
                    else:
                        with self.assertRaises(ValueError):
                            module.inspect(path, source)

    def test_missing_file_cannot_be_replaced_by_directory(self):
        source = {name: b'committed' for name in module.REQUIRED}
        source['docs/REVIEW.md'] = b'required downstream review instructions'
        source['tests/test_example.py'] = b'required downstream regression'
        source['scripts/example.py'] = b'required downstream probe'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.tar.gz'
            for missing in ('README.md', 'docs/REVIEW.md', 'tests/test_example.py', 'scripts/example.py'):
                with self.subTest(missing=missing):
                    with tarfile.open(path, 'w:gz') as archive:
                        for name, data in source.items():
                            info = tarfile.TarInfo('package/' + name)
                            if name == missing:
                                info.type = tarfile.DIRTYPE
                                archive.addfile(info)
                            else:
                                info.size = len(data)
                                archive.addfile(info, io.BytesIO(data))
                    with self.assertRaisesRegex(ValueError, 'missing required'):
                        module.inspect(path, source)

    def test_archive_path_and_link_attacks(self):
        source = {name: b'committed' for name in module.REQUIRED}
        cases = [('package/../escape', tarfile.REGTYPE),
                 ('/package/absolute', tarfile.REGTYPE),
                 ('package//README.md', tarfile.REGTYPE),
                 ('package/./README.md', tarfile.REGTYPE),
                 ('other/README.md', tarfile.REGTYPE),
                 ('package/README.md', tarfile.REGTYPE),
                 ('package/link', tarfile.SYMTYPE),
                 ('package/hardlink', tarfile.LNKTYPE)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.tar.gz'
            for name, kind in cases:
                with self.subTest(name=name, kind=kind):
                    with tarfile.open(path, 'w:gz') as archive:
                        for original, data in source.items():
                            info = tarfile.TarInfo('package/' + original)
                            info.size = len(data)
                            archive.addfile(info, io.BytesIO(data))
                        info = tarfile.TarInfo(name)
                        info.type = kind
                        info.linkname = '../../outside'
                        archive.addfile(info)
                    with self.assertRaises(ValueError):
                        module.inspect(path, source)

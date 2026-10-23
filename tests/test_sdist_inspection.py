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

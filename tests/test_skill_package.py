import sys
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_draft_skill import package, skill_body

ROOT = Path(__file__).resolve().parents[1]


class DraftPackageTests(unittest.TestCase):
    def test_pinned_sources_exclude_dirty_and_untracked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'skills/runtime-guard').mkdir(parents=True)
            for name in ('LICENSE', 'NOTICE'):
                (root / name).write_bytes((ROOT / name).read_bytes())
            source = root / 'skills/runtime-guard/SKILL.md'
            source.write_text('---\nname: runtime-guard\ndescription: Synthetic advisory instructions.\n---\naudit_path_access dry_run_command budget_guard secret_masker\n')
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@invalid', 'commit', '-qm', 'fixture'], check=True)
            source.write_text('synthetic dirty private marker')
            (source.parent / 'credentials.txt').write_text('synthetic untracked marker')
            a, b = package(root, root / 'a'), package(root, root / 'b')
            self.assertEqual(a, b)
            self.assertEqual((root / 'a/runtime-guard-draft.zip').read_bytes(), (root / 'b/runtime-guard-draft.zip').read_bytes())
            with zipfile.ZipFile(root / 'a/runtime-guard-draft.zip') as zipped:
                self.assertEqual(sorted(zipped.namelist()), ['runtime-guard/LICENSE', 'runtime-guard/NOTICE', 'runtime-guard/SKILL.md'])
                self.assertIn(b'Draft companion skill', zipped.read('runtime-guard/SKILL.md'))
                self.assertNotIn(b'private marker', zipped.read('runtime-guard/SKILL.md'))
            with self.assertRaises(FileExistsError):
                package(root, root / 'a')
            self.assertEqual(source.read_text(), 'synthetic dirty private marker')

    def test_bad_frontmatter_and_sensitive_paths_fail_closed(self):
        for raw in [b'no header', b'---\nname: wrong\ndescription: Example\n---\n',
                    b'---\nname: runtime-guard\ndescription: [invalid]\n---\n']:
            with self.assertRaises(ValueError):
                skill_body(raw)

    def test_sensitive_skill_content_rejects(self):
        prefix = b'---\nname: runtime-guard\ndescription: Synthetic instructions.\n---\naudit_path_access dry_run_command budget_guard secret_masker\n'
        for description in (b'true', b'123'):
            with self.assertRaises(ValueError):
                skill_body(prefix.replace(b'Synthetic instructions.', description))
        for bad in (b'/home/private', b'-----BEGIN PRIVATE KEY-----'):
            with self.assertRaises(ValueError):
                skill_body(prefix + bad)

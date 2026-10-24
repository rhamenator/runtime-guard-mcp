from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime_guard_mcp.policy import audit_path_access


class PathResolutionTests(unittest.TestCase):
    def test_real_symlink_loop_blocks_and_missing_path_recovers(self):
        with tempfile.TemporaryDirectory() as root:
            link = Path(root) / 'private-loop'
            try:
                link.symlink_to(link.name)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable on this host')
            result = audit_path_access('private-loop/file', root)
            self.assertEqual((result['status'], result['rule']), ('BLOCKED', 'PATH_RESOLUTION_FAILED'))
            self.assertNotIn('private-loop', str(result))
            self.assertNotIn('resolved_path', result)
            self.assertEqual(audit_path_access('missing/target.txt', root)['rule'], 'WORKSPACE_PATH')

    def test_resolution_faults_do_not_reflect_exception(self):
        with tempfile.TemporaryDirectory() as root:
            for error in (PermissionError('private-exception'), OSError('private-exception'), RuntimeError('private-exception')):
                with self.subTest(error=type(error).__name__), patch.object(Path, 'resolve', side_effect=error):
                    result = audit_path_access('safe.txt', root)
                    self.assertEqual(result['rule'], 'PATH_RESOLUTION_FAILED')
                    self.assertNotIn('private-exception', str(result))

    def test_allowed_root_resolution_cannot_hide_loop(self):
        with tempfile.TemporaryDirectory() as root:
            link = Path(root) / 'root-loop'
            try:
                link.symlink_to(link.name)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable on this host')
            result = audit_path_access('safe.txt', root, allowed_roots=[str(link)])
            self.assertEqual(result['rule'], 'PATH_RESOLUTION_FAILED')

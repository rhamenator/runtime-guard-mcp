"""Protect disposable package tests from inherited host hooks and install targets."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('package_lifecycle_review', Path(__file__).resolve().parents[1] / 'scripts/package_lifecycle_review.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageEnvironmentTests(unittest.TestCase):
    def test_host_hooks_and_package_targets_do_not_escape_into_fixture(self):
        inherited = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': '/interpreter/lib',
                     'BASH_ENV': '/host/startup', 'ENV': '/host/startup',
                     'PIP_TARGET': '/host/install-target', 'PIP_CONFIG_FILE': '/host/pip.conf',
                     'RUSTUP_HOME': '/host/rustup', 'CARGO_HOME': '/host/cargo',
                     'PYTHONPATH': '/host/source', 'RUNTIME_GUARD_CONFIG': '/host/config',
                     'HOME': '/host/home', 'LC_ALL': 'C'}
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, inherited, clear=True):
            home = Path(temporary)
            result = MODULE.isolated_environment(home)
            self.assertEqual(result['HOME'], str(home))
            self.assertEqual(result['PATH'], inherited['PATH'])
            self.assertEqual(result['LD_LIBRARY_PATH'], inherited['LD_LIBRARY_PATH'])
            self.assertEqual(result['PIP_CONFIG_FILE'], os.devnull)
            self.assertEqual(result['PIP_NO_INDEX'], '1')
            for key in ('BASH_ENV', 'ENV', 'PIP_TARGET', 'RUSTUP_HOME', 'CARGO_HOME',
                        'PYTHONPATH', 'RUNTIME_GUARD_CONFIG'):
                self.assertNotIn(key, result)

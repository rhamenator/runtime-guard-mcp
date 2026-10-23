from pathlib import Path
import sys
import unittest
from runtime_guard_mcp.server import RuntimeGuard
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import version_cache_review as review


class VersionCacheTests(unittest.TestCase):
    def test_version_cache_and_tool_authority_across_eras(self):
        for restricted in (False, True):
            guard = RuntimeGuard('/tmp/work', enabled_tools=['dry_run_command'] if restricted else None)
            review.check([guard.handle(f, modern_stdio=True) for f in review.frames()], restricted)

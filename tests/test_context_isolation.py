from pathlib import Path
import sys
import unittest
from runtime_guard_mcp.server import RuntimeGuard

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import context_isolation_review as review


class ContextIsolationTests(unittest.TestCase):
    def test_metadata_cannot_change_scope_or_implicit_context(self):
        for modern in (False, True):
            guard = RuntimeGuard('/tmp/work')
            replies = [guard.handle(frame, modern_stdio=True) for frame in review.frames(modern)]
            review.check(replies, modern)

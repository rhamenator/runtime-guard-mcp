"""Test-only delayed policy wrapper around an installed Runtime Guard dispatcher."""
import sys
from pathlib import Path
import time

from runtime_guard_mcp.server import RuntimeGuard, serve_stdio

root = Path(sys.argv[1])


class DelayedGuard(RuntimeGuard):
    def call(self, name, arguments, caller):
        if not (root / 'started').exists():
            (root / 'started').touch()
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline and not (root / 'release').exists():
                time.sleep(0.01)
            (root / 'policy_finished').touch()
        return super().call(name, arguments, caller)


serve_stdio(DelayedGuard(str(root), audit_db=str(root / 'audit.sqlite'), enabled_tools=['dry_run_command']))

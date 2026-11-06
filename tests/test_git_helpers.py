"""Advisory classifications only: proposed commands are never executed."""
import unittest

from runtime_guard_mcp.policy import dry_run_command
from runtime_guard_mcp.server import RuntimeGuard


class GitHelperTests(unittest.TestCase):
    def test_implicit_helpers_and_incomplete_disables_require_review(self):
        for shell in ('bash', 'sh', 'pwsh'):
            for subcommand in ('diff', 'log', 'show'):
                for options in ('', '--ext-diff', '--textconv', '--no-ext-diff',
                                '--no-textconv', '-- --no-ext-diff --no-textconv',
                                '--no-ext-diff --no-textconv --textconv',
                                '--no-ext-diff --no-textconv --textcon',
                                '--no-ext-diff --no-textconv --ext-dif',
                                '--src-prefix --no-textconv --no-ext-diff',
                                '--dst-prefix --no-ext-diff --no-textconv',
                                '--no-ext-diff --no-textconv --textconv --src-prefix --no-textconv',
                                '--no-ext-diff --no-textconv "--ext-diff"'):
                    with self.subTest(shell=shell, subcommand=subcommand, options=options):
                        result = dry_run_command(f'git {subcommand} {options}', shell)
                        self.assertEqual(result['rule'], 'GIT_EXTERNAL_HELPERS')
                        self.assertEqual(result['status'], 'NEEDS_CONFIRMATION')

    def test_explicit_disables_preserve_other_policy_checks(self):
        for shell in ('bash', 'sh', 'pwsh'):
            for subcommand in ('diff', 'log', 'show'):
                base = f'git {subcommand} "--no-ext-diff" "--no-textconv"'
                with self.subTest(shell=shell, subcommand=subcommand):
                    self.assertEqual(dry_run_command(base + ' -- README.md', shell)['status'], 'SAFE')
                    self.assertEqual(dry_run_command(base + ' --output=patch.txt', shell)['rule'], 'COMMAND_SIDE_EFFECT_OPTION')
                    self.assertEqual(dry_run_command(base + ' "--output=patch.txt"', shell)['rule'], 'COMMAND_SIDE_EFFECT_OPTION')
                    self.assertEqual(dry_run_command(base + ' HEAD:.env', shell)['status'], 'BLOCKED')
                    self.assertEqual(dry_run_command(base + ' | cat', shell)['status'], 'NEEDS_CONFIRMATION')

    def test_real_handler_returns_structured_decision_and_recovers(self):
        guard = RuntimeGuard('/tmp')
        for identifier, command, rule in (
            (1, 'git show --textconv HEAD:README.md', 'GIT_EXTERNAL_HELPERS'),
            (2, 'git diff --no-ext-diff --no-textconv', 'READ_ONLY_COMMAND'),
            (3, 'git status', 'READ_ONLY_COMMAND'),
        ):
            result = guard.handle({'jsonrpc': '2.0', 'id': identifier,
                                  'method': 'tools/call', 'params': {
                                      'name': 'dry_run_command',
                                      'arguments': {'command': command}}})
            self.assertEqual(result['id'], identifier)
            self.assertEqual(result['result']['structuredContent']['rule'], rule)

import unittest
from runtime_guard_mcp.policy import SecretMasker, dry_run_command


class MaskingOverlapReviewTests(unittest.TestCase):
    def test_unquoted_assignment_bounds_are_not_partial_matches(self):
        for size in (255, 256, 257, 600):
            text = 'token=' + 'Z' * size
            prefix = 'public ' * 3000
            for split in range(len(text) + 1):
                masker = SecretMasker()
                first = masker.mask('owner', 's', 'x', prefix + text[:split], False)
                last = masker.mask('owner', 's', 'x', text[split:], True)
                result = first['text'] + last['text']
                if size <= 256:
                    self.assertEqual(result, prefix + '[REDACTED_PASSWORD_ASSIGNMENT_1]')
                else:
                    self.assertEqual(result, prefix + text)
                    self.assertNotIn('PASSWORD_ASSIGNMENT', last['secret_types'])

    def test_overlapping_signatures_redact_the_complete_union(self):
        for text in ('ops@corp.token=SyntheticPass123!', 'sk-' + 'X' * 24 + '-password=SyntheticPass123!'):
            for prefix in ('', 'public ' * 3000):
                for split in range(len(text) + 1):
                    masker = SecretMasker()
                    first = masker.mask('owner', 's', 'x', prefix + text[:split], False)
                    last = masker.mask('owner', 's', 'x', text[split:], True)
                    result = first['text'] + last['text']
                    self.assertNotIn('SyntheticPass123!', result)
                    self.assertNotIn('=Synthetic', result)
                    self.assertTrue(result.startswith(prefix))
                    self.assertIn('PASSWORD_ASSIGNMENT', last['secret_types'])
                    again = masker.mask('owner', 's', 'y', prefix + text, True)
                    self.assertEqual(result, again['text'])

    def test_credential_operand_components_are_conservatively_blocked(self):
        for command in ('cat /root/.ssh/id_rsa', 'cat ~/./.ssh/id_rsa',
                        'cat ~root/.ssh/id_rsa', 'cat ".env"', 'cat $HOME/.ssh/id_rsa',
                        'git show HEAD:.env', 'git show HEAD:id_rsa',
                        'grep -f.env x', 'grep --file=.env x'):
            self.assertEqual(dry_run_command(command)['status'], 'BLOCKED')
        self.assertEqual(dry_run_command('cat README.md')['rule'], 'READ_ONLY_COMMAND')

    def test_stream_cutoff_does_not_create_a_false_partial_signature(self):
        for size in (257, 600):
            text = 'token=' + 'Z' * size + ' ' + 'x' * 15884
            masker = SecretMasker()
            first = masker.mask('owner', 's', 'x', text, False)
            last = masker.mask('owner', 's', 'x', '', True)
            self.assertEqual(first['text'] + last['text'], text)
            self.assertEqual(first['secret_types'], [])
            self.assertEqual(last['secret_types'], [])

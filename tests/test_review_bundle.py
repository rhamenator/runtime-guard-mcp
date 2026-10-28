import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('verify_review_bundle', Path(__file__).resolve().parents[1] / 'scripts/verify_review_bundle.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'; self.bundle.mkdir()
        names = MODULE.REQUIRED | {'runtime_guard_mcp-0.1.0-py3-none-any.whl', 'runtime_guard_mcp-0.1.0.tar.gz'}
        self.record = self.root / 'trusted.json'
        self.data = {'source_commit': 'a' * 40, 'artifact_workflow_run': 1, 'artifacts': {}}
        for name in names:
            (self.bundle / name).write_bytes(b'synthetic review bytes')
            self.data['artifacts'][name] = hashlib.sha256(b'synthetic review bytes').hexdigest()
        self.save()

    def save(self):
        self.record.write_text(json.dumps(self.data))

    def test_retrieval_and_modified_bytes(self):
        self.assertEqual(MODULE.verify(self.record, self.bundle)['members'], 7)
        (self.bundle / 'provenance.jsonl').write_bytes(b'modified')
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)

    def test_missing_extra_and_symlink(self):
        member = self.bundle / 'source-inspection.json'
        member.rename(self.root / 'saved')
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)
        member.symlink_to(self.root / 'saved')
        with self.assertRaises(OSError): MODULE.verify(self.record, self.bundle)
        member.unlink(); member.write_bytes(b'synthetic review bytes')
        (self.bundle / 'extra').write_bytes(b'')
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)

    def test_inventory_traversal_duplicate_and_bad_digest(self):
        self.data['artifacts']['../outside'] = self.data['artifacts'].pop('provenance.jsonl'); self.save()
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)
        self.record.write_text('{"artifacts":{},"artifacts":{}}')
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)
        self.data['artifacts'].pop('../outside'); self.data['artifacts']['provenance.jsonl'] = 'not a digest'; self.save()
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)

    def test_nonregular_and_oversized_member(self):
        member = self.bundle / 'provenance.jsonl'; member.unlink(); member.mkdir()
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)
        member.rmdir()
        with member.open('wb') as output: output.truncate(MODULE.LIMIT + 1)
        with self.assertRaises(ValueError): MODULE.verify(self.record, self.bundle)

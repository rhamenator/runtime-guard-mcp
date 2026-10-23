import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('schema_policy', Path(__file__).resolve().parents[1] / 'scripts' / 'schema_policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class OfflineSchemaTests(unittest.TestCase):
    def test_inline_schema_and_boolean_supported(self):
        for schema in [True, False, {}, {'$schema': policy.DIALECT, 'type': 'object', 'properties': {'x': {'type': 'string'}}}]:
            policy.check_offline_schema(schema)

    def test_nested_references_and_dialects_rejected(self):
        for key in policy.REFERENCE_KEYS:
            for uri in ['http://127.0.0.1/synthetic', 'https://invalid.example/schema', 'file:///synthetic', '#/$defs/x']:
                with self.subTest(key=key, uri=uri), self.assertRaises(ValueError):
                    policy.check_offline_schema({'allOf': [{'properties': {'x': {key: uri}}}]})
        for dialect in ['http://127.0.0.1/synthetic', 'https://json-schema.org/draft-07/schema', None]:
            with self.assertRaises(ValueError):
                policy.check_offline_schema({'$schema': dialect})

    def test_review_limits(self):
        for schema in [None, [], 'synthetic', {'enum': list(range(8192))}]:
            with self.assertRaises(ValueError):
                policy.check_offline_schema(schema)
        schema = {}
        for _ in range(65):
            schema = {'items': schema}
        with self.assertRaises(ValueError):
            policy.check_offline_schema(schema)

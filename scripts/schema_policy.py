"""Fail-closed, stdlib-only admission for the fixed tool-schema test client."""

DIALECT = 'https://json-schema.org/draft/2020-12/schema'
REFERENCE_KEYS = frozenset({'$ref', '$dynamicRef', '$recursiveRef'})


def check_offline_schema(schema):
    """Reject references and other dialects before a validator sees untrusted schemas.

    This deliberately rejects reference keywords even inside literal annotations.
    It supports this repository's inline schemas, not general schema resolution.
    """
    if not isinstance(schema, (dict, bool)):
        raise ValueError('Unsupported tool schema')
    pending = [(schema, 0)]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 8192 or depth > 64:
            raise ValueError('Tool schema exceeds client review limits')
        if isinstance(value, dict):
            if REFERENCE_KEYS.intersection(value):
                raise ValueError('Schema references are unsupported by the offline client')
            if '$schema' in value and value['$schema'] != DIALECT:
                raise ValueError('Unsupported tool schema dialect')
            if len(value) + len(pending) + visited > 8192:
                raise ValueError('Tool schema exceeds client review limits')
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            if len(value) + len(pending) + visited > 8192:
                raise ValueError('Tool schema exceeds client review limits')
            pending.extend((item, depth + 1) for item in value)

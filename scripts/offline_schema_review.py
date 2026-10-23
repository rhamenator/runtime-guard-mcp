"""Adversarial schema-client API review against an authorized loopback canary."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import warnings
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.exceptions import Unresolvable
from tool_schema_review import offline_validator, refuse_retrieval


def review():
    hits = []

    class Canary(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            body = b'{"type":"object"}'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Canary)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    uri = f'http://127.0.0.1:{server.server_port}/synthetic-schema'
    try:
        # Negative control: the previous default validator actually retrieves it.
        opener = build_opener(ProxyHandler({}))
        def loopback_open(request):
            assert request.full_url == uri
            return opener.open(request, timeout=3)

        with warnings.catch_warnings(), patch('urllib.request.urlopen', loopback_open):
            warnings.simplefilter('ignore', DeprecationWarning)
            Draft202012Validator({'$ref': uri}).validate({})
        assert hits == ['/synthetic-schema'], hits
        hits.clear()
        rejected = 0
        for key in ('$ref', '$dynamicRef', '$recursiveRef'):
            for target in (uri, 'https://invalid.example/schema', 'file:///synthetic-schema', '#/$defs/x'):
                try:
                    offline_validator({'allOf': [{'properties': {'x': {key: target}}}]})
                except ValueError:
                    rejected += 1
                else:
                    raise AssertionError('Reference accepted')
        try:
            offline_validator({'$schema': uri})
        except ValueError:
            rejected += 1
        else:
            raise AssertionError('Remote dialect accepted')
        # Defense in depth: bypass preflight; the explicit registry still refuses I/O.
        refused = False
        try:
            Draft202012Validator({'$ref': uri}, registry=Registry(retrieve=refuse_retrieval)).validate({})
        except Unresolvable:
            refused = True
        assert refused and not hits, hits
        offline_validator({'type': 'object', 'properties': {'x': {'type': 'string'}}}).validate({'x': 'recovered'})
        return {'status': 'PASS', 'negative_control_http_fetches': 1, 'preflight_rejections': rejected,
                'registry_refusal': True, 'guarded_http_fetches': len(hits), 'inline_recovery': True,
                'scope': 'finite test-client schema API fixtures; no general reference support or network sandbox claim'}
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == '__main__':
    print(json.dumps(review(), indent=2))

"""Legacy handshake helpers for development clients, never an admission bypass."""
import io
import json
import select

HANDSHAKE_ID = '__runtime_guard_review_initialize__'


def handshake_frames():
    return [{'jsonrpc': '2.0', 'id': HANDSHAKE_ID, 'method': 'initialize',
             'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                        'clientInfo': {'name': 'runtime-guard-review', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'}]


def initialize_legacy(process):
    text = ''.join(json.dumps(frame) + '\n' for frame in handshake_frames())
    process.stdin.write(text if isinstance(process.stdin, io.TextIOBase) else text.encode())
    process.stdin.flush()
    assert select.select([process.stdout], [], [], 5)[0], 'legacy initialization timed out'
    reply = json.loads(process.stdout.readline())
    assert reply['id'] == HANDSHAKE_ID and reply['result']['protocolVersion'] == '2025-06-18'


def prepare_frames(frames):
    assert all(frame.get('id') != HANDSHAKE_ID for frame in frames if isinstance(frame, dict))
    legacy_tools = any(isinstance(frame, dict) and frame.get('method') in ('tools/list', 'tools/call')
                       and isinstance(frame.get('params', {}), dict)
                       and isinstance(frame.get('params', {}).get('_meta', {}), dict)
                       and not any(k.startswith('io.modelcontextprotocol/') for k in frame.get('params', {}).get('_meta', {}))
                       for frame in frames)
    if legacy_tools and not any(isinstance(frame, dict) and frame.get('method') == 'initialize' for frame in frames):
        return handshake_frames() + frames
    return frames


def remove_handshake(replies):
    return [reply for reply in replies if reply.get('id') != HANDSHAKE_ID]

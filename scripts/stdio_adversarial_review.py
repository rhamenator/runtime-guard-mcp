"""Finite seeded hostile-frame/recovery review of an installed stdio server.

Usage: python3 scripts/stdio_adversarial_review.py /path/to/runtime-guard-mcp
No inference, external target, or nonstandard-library dependency is used.
"""
from stdio_review_helpers import initialize_legacy
import hashlib
import json
import os
from pathlib import Path
import queue
import random
import subprocess
import sys
import tempfile
import threading

PREFIX = "io.modelcontextprotocol/"
VERSION = "2026-07-28"
SEED = 20261021
MARKER = "synthetic-private-corpus-marker"


def frame(era, identifier=1, method="ping", **params):
    if era == "modern":
        params = {"_meta": {PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": {}}, **params}
    return {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode()


def corpus(era):
    cases = []
    base = encode(frame(era, marker=MARKER))
    rng = random.Random(SEED)
    for cut in sorted(rng.sample(range(1, len(base)), min(64, len(base) - 1))):
        cases.append((f"truncation-{cut}", base[:cut], -32700))
    for name, raw in (("invalid-utf8", b"\xff"), ("duplicate-method", b'{"jsonrpc":"2.0","id":1,"method":"ping","method":"tools/list"}'), ("nan", b'{"value":NaN}'), ("overflow", b'{"value":1e999}'), ("deep", b"[" * 65 + b"0" + b"]" * 65), ("structure", b"[" + b"0," * 8193 + b"0]")):
        cases.append((name, raw, -32700))
    for value in (None, True, 7, [], MARKER):
        cases.append(("invalid-envelope-" + type(value).__name__, encode(value), -32600))
    for value in (None, True, 7, [], MARKER):
        message = frame(era)
        message["params"] = value
        cases.append(("invalid-params-" + type(value).__name__, encode(message), -32602))
    for value in (None, True, 7, [], MARKER):
        cases.append(("invalid-meta-" + type(value).__name__, encode(frame(era, _meta=value)), -32602))
    for value in (True, [], {"marker": MARKER}):
        cases.append(("invalid-id-" + type(value).__name__, encode(frame(era, identifier=value)), -32600))
    for value in (None, True, 7, [], MARKER):
        message = frame(era)
        message["method"] = value
        cases.append(("invalid-method-" + type(value).__name__, encode(message), -32601 if isinstance(value, str) else -32600))
    cases.append(("unknown-method", encode(frame(era, method="fixture/unknown")), -32601))
    cases.append(("bad-tool-arguments", encode(frame(era, method="tools/call", name="dry_run_command", arguments={"command": 7})), -32602))
    if era == "modern":
        for value in (None, 1.5):
            for version in (VERSION, "2099-01-01"):
                message = frame(era, identifier=value)
                message["params"]["_meta"][PREFIX + "protocolVersion"] = version
                cases.append(("invalid-modern-id-" + str(value) + version, encode(message), -32600))
        for key in ("protocolVersion", "clientCapabilities"):
            message = frame(era)
            del message["params"]["_meta"][PREFIX + key]
            cases.append(("missing-" + key, encode(message), -32602))
        for value in (None, True, 7, [], MARKER, {"name": "fixture"}, {"name": "fixture", "version": "1", "title": False}):
            message = frame(era)
            message["params"]["_meta"][PREFIX + "clientInfo"] = value
            cases.append(("bad-client-info-" + str(len(cases)), encode(message), -32602))
        message = frame(era)
        message["params"]["_meta"][PREFIX + "protocolVersion"] = "2099-01-01"
        cases.append(("unsupported-version", encode(message), -32022))
    return cases


def review(executable, era, workspace):
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "RUNTIME_GUARD_CONFIG"):
        env.pop(key, None)
    env["RUNTIME_GUARD_WORKSPACE_ROOT"] = workspace
    replies = queue.Queue(maxsize=4)
    process = subprocess.Popen([executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, cwd=workspace)

    def read():
        while True:
            line = process.stdout.readline(2 * 1048576)
            if not line:
                return
            try:
                replies.put_nowait(line)
            except queue.Full:
                return

    deadline = threading.Timer(20, process.kill)
    deadline.daemon = True
    deadline.start()
    initialize_legacy(process)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()

    def exchange(raw):
        process.stdin.write(raw + b"\n")
        process.stdin.flush()
        try:
            line = replies.get(timeout=3)
        except queue.Empty:
            raise AssertionError("server did not return one bounded response") from None
        if MARKER.encode() in line:
            raise AssertionError("server reflected private synthetic marker")
        reply = json.loads(line)
        if reply.get("jsonrpc") != "2.0":
            raise AssertionError("invalid response envelope")
        return reply

    cases = corpus(era)
    digest = hashlib.sha256()
    try:
        if era == "legacy":
            exchange(encode(frame(era, method="initialize", protocolVersion="2025-06-18", capabilities={}, clientInfo={"name": "corpus", "version": "1"})))
        else:
            discovered = exchange(encode(frame(era, method="server/discover")))
            if VERSION not in discovered["result"]["supportedVersions"]:
                raise AssertionError("modern discovery missing version")
        for index, (name, raw, expected) in enumerate(cases):
            digest.update(len(raw).to_bytes(4, "big") + raw + str(expected).encode())
            reply = exchange(raw)
            if reply.get("error", {}).get("code") != expected:
                raise AssertionError(f"{era} {name}: expected error {expected}")
            identifier = "recovery-" + str(index)
            recovered = exchange(encode(frame(era, identifier=identifier)))
            expected_result = {} if era == "legacy" else {"resultType": "complete"}
            if recovered.get("id") != identifier or "error" in recovered or not isinstance(recovered.get("result"), dict) or (era == "legacy" and recovered["result"] != {}) or any(recovered.get("result", {}).get(key) != value for key, value in expected_result.items()):
                raise AssertionError(f"{era} {name}: recovery failed")
        process.stdin.close()
        if process.wait(timeout=5) != 0:
            raise AssertionError("server failed after corpus")
        reader.join(timeout=1)
        if not replies.empty():
            raise AssertionError("server emitted extra replies")
        return {"era": era, "hostile_frames": len(cases), "recovery_checks": len(cases), "corpus_sha256": digest.hexdigest()}
    finally:
        deadline.cancel()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        reader.join(timeout=1)
        process.stdin.close()
        process.stdout.close()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: stdio_adversarial_review.py /path/to/runtime-guard-mcp")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="runtime-guard-stdio-review-") as workspace:
        results = [review(executable, era, workspace) for era in ("legacy", "modern")]
    print(json.dumps({"status": "PASS", "seed": SEED, "results": results}, indent=2))


if __name__ == "__main__":
    main()

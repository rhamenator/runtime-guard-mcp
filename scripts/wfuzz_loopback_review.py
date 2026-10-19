#!/usr/bin/env python3
"""Bounded Wfuzz review of an installed Runtime Guard HTTP entry point."""

from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time


def status(port: int, token: str | None) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    try:
        connection.request("POST", "/mcp", b'{"jsonrpc":"2.0","id":1,"method":"ping"}', headers)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def sweep(wfuzz: str, words: Path, url: str, headers: list[str]) -> dict[str, int]:
    command = [wfuzz, "-w", str(words), "-X", "POST", "-H", "Content-Type: application/json"]
    for header in headers:
        command.extend(["-H", header])
    command.extend(["-d", '{"jsonrpc":"2.0","id":1,"method":"ping"}', "-u", url, "-t", "1", "--req-delay", "2", "-o", "json"])
    run = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if run.returncode:
        raise RuntimeError("Wfuzz scan failed")
    # Wfuzz 3.1.0 writes two 'default' lines before its JSON report.
    report = json.loads(run.stdout[run.stdout.index("["):])
    return {item["payload"]: item["code"] for item in report}


def run(executable: str, wfuzz: str) -> dict:
    if not Path(executable).is_file() or not os.access(executable, os.X_OK):
        raise ValueError("provide an installed executable with --server")
    version = subprocess.run([wfuzz, "--version"], capture_output=True, text=True, timeout=5, check=True).stdout.strip().splitlines()[-1]
    token = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="runtime-guard-wfuzz-") as temporary:
        root = Path(temporary)
        (root / "workspace").mkdir()
        config = root / "config.json"
        config.write_text(json.dumps({"workspace_root": str(root / "workspace"), "audit_db": str(root / "audit.sqlite")}))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        environment = dict(os.environ, RUNTIME_GUARD_AUTH_TOKEN=token)
        process = subprocess.Popen([executable, "--transport", "http", "--host", "127.0.0.1", "--port", str(port), "--config", str(config)], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError("installed server exited during startup")
                try:
                    if status(port, None) == 401:
                        break
                except OSError:
                    time.sleep(0.02)
            else:
                raise AssertionError("installed server did not start")
            path_words = root / "paths.txt"
            path_words.write_text("mcp\nadmin\nmetrics\n.env\n")
            paths = sweep(wfuzz, path_words, f"http://127.0.0.1:{port}/FUZZ", ["Authorization: Bearer " + token])
            if paths != {"mcp": 200, "admin": 404, "metrics": 404, ".env": 404}:
                raise AssertionError(f"unexpected path status codes: {paths}")
            auth_words = root / "auth.txt"
            auth_words.write_text("invalid\n" + token + "\n")
            auth = sweep(wfuzz, auth_words, f"http://127.0.0.1:{port}/mcp", ["Authorization: Bearer FUZZ"])
            auth_result = {"invalid": auth.get("invalid"), "generated-valid-token": auth.get(token)}
            if auth_result != {"invalid": 401, "generated-valid-token": 200} or len(auth) != 2:
                raise AssertionError(f"unexpected auth status codes: {auth_result}")
            if status(port, token) != 200:
                raise AssertionError("server did not recover after fuzzing")
            return {"status": "PASS", "scanner": f"Wfuzz {version}", "target": "installed entry point on ephemeral loopback HTTP", "requests": 6, "path_statuses": paths, "auth_statuses": auth_result, "recovery": 200}
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, help="path to an installed runtime-guard-mcp executable")
    parser.add_argument("--wfuzz", default="wfuzz", help="Wfuzz executable")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.server, args.wfuzz), indent=2))
    except (AssertionError, IndexError, KeyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "FAIL", "reason": str(error)}), file=sys.stderr)
        raise SystemExit(1) from error

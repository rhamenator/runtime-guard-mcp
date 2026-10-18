#!/usr/bin/env python3
"""Bounded remote probe for a loopback Runtime Guard MCP endpoint.

All payloads are synthetic. Proposed shell commands are classified, never run.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def post(url: str, message: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    body = json.dumps(message, separators=(",", ":")).encode()
    request = Request(url, body, {"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, json.load(error)


class Probe:
    def __init__(self, url: str):
        self.url = url
        self.next_id = 1

    def request(self, method: str, params: dict | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict]:
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        self.next_id += 1
        if params is not None:
            message["params"] = params
        return post(self.url, message, headers)

    def call(self, name: str, arguments: dict) -> dict:
        status, response = self.request("tools/call", {"name": name, "arguments": arguments})
        assert status == 200 and "result" in response, f"{name}: unexpected transport result"
        return response["result"]["structuredContent"]


def run(url: str, budget_limit: int | None) -> None:
    host = urlsplit(url).hostname
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Probe requires a loopback URL; use an SSH local port forward.")
    probe = Probe(url)
    status, response = probe.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "adversarial-probe", "version": "1"}})
    assert status == 200 and response["result"]["serverInfo"]["name"] == "runtime-guard-mcp"
    status, response = probe.request("tools/list")
    assert status == 200
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert {"audit_path_access", "dry_run_command", "budget_guard", "secret_masker"} <= names
    print("PASS protocol discovery")

    for command, expected in (
        ("find . -delete", "NEEDS_CONFIRMATION"),
        ("find . -exec rm -rf /tmp/example {} +", "BLOCKED"),
        ("cat /proc/self/environ", "BLOCKED"),
        ("cat ~/.config/gcloud/application_default_credentials.json", "BLOCKED"),
    ):
        result = probe.call("dry_run_command", {"command": command})
        assert result["status"] == expected, f"shell classification mismatch: {result['rule']}"
    print("PASS shell classification")

    result = probe.call("audit_path_access", {"path": "../../etc/shadow"})
    assert result["status"] == "BLOCKED"
    print("PASS path containment")

    synthetic = "ghp_" + "A" * 24
    emitted = []
    for character in synthetic:
        emitted.append(probe.call("secret_masker", {"session_id": "probe", "stream_id": "split", "chunk": character, "final": False})["text"])
    emitted.append(probe.call("secret_masker", {"session_id": "probe", "stream_id": "split", "chunk": "", "final": True})["text"])
    output = "".join(emitted)
    assert synthetic not in output and "[REDACTED_GITHUB_TOKEN_" in output
    print("PASS chunked redaction")

    status, response = post(url, {"jsonrpc": "2.0", "id": True, "method": "ping"})
    assert status == 200 and response["error"]["code"] == -32600
    status, response = probe.request("tools/call", {"name": "missing", "arguments": {}})
    assert status == 200 and response["error"]["code"] == -32602
    print("PASS malformed protocol inputs")

    for headers in ({"Origin": "https://invalid.example"}, {"Host": "invalid.example"}):
        status, _ = probe.request("ping", headers=headers)
        assert status == 403
    print("PASS Host and Origin rejection")

    if budget_limit is not None:
        assert 1 <= budget_limit <= 100
        # Run only against a fresh server configured with token_hour=budget_limit.
        def reserve(_: int) -> str:
            return probe.call("budget_guard", {"session_id": "probe-budget", "tokens": 1, "consume": True})["status"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(reserve, range(budget_limit + 2)))
        assert outcomes.count("SAFE") == budget_limit and outcomes.count("BLOCKED") == 2
        print("PASS concurrent budget reservations")


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic Runtime Guard remote probe")
    parser.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--budget-limit", type=int, help="Run budget concurrency probe against a fresh server with this token_hour limit")
    args = parser.parse_args()
    try:
        run(args.url, args.budget_limit)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

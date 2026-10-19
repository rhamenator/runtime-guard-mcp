"""Probe the installed stdio entry point as a minimal MCP client.

Usage: python3 scripts/client_smoke.py /path/to/runtime-guard-mcp
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: client_smoke.py /path/to/runtime-guard-mcp")
    with tempfile.TemporaryDirectory(prefix="runtime-guard-client-") as workspace:
        env = os.environ.copy()
        env["RUNTIME_GUARD_WORKSPACE_ROOT"] = workspace
        env.pop("RUNTIME_GUARD_CONFIG", None)
        with subprocess.Popen(
            [sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env,
        ) as server:
            assert server.stdin and server.stdout

            def request(identifier: int, method: str, params: dict | None = None) -> dict:
                message = {"jsonrpc": "2.0", "id": identifier, "method": method}
                if params is not None:
                    message["params"] = params
                server.stdin.write((json.dumps(message) + "\n").encode())
                server.stdin.flush()
                line = server.stdout.readline()
                if not line:
                    raise AssertionError("server closed before replying")
                reply = json.loads(line)
                assert reply.get("id") == identifier, reply
                assert "error" not in reply, reply
                return reply["result"]

            initialized = request(1, "initialize", {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "client-smoke", "version": "1"},
            })
            assert initialized["protocolVersion"] == "2025-06-18", initialized
            assert initialized["capabilities"] == {"tools": {"listChanged": False}}
            server.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            server.stdin.flush()
            tools = request(2, "tools/list")["tools"]
            assert [tool["name"] for tool in tools] == [
                "audit_path_access", "dry_run_command", "budget_guard", "secret_masker"
            ]
            for tool in tools:
                assert tool["inputSchema"]["type"] == "object"
                assert tool["outputSchema"]["type"] == "object"
            result = request(3, "tools/call", {
                "name": "audit_path_access",
                "arguments": {"path": str(Path(workspace) / "example.txt"), "operation": "read"},
            })
            assert result["isError"] is False, result
            structured = result["structuredContent"]
            assert structured["status"] == "SAFE", result
            assert json.loads(result["content"][0]["text"]) == structured
            server.stdin.close()
            assert server.wait(timeout=5) == 0
    print("PASS: installed stdio initialize, tools/list schemas, and tools/call")


if __name__ == "__main__":
    main()

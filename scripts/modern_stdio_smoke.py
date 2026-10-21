"""Dependency-free installed MCP 2026 stdio probe; no inference or network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PREFIX = "io.modelcontextprotocol/"
VERSION = "2026-07-28"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: modern_stdio_smoke.py /path/to/runtime-guard-mcp")
    with tempfile.TemporaryDirectory(prefix="runtime-guard-modern-") as workspace:
        env = os.environ.copy()
        for key in ("PYTHONPATH", "PYTHONHOME", "RUNTIME_GUARD_CONFIG", "RUNTIME_GUARD_AUDIT_DB"):
            env.pop(key, None)
        env["RUNTIME_GUARD_WORKSPACE_ROOT"] = workspace
        frames = []
        for identifier, method, extra in ((1, "server/discover", {}), (2, "tools/list", {}), (3, "tools/call", {"name": "dry_run_command", "arguments": {"command": "git status"}}), (4, "ping", {})):
            frames.append({"jsonrpc": "2.0", "id": identifier, "method": method, "params": {"_meta": {PREFIX + "protocolVersion": VERSION, PREFIX + "clientCapabilities": {}}, **extra}})
        frames.insert(3, {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": "unknown", "reason": "late cancellation fixture"}})
        frames.append({"jsonrpc": "2.0", "id": 5, "method": "ping", "params": {"_meta": {PREFIX + "protocolVersion": "2099-01-01", PREFIX + "clientCapabilities": {}}}})
        frames.append({"jsonrpc": "2.0", "id": 6, "method": "server/discover", "params": {"_meta": {PREFIX + "protocolVersion": VERSION}}})
        run = subprocess.run([str(Path(sys.argv[1]).resolve())], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), capture_output=True, cwd=workspace, env=env, timeout=10, check=True)
        replies = [json.loads(line) for line in run.stdout.splitlines()]
        assert [reply["id"] for reply in replies] == [1, 2, 3, 4, 5, 6], replies
        for reply in replies[:4]:
            assert reply["result"]["resultType"] == "complete", reply
            assert PREFIX + "serverInfo" in reply["result"]["_meta"], reply
        assert replies[0]["result"]["supportedVersions"] == [VERSION, "2025-06-18"]
        names = [tool["name"] for tool in replies[1]["result"]["tools"]]
        assert names == sorted(names) and len(names) == 4, names
        assert replies[2]["result"]["structuredContent"]["status"] == "SAFE"
        assert replies[4]["error"]["code"] == -32022
        assert replies[5]["error"]["code"] == -32602
    print("PASS: installed modern stdio discovery, metadata, tool, version errors and late cancellation recovery")


if __name__ == "__main__":
    main()

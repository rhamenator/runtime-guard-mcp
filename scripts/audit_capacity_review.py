"""Installed stdio audit-capacity/restart/backup/fresh-file review, both protocol eras."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

PREFIX = "io.modelcontextprotocol/"


def review(executable, root, era):
    audit, config = root / (era + ".sqlite"), root / (era + ".json")
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "RUNTIME_GUARD_CONFIG"):
        env.pop(key, None)

    def run(methods):
        frames = []
        for index, method in enumerate(methods):
            params = {} if method == "ping" else {"name": "dry_run_command", "arguments": {"command": "git status"}}
            if era == "modern":
                params["_meta"] = {PREFIX + "protocolVersion": "2026-07-28", PREFIX + "clientCapabilities": {}}
            frames.append({"jsonrpc": "2.0", "id": index + 1, "method": method, "params": params})
        result = subprocess.run([executable, "--config", str(config)], input=b"".join(json.dumps(frame).encode() + b"\n" for frame in frames), capture_output=True, cwd=root, env=env, timeout=8, check=True)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        assert [reply["id"] for reply in replies] == list(range(1, len(frames) + 1)), replies
        return [reply["result"] for reply in replies]

    def rows(path):
        connection = sqlite3.connect(path)
        try:
            return connection.execute("SELECT * FROM decisions ORDER BY rowid").fetchall()
        finally:
            connection.close()

    config.write_text(json.dumps({"workspace_root": str(root), "audit_db": str(audit), "audit_max_records": 2}))
    results = run(["tools/call"] * 3 + ["ping"])
    assert [result["structuredContent"]["rule"] for result in results[:3]] == ["READ_ONLY_COMMAND", "READ_ONLY_COMMAND", "AUDIT_CAPACITY"]
    assert results[2]["isError"] is True
    assert json.loads(results[2]["content"][0]["text"]) == results[2]["structuredContent"]
    assert "READ_ONLY_COMMAND" not in results[2]["content"][0]["text"]
    if era == "legacy":
        assert results[3] == {}
    else:
        assert results[3]["resultType"] == "complete"
    original = rows(audit)
    assert len(original) == 2
    assert run(["tools/call"])[0]["structuredContent"]["rule"] == "AUDIT_CAPACITY"
    assert rows(audit) == original
    archive = root / (era + "-archive.sqlite")
    source, destination = sqlite3.connect(audit), sqlite3.connect(archive)
    try:
        source.backup(destination)
    finally:
        source.close()
        destination.close()
    assert rows(archive) == original
    fresh = root / (era + "-fresh.sqlite")
    config.write_text(json.dumps({"workspace_root": str(root), "audit_db": str(fresh), "audit_max_records": 2}))
    assert run(["tools/call"])[0]["structuredContent"]["rule"] == "READ_ONLY_COMMAND"
    assert len(rows(fresh)) == 1
    assert rows(audit) == original
    return {"era": era, "retained_records": 2, "restart_blocked": True, "backup_preserved": True, "fresh_file_recovered": True}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_capacity_review.py /path/to/runtime-guard-mcp")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="runtime-guard-capacity-") as directory:
        results = [review(executable, Path(directory), era) for era in ("legacy", "modern")]
    print(json.dumps({"status": "PASS", "results": results}, indent=2))


if __name__ == "__main__":
    main()

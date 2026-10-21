"""Fresh-install stdio probe using the optional official Python MCP SDK.

Install the server and `mcp==2.3.0` in a disposable virtual environment, then run:
python scripts/official_sdk_smoke.py /path/to/runtime-guard-mcp
"""

import os
import sys
import tempfile

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def probe(executable: str) -> None:
    with tempfile.TemporaryDirectory(prefix="runtime-guard-sdk-") as workspace:
        env = {**os.environ, "RUNTIME_GUARD_WORKSPACE_ROOT": workspace}
        env.pop("RUNTIME_GUARD_CONFIG", None)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        parameters = StdioServerParameters(command=executable, env=env, cwd=workspace)
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                initialized = await session.initialize()
                assert initialized.protocol_version == "2025-06-18"
                assert initialized.capabilities.tools is not None
                listed = await session.list_tools()
                assert [tool.name for tool in listed.tools] == [
                    "audit_path_access", "dry_run_command", "budget_guard", "secret_masker"
                ]
                for tool in listed.tools:
                    assert tool.input_schema["type"] == "object"
                    assert tool.output_schema["type"] == "object"
                called = await session.call_tool("dry_run_command", {"command": "git status"})
                assert called.is_error is False
                assert called.structured_content["status"] == "SAFE"
    print("PASS: official SDK stdio initialize, tools/list schemas, and tools/call")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: official_sdk_smoke.py /path/to/runtime-guard-mcp")
    anyio.run(probe, sys.argv[1])

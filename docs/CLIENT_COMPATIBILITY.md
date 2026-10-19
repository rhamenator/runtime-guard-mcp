# Client interoperability evidence

This records verified behavior for revision `384df80` plus the client smoke scripts in this branch. The server is advisory and is not yet a stable release.

## Reproduce the fresh install

Use Python 3.11 or newer in an empty virtual environment. The following was run with Python 3.12.3 on 2026-10-18:

```bash
python3 -m venv /tmp/runtime-guard-smoke
/tmp/runtime-guard-smoke/bin/python -m pip install .
python3 scripts/client_smoke.py /tmp/runtime-guard-smoke/bin/runtime-guard-mcp
/tmp/runtime-guard-smoke/bin/python -m pip install 'mcp==2.3.0'
/tmp/runtime-guard-smoke/bin/python scripts/official_sdk_smoke.py /tmp/runtime-guard-smoke/bin/runtime-guard-mcp
```

The installed distribution has no third-party runtime requirements. The MCP SDK is a test-only dependency. Both probes use a temporary workspace, clear `RUNTIME_GUARD_CONFIG`, and launch the installed stdio entry point. They check `initialize` (negotiated `2025-06-18` and tool capability), `tools/list` (four names and input/output schema objects), and `tools/call` (structured result and text fallback). The local probe also checks the initialized notification and a path check. Expected output is a `PASS` line from each command.

## Limits

The probes do not establish Codex, Claude Code, or Cursor end-to-end integration. No fresh install in those clients has been completed. Cursor CLI is unavailable on this host. They also do not establish MCP `2026-07-28` or full Streamable HTTP conformance. The current HTTP endpoint is JSON-RPC over HTTP; stdio is the tested buyer path. Do not list a client as supported from these probes alone.

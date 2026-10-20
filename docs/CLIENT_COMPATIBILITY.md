# Client interoperability evidence

This records verified behavior for the installed server at revision `58cc1b7` and the CLI versions noted below. The server is advisory and is not yet a stable release.

## Reproduce the fresh install

Use Python 3.11 or newer in an empty virtual environment. The following was run with Python 3.12.3 on 2026-10-18:

```bash
python3 -m venv /tmp/runtime-guard-smoke
/tmp/runtime-guard-smoke/bin/python -m pip install .
python3 scripts/client_smoke.py /tmp/runtime-guard-smoke/bin/runtime-guard-mcp
/tmp/runtime-guard-smoke/bin/python -m pip install 'mcp==2.3.0'
/tmp/runtime-guard-smoke/bin/python scripts/official_sdk_smoke.py /tmp/runtime-guard-smoke/bin/runtime-guard-mcp
```

CI builds a wheel on Python 3.11 and 3.13, installs it without dependencies into a fresh virtual environment, and runs the minimal stdio client against that installed executable with a 20-second process limit. This verifies the packaged entry point and tool workflow on each change; it does not replace the application-specific client probes below.

The installed distribution has no third-party runtime requirements. The MCP SDK is a test-only dependency. Both probes use a temporary workspace, clear `RUNTIME_GUARD_CONFIG`, and launch the installed stdio entry point. They check `initialize` (negotiated `2025-06-18` and tool capability), `tools/list` (four names and input/output schema objects), and `tools/call` (structured result and text fallback). The local probe also checks the initialized notification and a path check. Expected output is a `PASS` line from each command.

## Claude Code 2.1.301

An isolated Claude Code session completed a real stdio call on 2026-10-18. With the installed server executable and a temporary workspace, this MCP config was used (replace the paths with your own virtual environment and workspace):

```json
{"mcpServers":{"runtime-guard":{"type":"stdio","command":"/path/to/venv/bin/runtime-guard-mcp","args":[],"env":{"RUNTIME_GUARD_WORKSPACE_ROOT":"/path/to/workspace"}}}}
```

The one-shot command was:

```bash
claude -p --mcp-config /path/to/config.json --strict-mcp-config \
  --no-session-persistence --max-turns 3 \
  --allowedTools 'mcp__runtime-guard__dry_run_command' \
  --output-format stream-json --verbose \
  'Call the runtime-guard dry_run_command MCP tool exactly once with command git status. Report only the tool status and rule.'
```

The event stream showed `mcp__runtime-guard__dry_run_command` called with `{"command":"git status"}` and a tool result of `{"status":"SAFE","rule":"READ_ONLY_COMMAND","remediation":"No remediation needed."}`. Without `--allowedTools`, the client reported a permission denial for that MCP tool; this is a client permission decision, not a server verdict. Grant only the individual advisory tool needed for the session. No other Claude Code workflow or transport was tested.

## Codex CLI 0.151.0

An isolated `CODEX_HOME` with a single `[mcp_servers.runtime_guard]` stdio entry appeared in `codex mcp list --json` as enabled. A one-shot `codex exec --ignore-user-config --ephemeral -s read-only` session attempted `dry_run_command`, but the event stream reported `MCP tool call requires approval, but approval policy is never`. The agent's final prose incorrectly reported `SAFE` after this denied call. Integration code and users must rely on the MCP tool event/result, and treat denied or failed calls as unavailable. The server itself was not called in that attempt.

A second isolated Codex session on 2026-10-19 used a temporary workspace and the CLI's `--approve-for-me` review option. The command was:

```bash
codex exec --ignore-user-config --ephemeral --skip-git-repo-check \
  --approve-for-me -C /path/to/temporary/workspace \
  -c 'mcp_servers.runtime_guard={command="/path/to/venv/bin/runtime-guard-mcp",env={RUNTIME_GUARD_WORKSPACE_ROOT="/path/to/temporary/workspace"}}' \
  --json \
  'Call the runtime_guard dry_run_command MCP tool exactly once with command git status. Do not run a shell. Report the tool result status and rule only if the MCP call succeeded; otherwise report the call failure.'
```

The `mcp_tool_call` event had `status: completed`, `error: null`, and `structured_content` containing `status: SAFE`, `rule: READ_ONLY_COMMAND`, and `remediation: No remediation needed.` The approval option was used only for this bounded smoke test; normal client integrations should use their intended permission review policy. This does not establish that Codex automatically intercepts shell commands or enforces the advisory verdict.

## Limits

Claude Code and Codex each completed one local stdio call with explicit tool permission. Cursor CLI is unavailable on this host. The probes do not establish MCP `2026-07-28` or full Streamable HTTP conformance. The current HTTP endpoint is JSON-RPC over HTTP; stdio is the tested buyer path. Do not list a client as fully supported from these probes alone.

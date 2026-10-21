# Client interoperability evidence

This records versioned observations for installed server revisions and CLI versions noted below. The server is advisory and is not yet a stable release.

## Reproduce the fresh install

Use Python 3.11 or newer in an empty virtual environment. The following was run with Python 3.12.3 on 2026-10-18:

```bash
python3 -m venv /tmp/runtime-guard-smoke
/tmp/runtime-guard-smoke/bin/python -m pip install .
python3 scripts/client_smoke.py /tmp/runtime-guard-smoke/bin/runtime-guard-mcp
/tmp/runtime-guard-smoke/bin/python -m pip install 'mcp==2.3.0'
/tmp/runtime-guard-smoke/bin/python scripts/official_sdk_smoke.py /tmp/runtime-guard-smoke/bin/runtime-guard-mcp
```

CI builds a wheel on Python 3.11, 3.12, 3.13, and 3.14, installs it without dependencies into a fresh virtual environment, and runs the minimal stdio client against that installed executable with a 20-second process limit. CI also runs the full live adversarial probe against that installed executable, including HTTP and stdio failure/recovery paths. This verifies the packaged entry point and tool workflow on each change; it does not replace the application-specific client probes below.

The installed distribution has no third-party runtime requirements. The MCP SDK is a test-only dependency. CI runs SDK 2.3.0 on Python 3.12 in a separate client virtual environment, against the dependency-free installed server environment, with a 30-second limit. The SDK subprocess starts the server from its temporary workspace with Python path overrides cleared. SDK transitive packages are resolved during client setup; they are not server requirements. Both probes use a temporary workspace and launch the installed stdio entry point. The minimal client clears `RUNTIME_GUARD_CONFIG`; the SDK client replaces it with a disposable configuration containing a two-token budget and an audit database. They check `initialize` (negotiated `2025-06-18` and tool capability), `tools/list` (four names and input/output schema objects), and `tools/call` (structured result and text fallback). The minimal probe also checks the initialized notification and a path check. The SDK probe additionally requires path escape and instruction-like deletion to be blocked, proves the token budget applies across different session IDs, and checks synthetic secret masking plus audit database/sidecar bytes. It verifies a temporary sentinel remains unchanged. Expected output is a `PASS` line from each command.

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

## Cursor CLI 2026.10.19-6bbf2c4

On 2026-10-21, an authenticated Cursor CLI discovered all four tools from a wheel built at server revision `7e2f209`. A temporary ACP session then exposed only `dry_run_command` and completed exactly two inspections. The independent SQLite audit recorded `SAFE` / `READ_ONLY_COMMAND` and `BLOCKED` / `RECURSIVE_DELETE`; a temporary sentinel remained unchanged. Two tool permission requests were approved. The sanitized [evidence record](evidence/cursor-cli-2026-10-21.json) pins the wheel digest.

For a normal installation, create a project-local `.cursor/mcp.json` after installing the server:

```json
{"mcpServers":{"runtime_guard":{"command":"/path/to/venv/bin/runtime-guard-mcp","env":{"RUNTIME_GUARD_WORKSPACE_ROOT":"/path/to/project"}}}}
```

From that project directory, run `agent mcp enable runtime_guard` and `agent mcp list-tools runtime_guard`. Use the existing Cursor login, or run `agent login` if needed; never put account credentials into project files. Cursor account/model usage may incur service costs independently of this server. Keep normal tool permission review enabled.

To reproduce the bounded authenticated ACP probe on Linux:

```bash
python3 scripts/cursor_client_smoke.py --server /path/to/venv/bin/runtime-guard-mcp --client /path/to/agent
```

The script creates and removes a temporary project and audit store, uses existing account authentication, and requests one agent turn with two synthetic inspections. Its ACP permission handler allows once only for permission titles containing `dry_run_command` and rejects other requests. It does not use a global force-allow option. The ACP phase has a 90-second deadline; discovery/setup have separate short timeouts. It prints only sanitized results and terminates its isolated process group. This is an optional authenticated host probe, not CI. Terminal UI, cancellation propagation, and whole-agent enforcement are not established.

## Limits

Claude Code and Codex each completed one local stdio call with explicit tool permission. Cursor CLI completed discovery and two ACP-driven stdio calls as described above; terminal UI and cancellation remain unverified. The probes do not establish MCP `2026-07-28` or full Streamable HTTP conformance. The current HTTP endpoint is JSON-RPC over HTTP; stdio is the tested buyer path. Do not list a client as fully supported from these probes alone.

## Modern stdio implementation

MCP 2026-07-28 per-request stdio discovery, result envelopes, version errors and cancellation dispatch are implemented. `scripts/modern_stdio_smoke.py` probes a fresh wheel with an independent, dependency-free wire client in CI. Controlled slow-policy tests exercise active and queued cancellation. The official SDK and coding-client evidence above uses legacy initialization; modern authenticated client and UI cancellation probes remain required. The HTTP endpoint does not advertise modern transport support.

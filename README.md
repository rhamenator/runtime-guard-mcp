# runtime-guard-mcp

[![CI](https://github.com/rhamenator/runtime-guard-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rhamenator/runtime-guard-mcp/actions/workflows/ci.yml) [![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](LICENSE)

An MCP server for **advisory** runtime safety checks in coding agents. It inspects proposed file paths and shell commands, tracks caller budgets, detects repeated actions, and masks common credentials in output. It never executes shell commands or opens the target files. It is separate from [request-guard-mcp](https://github.com/rhamenator/request-guard-mcp), which handles request classification and is being extended for HTTP egress.

## Run locally

Python 3.11 or newer; the runtime uses only the standard library. See [dependency decisions](docs/dependencies.md) for the packaging and protocol tradeoffs.

```bash
python3 -m pip install --no-build-isolation -e .
RUNTIME_GUARD_WORKSPACE_ROOT="$PWD" runtime-guard-mcp
```

The default transport is MCP over stdio. Keep stdout reserved for JSON-RPC. A client can configure a local stdio server with command `runtime-guard-mcp` and environment variable `RUNTIME_GUARD_WORKSPACE_ROOT` set to the intended workspace.

For a local HTTP endpoint:

```bash
runtime-guard-mcp --transport http --host 127.0.0.1 --port 8765
```

The HTTP endpoint is `/mcp`. It handles JSON-RPC POST requests and returns JSON responses; GET streaming is unsupported. Non-loopback binding requires `RUNTIME_GUARD_AUTH_TOKEN`, and public deployment also needs TLS termination and explicit network controls. The server checks `Origin` and `Host`. HTTP connections have a five-second total deadline as well as a five-second inactivity timeout; slow legitimate uploads may be disconnected. A fresh installed stdio entry point passed repeatable initialize, list, and call probes with a minimal client and the official Python MCP SDK 2.3.0; see [client interoperability evidence](docs/CLIENT_COMPATIBILITY.md). Claude Code and Codex CLI each completed one local stdio call with explicit tool permission. Cursor remains untested.

Copy [the config example](runtime-guard.example.json), set `RUNTIME_GUARD_CONFIG` to its path, and adjust budgets using the [config schema](schemas/config.schema.json). `allowed_roots` are operator configured extra roots; no MCP call can change them. `audit_db` enables SQLite decision metadata only (timestamp, hashed caller, tool, status, rule). Leave it null to disable audit persistence. Set `enabled_tools` to hide tools your environment does not need.

## Tools

| Tool | Result | Limit |
| --- | --- | --- |
| `audit_path_access` | `SAFE`, `NEEDS_CONFIRMATION`, or `BLOCKED` for a proposed path | A check cannot prevent later symlink changes or direct file access by other tools |
| `dry_run_command` | Risk tier for shell text | A heuristic parser cannot prove a command safe; it never runs the command |
| `budget_guard` | Caller-wide token, payload, command, and loop budget | Agents must report usage; this does not meter other tools automatically |
| `secret_masker` | Text with stable `[REDACTED_*]` placeholders | Signature based; unknown formats can remain unmasked |

Blocked tool calls return an MCP tool result with `isError: true`, structured JSON, and a text fallback. Protocol errors use JSON-RPC errors. [Tool declarations](schemas/tools.json) include input and output schemas.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

See [release quality gates](docs/QUALITY_BAR.md), [contributing](CONTRIBUTING.md), [security reporting](SECURITY.md), [support](SUPPORT.md), [the changelog](CHANGELOG.md), and [architecture and roadmap](docs/architecture.md), [security model](docs/security.md), and the [draft agent skill](skills/runtime-guard/SKILL.md). The skill is for client integration after the user has configured this server; it does not grant permission for tool execution.

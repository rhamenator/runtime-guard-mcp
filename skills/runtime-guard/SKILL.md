---
name: runtime-guard
description: Use a connected runtime-guard-mcp server to assess proposed coding-agent file and shell actions, track reported budgets, and redact output. Applies when this separate advisory MCP server is configured; not for HTTP egress or inbound scraping defense.
---

# Runtime Guard

Install and connect [Runtime Guard MCP](https://github.com/rhamenator/runtime-guard-mcp) by stdio, with `RUNTIME_GUARD_WORKSPACE_ROOT` set to the intended workspace. Confirm `tools/list` advertises the needed tool before using it. This skill does not install the server or grant execution permission.

## Choose the tool

- Before a file read, write, or delete with an uncertain boundary, call `audit_path_access` using the exact path and operation. Recheck after the path or filesystem state changes; a prior result does not authorize a later action.
- Before a shell command with uncertain or destructive effects, call `dry_run_command` with the exact command and shell. The server analyzes text and never executes it.
- When a workflow needs usage limits, call `budget_guard` with the actual session and reported token, payload, and command counts. Use `consume=true` only when reserving that usage; give repeated actions a stable fingerprint so the server can detect loops.
- When command output or fetched text may contain credentials, use `secret_masker` with one stream ID across chunks and `final=true` to flush the last chunk. Keep unredacted text out of subsequent model-visible output when practical.

Treat `BLOCKED` as a stop for the proposed action and report its rule and remediation. Treat `NEEDS_CONFIRMATION` as a request for human review. `SAFE` is a heuristic advisory result, not a permission grant or proof that a command or path is harmless. The server cannot see actions routed through other tools; host and client controls are needed for enforcement.

HTTP parser and unsupported-method failures return generic JSON HTTP errors without reflecting request data. Treat them as transport failures; HEAD error responses omit the body.

Invalid JSON-RPC ID types produce `-32600` with a null response ID even when the request envelope is malformed. Correct the request before retrying.

Use UTF-8 JSON configuration without duplicate keys or non-finite numbers. Invalid, unreadable, or oversized configuration stops startup; correct the file before reconnecting.

For JSON-RPC calls, omit `params` or send an object or array. Scalar parameters return `-32602`; tool calls require the documented object fields.

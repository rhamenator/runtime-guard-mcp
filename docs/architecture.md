# Architecture and implementation roadmap

## Boundary

`runtime-guard-mcp` is a local policy advisor. The agent host calls one of four MCP tools, the server returns a structured risk result, and the host or user decides whether to perform an action. It cannot intercept arbitrary filesystem, shell, or model activity. Strong enforcement requires routing actions through a trusted execution wrapper or OS sandbox. The service does not ask for credentials or read target files. Request safety remains in `request-guard-mcp`.

## Components

* `server.py`: stdio and local HTTP JSON-RPC transport, tool discovery, validation, and structured results.
* `policy.py`: lexical and resolved path checks; conservative shell classification; caller budget windows and repeated action tracking; bounded secret masking.
* `audit.py`: optional SQLite decision metadata. No raw paths, commands, payloads, or secret values are persisted.

State is scoped by authenticated caller (HTTP bearer token, if configured) or local stdio process. Current HTTP deployments support a single configured bearer credential and one shared budget scope. In memory state resets on restart; only redacted audits persist when `audit_db` is configured. A multi-tenant or multi-replica service would need authenticated caller identities and atomic shared state.

## Behavior and risk tiers

`audit_path_access` resolves existing symlinks, rejects paths outside configured roots and sensitive path names, and marks deletion for confirmation. Because it does not open or lock a target, a later operation can race with filesystem changes. `dry_run_command` blocks known destructive patterns, marks nested/compound/privileged commands for confirmation, and marks a small read-only allowlist safe. `SAFE` is a classification, not authorization. PowerShell is supported conservatively through heuristics; full AST parsing is future work.

`budget_guard` uses caller-wide one-hour token and payload windows, a one-minute command window, and session-scoped repeated fingerprint detection over five minutes. `consume=true` reserves reported usage atomically within one process. Calls without `consume` are previews. `secret_masker` recognizes common token and private-key formats and assignment patterns. It holds a bounded tail to catch tokens split across chunks and uses stable placeholders scoped to the caller. It does not promise detection of every credential or private identifier.

## Milestones

| Milestone | Deliverable | Verification |
| --- | --- | --- |
| 1. Core protocol | stdio MCP initialize, tools/list, tools/call and schemas | subprocess contract tests, malformed request checks |
| 2. Policy tools | path, command, budgets, masker | symlink escape, destructive command, cross-session budget, chunk boundary tests |
| 3. Local operations | HTTP POST transport, config, redacted SQLite audit | HTTP smoke test, Origin/Host denial, config checks, audit content test |
| 4. Release | client recipes, package publishing, Agensi listing and MCP Registry metadata | fresh-machine install, client SDK compatibility, security review, registry validation before publication |

Milestones 1–3 are implemented locally. In addition to the standard-library tests, the official Python MCP SDK 2.3.0 completed initialize, `tools/list`, and `tools/call` over both stdio and Streamable HTTP on 2026-10-18. Milestone 4 remains open until distribution and Codex, Claude Code, and Cursor validation are complete. No external listing or repository publication is implied by these local files.

The [registry metadata example](server.json.example) is a template for a future published PyPI package and GitHub repository; its URLs and package ownership must be verified before validation or submission. Agensi lists `SKILL.md` workflows separately from the official MCP Registry. The local skill documents the integration workflow but has not been submitted.

## Reuse and economy

This project reuses the established MCP pattern from the user's Rust servers: declared tools, per-caller state, structured decisions, and redacted telemetry. It keeps the same privacy rule of never logging raw credentials. The repository's `AGENTS.md` instructs future Codex work to search narrowly, reuse helpers, run focused tests before the full suite, and avoid repeated large logs. That keeps maintenance efficient without weakening verification.

## Protocol references

* [MCP tools and result errors](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
* [MCP Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
* [Official registry metadata requirements](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)

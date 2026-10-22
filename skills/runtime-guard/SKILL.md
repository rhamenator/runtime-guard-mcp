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

Cursor CLI 2026.10.19-6bbf2c4 has bounded ACP/stdio discovery and safe/blocked inspection evidence. Configure the installed server in project-local `.cursor/mcp.json`, run `agent mcp enable runtime_guard` and `agent mcp list-tools runtime_guard` from that project, and retain normal tool permissions. Existing Cursor authentication is required; account/model service costs are separate. Terminal UI and cancellation remain unverified.

Custom MCP clients must initialize with `protocolVersion`, an object `capabilities`, and `clientInfo` containing string `name` and `version`. Correct malformed initialization fields after `-32602` before retrying.

Request parameters and optional `_meta` must be objects. Arrays or malformed metadata return `-32602` before tool dispatch; retry with the documented tool arguments. MCP 2026 negotiation remains unfinished.

### Modern stdio requests and cancellation

Modern clients may call `server/discover` without initialization, supplying `_meta.io.modelcontextprotocol/protocolVersion` (`2026-07-28`) and `_meta.io.modelcontextprotocol/clientCapabilities` (an object) on every request. Legacy clients retain the initialization workflow above. Modern results include `resultType: complete`. This modern implementation is still undergoing release conformance and client review; use stdio, as HTTP remains legacy.

Cancel a pending stdio request using `notifications/cancelled` with its string or integer `requestId`. Queued work is discarded and an active reply is suppressed; already applied budget/masker/audit changes are not undone, and running policy functions finish. This grants no execution permission. At most 32 requests may be outstanding; error `1001` asks the client to retry after pending work completes. See the README for EOF and output-backpressure limitations.

Modern request IDs must be strings or integers, including requests with unsupported versions; null/float IDs return `-32600`. Optional modern `clientInfo.title` must be a string or the request returns `-32602`. These checks add no permissions.

### Audit capacity

If the separately configured server enables `audit_db`, `audit_max_records` defaults to 100000 (positive integer). `BLOCKED` / `AUDIT_CAPACITY` means the file has reached its committed-record limit; do not run the proposed action or repeatedly retry budget/masking calls. Ask the operator to stop the server, verify and preserve an SQLite backup, retain the final hash externally, and configure a fresh audit file before restarting. Do not delete rows or disable auditing to bypass the decision. The README describes permissions and the tested backup/restart workflow. This is a record limit, not a byte quota or automatic rotation, and new files do not automatically anchor previous chains. No new execution permission is granted.

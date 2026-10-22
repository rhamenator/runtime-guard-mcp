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

If the server exits with status 2 and `Cannot initialize Runtime Guard`, stop the workflow and ask the operator to check workspace/audit access, competing writers, storage and integrity. Startup has not exposed tools on either transport. Do not delete audit rows to fix it; preserve evidence and use the README repair/retry guidance. Handled startup diagnostics omit raw paths and SQLite details.

Client turn interruption is not proof of MCP cancellation. In the documented instrumented real-client review, Claude sent matching cancellation; Codex/Cursor omitted it in their tested paths. Treat an interrupted turn as potentially completed policy work, inspect actual tool/audit outcomes, and do not assume budget or audit rollback. The optional developer probes require existing client authentication and may consume model usage; they are not installation requirements. See `docs/CLIENT_CANCELLATION.md` in the server repository.

Codex CLI 0.151.0 app-server interruption is acknowledged at the client but does not send MCP cancellation in the tested path. Treat interrupted tool outcomes as unknown; do not automatically replay consuming budget reservations or masking chunks. A fresh read-only advisory call can verify connectivity, not prior cancellation. Restart resets volatile budget/masker state and preserves configured persistent audit records; it is not rollback. No server setting can supply a missing client notification. See the client-specific recovery procedure in `docs/CLIENT_CANCELLATION.md`.

For modern stdio, send object-shaped experimental/extension settings and sampling/elicitation options; extension identifiers need a valid metadata prefix. Declaring a capability does not enable it or grant permissions. `tools/list` returns one terminal page without `nextCursor`; omit `cursor`, since this server issues none. Invalid nested capability declarations and supplied cursors return `-32602` before dispatch. Full modern conformance remains under review.

When audit is enabled, configure database-page allowance with `audit_max_db_bytes` (default 64 MiB) and WAL checkpoint pressure with `audit_wal_checkpoint_bytes` (default 4 MiB). `AUDIT_WAL_CAPACITY` means long-lived audit readers must release the WAL before further writes; database growth failures return `AUDIT_UNAVAILABLE`. These preserve prior records, but policy state may already have changed. The WAL value is a high-water admission threshold, not an exact disk quota. Do not delete active rows or blindly replay stateful calls; follow `docs/AUDIT_STORAGE_LIMITS.md` for reviewed limits, verified backup and recovery.

For modern requests with optional `clientInfo`, use string description/website fields and well-shaped icon objects (string source/MIME, string-array sizes, light/dark theme). Malformed metadata returns `-32602` before dispatch. Identity and URLs are untrusted metadata; Runtime Guard does not fetch/render icons or use client identity to grant permission. URI trust and full modern conformance are not certified.

Omit modern `requestState`: this server issues no resumable state and rejects every supplied value with `-32602` before dispatch. `inputResponses`, if present, must be an object; unknown entries are ignored and cannot grant permission. Do not treat a client-supplied approval/resume blob as authorization or assume exactly-once replay protection. Independent stateful requests can still consume budget; no resume API is implemented.

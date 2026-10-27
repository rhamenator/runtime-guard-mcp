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

For compatible legacy JSON-RPC calls, omit `params` or send an object. Arrays and scalar parameters return `-32602`; tool calls require the documented object fields.

Cursor CLI 2026.10.19-6bbf2c4 has bounded ACP/stdio discovery and safe/blocked inspection evidence. Configure the installed server in project-local `.cursor/mcp.json`, run `agent mcp enable runtime_guard` and `agent mcp list-tools runtime_guard` from that project, and retain normal tool permissions. Existing Cursor authentication is required; account/model service costs are separate. Terminal UI remains unverified. The tested ACP cancel acknowledged interruption but omitted MCP cancellation; use the recovery guidance below.

Legacy MCP clients must initialize with `protocolVersion`, an object `capabilities`, and `clientInfo` containing string `name` and `version`. Correct malformed initialization fields after `-32602` before retrying.

Request parameters and optional `_meta` must be objects. Arrays or malformed metadata return `-32602` before tool dispatch; retry with the documented tool arguments. Modern stdio uses per-request metadata as described below; full release conformance review remains open.

### Modern stdio requests and cancellation

Modern clients may call `server/discover` without initialization, supplying `_meta.io.modelcontextprotocol/protocolVersion` (`2026-07-28`) and `_meta.io.modelcontextprotocol/clientCapabilities` (an object) on every request. Legacy clients retain the initialization workflow above. Modern results include `resultType: complete`. This modern implementation is still undergoing release conformance and client review; use stdio, as HTTP remains legacy.

Cancel a pending stdio request using `notifications/cancelled` with its string or integer `requestId`. Queued work is discarded and replies waiting for output are suppressed; a response frame already being written cannot be retracted; already applied budget/masker/audit changes are not undone, and running policy functions finish. This grants no execution permission. At most 32 requests may be outstanding; error `1001` asks the client to retry after pending work completes. See the README for EOF and output-backpressure limitations.

Modern request IDs must be strings or integers, including requests with unsupported versions; null/float IDs return `-32600`. Optional modern `clientInfo.title` must be a string or the request returns `-32602`. These checks add no permissions.

### Audit capacity

If the separately configured server enables `audit_db`, `audit_max_records` defaults to 100000 (positive integer). `BLOCKED` / `AUDIT_CAPACITY` means the file has reached its committed-record limit; do not run the proposed action or repeatedly retry budget/masking calls. Ask the operator to stop the server, verify and preserve an SQLite backup, retain the final hash externally, and configure a fresh audit file before restarting. Do not delete rows or disable auditing to bypass the decision. The README describes permissions and the tested backup/restart workflow. This setting limits records; separate database-page and WAL admission settings are described below. None supplies an exact total disk quota or automatic rotation, and new files do not automatically anchor previous chains. No new execution permission is granted.

If the server exits with status 2 and `Cannot initialize Runtime Guard`, stop the workflow and ask the operator to check workspace/audit access, competing writers, storage and integrity. Startup has not exposed tools on either transport. Do not delete audit rows to fix it; preserve evidence and use the README repair/retry guidance. Handled startup diagnostics omit raw paths and SQLite details.

Client turn interruption is not proof of MCP cancellation. In the documented instrumented real-client review, Claude sent matching cancellation; Codex/Cursor omitted it in their tested paths. Treat an interrupted turn as potentially completed policy work, inspect actual tool/audit outcomes, and do not assume budget or audit rollback. The optional developer probes require existing client authentication and may consume model usage; they are not installation requirements. See `docs/CLIENT_CANCELLATION.md` in the server repository.

Codex CLI 0.151.0 app-server interruption is acknowledged at the client but does not send MCP cancellation in the tested path. Treat interrupted tool outcomes as unknown; do not automatically replay consuming budget reservations or masking chunks. A fresh read-only advisory call can verify connectivity, not prior cancellation. Restart resets volatile budget/masker state and preserves configured persistent audit records; it is not rollback. No server setting can supply a missing client notification. See the client-specific recovery procedure in `docs/CLIENT_CANCELLATION.md`.

For modern stdio, send object-shaped experimental/extension settings and sampling/elicitation options; extension identifiers need a valid metadata prefix. Declaring a capability does not enable it or grant permissions. `tools/list` returns one terminal page without `nextCursor`; omit `cursor`, since this server issues none. Invalid nested capability declarations and supplied cursors return `-32602` before dispatch. Full modern conformance remains under review.

When audit is enabled, configure database-page allowance with `audit_max_db_bytes` (default 64 MiB) and WAL checkpoint pressure with `audit_wal_checkpoint_bytes` (default 4 MiB). `AUDIT_WAL_CAPACITY` means long-lived audit readers must release the WAL before further writes; database growth failures return `AUDIT_UNAVAILABLE`. These preserve prior records, but policy state may already have changed. The WAL value is a high-water admission threshold, not an exact disk quota. Do not delete active rows or blindly replay stateful calls; follow `docs/AUDIT_STORAGE_LIMITS.md` for reviewed limits, verified backup and recovery.

For modern requests with optional `clientInfo`, use string description/website fields and well-shaped icon objects (string source/MIME, string-array sizes, light/dark theme). Malformed metadata returns `-32602` before dispatch. Identity and URLs are untrusted metadata; Runtime Guard does not fetch/render icons or use client identity to grant permission. URI trust and full modern conformance are not certified.

Omit modern `requestState`: this server issues no resumable state and rejects every supplied value with `-32602` before dispatch. `inputResponses`, if present, must be an object; unknown entries are ignored and cannot grant permission. Do not treat a client-supplied approval/resume blob as authorization or assume exactly-once replay protection. Independent stateful requests can still consume budget; no resume API is implemented.

Send method-bearing requests to stdio. This server issues no outbound RPC requests; recognizable unsolicited result/error responses are ignored, not treated as commands, approvals or responses to your pending calls. A peer response ID cannot complete or cancel an active client request. Malformed requests still return controlled errors. No outbound RPC correlation feature is implied.

Cancellation notifications with malformed metadata are ignored without a reply. Valid cancellation still suppresses replies only; it does not undo policy state or committed audit records.

`secret_masker` keeps at most 128 unfinished streams and 4,096 distinct secret placeholders per caller. On `STREAM_LIMIT`, finish an existing stream with `final=true` before opening another. On `SECRET_STATE_LIMIT`, discard blocked output; existing secrets can still be masked, but more distinct secrets require a fresh server process, which also resets volatile budgets and masker state. Changing session IDs does not bypass the caller-wide secret limit.

Stdio output is bounded to 32 queued frames and 16 MiB of encoded queued/active data. A frame has five seconds to reach the client; EOF also has a five-second output-drain budget after the existing policy drain. Stalled/disconnected output or exceeded buffering ends the CLI session with exit code 2. Discard a partial response and reconnect; an interrupted decision may already have changed budgets, masker state or audit records. Do not automatically replay stateful calls. No rollback or whole-agent enforcement is provided.

Custom clients must use string or integer request IDs. Explicit null, floating-point (including `1.0`), boolean, array and object IDs return `-32600` before policy work in both protocol versions and legacy HTTP. Omit the ID only for a notification, which does not execute tool calls or receive a JSON-RPC reply. This validation is not replay protection or exactly-once execution.

Stdio cancellation also suppresses a completed result still waiting in the output queue. Request IDs and admission slots remain reserved until delivery or cancellation discard. A frame whose pipe write already began cannot be retracted, and cancellation does not undo committed policy/audit effects.

### Invocation throttling

All valid tool calls share a process allowance of 600 calls per fixed minute, independent of tool/session/caller and `budget_guard.consume`. Operators may configure the positive integer `invocations_minute` in server JSON. If `INVOCATION_RATE_LIMIT` blocks a call, wait up to 60 seconds before retrying; ping remains available. Denials do not mutate policy state or write audit rows. Restart resets the allowance, separate processes have separate limits, and HTTP callers share capacity. This is not a distributed or per-user quota.

Trace metadata is not an identity or permission signal. Requests with malformed `traceparent` return generic `-32602` before tool admission or policy/audit work; cancellation notifications with malformed values are ignored. Both stdio versions and legacy HTTP check the W3C lowercase hexadecimal core fields, nonzero IDs, forbidden `ff` version and exact version-00 length. Future versions require a compatible core and a dash before any opaque extension; no future extension is interpreted. Values are not echoed, persisted in audit records or used to generate/forward traces. This is partial trace-context validation: context association and propagation review remain release gates.

Supplied `tracestate` also receives bounded grammar validation before tool work or cancellation. Malformed values return generic `-32602` for requests and are ignored on cancellation notifications. The local cap is 32,768 ASCII characters and 32 comma-separated members (including empty members); keys/values are limited to 256 characters, tenant/system portions to 241/14, and duplicate keys reject. Empty/whitespace members and surrounding space/tab separators are accepted. Metadata values remain opaque, unlogged and unauthoritative; no tracing propagation is added.

Supplied `baggage` now receives wire-format validation before tool/cancellation effects. Local caps are 8,192 ASCII characters and 64 comma-separated members. Keys use HTTP token characters; values/properties support valid percent escapes, empty values, duplicate keys, additional equals signs and optional space/tab separators. Malformed escapes, raw control/non-ASCII characters, empty members/strings or excess limits reject; omit baggage when there is none. Values remain encoded and opaque: no decoding, identity mapping, audit retention or forwarding is performed. Invalid requests return generic `-32602`; invalid cancellation metadata is ignored. Context association/propagation and broader release reviews remain open.

Request metadata is not authenticated identity. Changing clientInfo, trace/baggage or vendor role claims cannot change configured roots, tool permissions or shared quotas. Masking tails continue only with the explicit `session_id`/`stream_id` pair; interleave unrelated work with distinct pairs. Handles, placeholder maps and quotas are process-local: after restart discard unfinished output/handles and replay the full logical stream, with external budget accounting as needed. HTTP callers share one owner's namespace and quota; this server is not multi-tenant. See the repository's request-context review for the documented portability limitation and required human release disposition.

Modern stdio discovery/tool-list results use `ttlMs: 0` and `cacheScope: private`; clients should treat them as immediately stale and keep authorization contexts separate. Cache hints or previously learned tool declarations never grant access to operator-disabled tools. Legacy revisions still use initialize-based grammar; discovery's legacy version entry does not advertise modern metadata for that revision. See the repository's version/cache/cancellation review for tested compatibility and remaining client/cancellation limitations.

Unexpected legacy HTTP server failures return generic JSON-RPC `-32603`; notifications have no JSON-RPC reply. Treat the interrupted tool outcome as unknown and use the documented recovery procedure. Do not automatically replay consuming budgets or masking chunks; prior state changes are not rolled back. HTTP remains legacy JSON-RPC, not Streamable HTTP.

If `audit_path_access` returns `PATH_RESOLUTION_FAILED`, restore path accessibility or remove the symlink loop before retrying. Missing targets may still receive an advisory decision for a proposed new file. A SAFE decision does not prove existence, grant permissions or prevent a later filesystem race.

Read-oriented command names can have side effects. Explicit Git `--output`, find file-output actions and ripgrep `--pre`/`--hostname-bin` options require confirmation. This is conservative text inspection, including option-like quoted operands; configuration, aliases, external helpers and unrecognized syntax can still change effects. Never execute solely because the advisory result is `SAFE`.

Shell background/control characters, input redirection and parentheses also require confirmation, including when quoted as literal operands. This deliberately conservative check covers process-substitution text without evaluating shell syntax. A plain read-oriented command result still cannot account for aliases, configuration or external helpers.

Legacy stdio clients must complete `initialize` followed by `notifications/initialized` before `tools/list` or `tools/call`; otherwise error `1002` requests the handshake. Malformed/early initialization notifications do not unlock tools; a repeated successful legacy initialization returns `-32600` and requires a fresh connection. Ping is available before initialization. Modern per-request metadata remains independent; the custom HTTP endpoint retains its existing JSON-RPC behavior. These checks add no execution permissions or rollback.

Assignment masking also recognizes quoted JSON-style password/api-key/secret/token keys and quoted values (including spaces and escaped characters), bounded to 8–256 matched value units. It operates on text, not a JSON decoder; replacement text need not preserve JSON structure. Short, encoded, unknown or longer formats can remain unmasked. Keep the signature-only limitation and inspect output before sharing it.

Initialization notifications remain silent even when admission is full. A saturated notification may be dropped without advancing legacy state; after capacity clears, resend `notifications/initialized` or reconnect if legacy tools still return `1002`. Quoted assignment masking also handles a final unterminated quote (including an unfinished escape), within the same 8–256 value-unit bound; intermediate stream tails stay buffered until later input or final flush.

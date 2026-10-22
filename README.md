# runtime-guard-mcp

[![CI](https://github.com/rhamenator/runtime-guard-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rhamenator/runtime-guard-mcp/actions/workflows/ci.yml) [![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](LICENSE)

An MCP server for **advisory** runtime safety checks in coding agents. It inspects proposed file paths and shell commands, tracks caller budgets, detects repeated actions, and masks common credentials in output. It never executes shell commands or opens the target files. It is separate from [request-guard-mcp](https://github.com/rhamenator/request-guard-mcp), which handles request classification and is being extended for HTTP egress.

## Run locally

Python 3.11 or newer; CI exercises Python 3.11 through 3.14. The runtime uses only the standard library. See [dependency decisions](docs/dependencies.md) for the packaging and protocol tradeoffs.

```bash
python3 -m pip install --no-build-isolation -e .
RUNTIME_GUARD_WORKSPACE_ROOT="$PWD" runtime-guard-mcp
```

The default transport is MCP over stdio. Keep stdout reserved for JSON-RPC. A client can configure a local stdio server with command `runtime-guard-mcp` and environment variable `RUNTIME_GUARD_WORKSPACE_ROOT` set to the intended workspace.

For a local HTTP endpoint:

```bash
runtime-guard-mcp --transport http --host 127.0.0.1 --port 8765
```

The HTTP endpoint is `/mcp`. It handles JSON-RPC POST requests and returns JSON responses; GET streaming is unsupported. Non-loopback binding requires `RUNTIME_GUARD_AUTH_TOKEN`, and public deployment also needs TLS termination and explicit network controls. The server checks `Origin` and `Host`. HTTP parser and unsupported-method errors return generic JSON without reflecting request data; HEAD error responses have no body. HTTP connections have a five-second total deadline as well as a five-second inactivity timeout; slow legitimate uploads may be disconnected. A fresh installed stdio entry point passed repeatable initialize, list, and call probes with a minimal client and the official Python MCP SDK 2.3.0; see [client interoperability evidence](docs/CLIENT_COMPATIBILITY.md). Claude Code and Codex CLI each completed one local stdio call with explicit tool permission. Cursor CLI 2026.10.19-6bbf2c4 discovered all four tools and completed safe and blocked stdio inspections through ACP; its terminal UI remains unverified; the tested ACP interrupt omitted MCP cancellation (see the cancellation limitation below).

Copy [the config example](runtime-guard.example.json), set `RUNTIME_GUARD_CONFIG` to its path, and adjust budgets using the [config schema](schemas/config.schema.json). Configuration must be UTF-8 JSON without duplicate keys or non-finite numbers, under the same 1 MiB, nesting, and structure limits as requests. Invalid or unreadable files stop startup with a controlled error. `allowed_roots` are operator configured extra roots; no MCP call can change them. `audit_db` enables SQLite decision metadata only (timestamp, hashed caller, tool, status, rule). Startup and integrity verification stream audit rows instead of materializing the table in Python memory. Verification holds the writer lock for the scan; CPU scan time and physical database/WAL bytes are not capped by the record policy below. Audit storage uses a 250 ms SQLite busy timeout per database lock attempt; contention returns `BLOCKED` / `AUDIT_UNAVAILABLE`; retry only after storage is restored. This is not a total request deadline. Use one writer process per audit database. A process-local tip anchor rejects unexpected tail changes while running; detecting tail deletion across restart still requires an external anchor. Leave it null to disable audit persistence. Set `enabled_tools` to hide tools your environment does not need.

## Tools

| Tool | Result | Limit |
| --- | --- | --- |
| `audit_path_access` | `SAFE`, `NEEDS_CONFIRMATION`, or `BLOCKED` for a proposed path | A check cannot prevent later symlink changes or direct file access by other tools |
| `dry_run_command` | Risk tier for shell text | A heuristic parser cannot prove a command safe; it never runs the command |
| `budget_guard` | Caller-wide token, payload, command, and loop budget | Agents must report usage; this does not meter other tools automatically |
| `secret_masker` | Text with stable `[REDACTED_*]` placeholders | Signature based; unknown formats can remain unmasked |

Blocked tool calls return an MCP tool result with `isError: true`, structured JSON, and a text fallback. Protocol errors use JSON-RPC errors. Initialization requires string `protocolVersion`, object `capabilities`, and `clientInfo` with string `name` and `version`; malformed fields return `-32602`. When `params` is present it must be an object; arrays and scalar values return `-32602`. Modern request IDs are checked before metadata/version dispatch, and optional `clientInfo.title` must be a string. Optional request `_meta` must also be an object; extension keys are preserved. This validates the legacy envelope and does not implement 2026 per-request negotiation. Invalid ID types return `-32600` with a null response ID, including malformed request envelopes. Both transports require UTF-8 JSON and return `-32700` for duplicate object keys, non-finite numbers, more than 64 levels of nesting, or more than 8192 structural markers outside strings. [Tool declarations](schemas/tools.json) include input and output schemas.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

See [release quality gates](docs/QUALITY_BAR.md), [contributing](CONTRIBUTING.md), [security reporting](SECURITY.md), [support](SUPPORT.md), [the changelog](CHANGELOG.md), and [architecture and roadmap](docs/architecture.md), [security model](docs/security.md), and the [draft agent skill](skills/runtime-guard/SKILL.md). The skill is for client integration after the user has configured this server; it does not grant permission for tool execution.

## MCP 2026 stdio and cancellation

Stdio accepts MCP `2026-07-28` requests with per-request metadata, alongside legacy `2025-06-18` initialization. Start the server normally; modern clients do not initialize first. Every modern request needs:

```json
{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}
```

`server/discover` reports versions and tools capability. Modern successful replies include `resultType: "complete"` and server information; discovery and tool lists have private, immediately stale cache hints. Unknown versions return `-32022` with supported versions; incomplete metadata returns `-32602`. Capabilities and client identity are not inherited or used as authentication. Modern tool lists sort by name. Legacy tools and SDK initialization remain available.

Cancel an outstanding stdio request with `{"jsonrpc":"2.0","method":"notifications/cancelled","params":{"requestId":1}}`. Queued work is skipped; cancelled in-flight replies are suppressed. Running policy work finishes without forced interruption, and completed budget reservations, masker updates or audit writes are not rolled back. Malformed, unknown and late cancellations are ignored. Legacy initialization cannot be cancelled.

Stdio admits at most 32 outstanding requests, including running work, with one policy worker. Overload returns application error `1001`; retry after outstanding work completes. Cancellation processing does not queue behind policy work. On input EOF, admitted work has up to five seconds to drain before remaining replies are suppressed and the process exits. A client that stops reading output can still stall writes: this is not a complete I/O exhaustion guarantee.

The HTTP endpoint remains legacy JSON-RPC over HTTP and rejects modern metadata with `-32022`; modern HTTP, full conformance, broader modern coding-client validation and sustained resource evidence remain release gates. These changes add no permissions or runtime dependencies. Run `python3 scripts/modern_stdio_smoke.py /path/to/runtime-guard-mcp` against a fresh installation.

The optional official Python SDK probe supports both eras: run `python3 scripts/official_sdk_smoke.py /path/to/runtime-guard-mcp --modern` in the separate `mcp==2.3.0` client environment. Omitting the flag runs legacy initialization. CI runs both against the dependency-free installed server.

For a finite hostile-frame review against a fresh installation, run `python3 scripts/stdio_adversarial_review.py /path/to/runtime-guard-mcp`. It checks seeded malformed frames in both protocol eras and a valid ping after every rejection. It is a bounded regression corpus, not a full fuzzing or conformance claim; see [stdio adversarial evidence](docs/STDIO_ADVERSARIAL_EVIDENCE.md).

## Audit capacity and recovery

When `audit_db` is enabled, `audit_max_records` defaults to **100000**, a positive integer in the config file. After that many committed decisions, audited tools return `BLOCKED` / `AUDIT_CAPACITY` (`isError: true`) and omit their computed result. Existing rows are preserved. The count is atomic within the supported single writer and is reconstructed after restart; restarting cannot bypass the limit. Existing databases above a newly configured limit still verify/open, but cannot append. This is a record-count cap, not a byte quota, time-based retention or automatic rotation policy.

Monitor capacity before it fills: fail-closed behavior trades availability for preserved evidence. Full-capacity rejections cannot themselves be appended. Policy budget/masker state may already have changed, so do not blindly retry those calls. Ping/discovery remain available; changing the configured audit path requires a restart.

To recover, stop the server, verify and back up the complete SQLite database with SQLite's backup API (tested by `scripts/audit_capacity_review.py`). Do not copy only the live main file while WAL writes are active, or delete audit rows to free capacity. Keep the original/backup and an external record of the verified final hash, then configure a fresh `audit_db` path and restart. Each new file starts a new hash chain; cross-file continuity is not automatically anchored or signed. Operators may explicitly raise the configured record limit after reviewing storage capacity. Required filesystem permissions are unchanged; this feature adds no network service or dependency.

Test the fresh-install workflow with `python3 scripts/audit_capacity_review.py /path/to/runtime-guard-mcp`. It checks full-capacity rejection, restart, SQLite backup preservation and fresh-file recovery in legacy and modern stdio.

Audit initialization failures stop before either transport serves requests, with exit status 2 and a generic diagnostic (no database path, SQLite detail or traceback). Check workspace/storage permissions, free space, competing writers and audit integrity. Do not delete records or recreate a damaged file as a shortcut. Startup schema creation and legacy hash backfill are one SQLite write transaction; verification must pass before commit. A failed migration closes the connection and rolls back schema/backfill changes, allowing repair and retry. Startup holds the SQLite write lock during verification; keep one writer per file. Journal-mode setup happens before this transaction and is not undone. Test a fresh installation with `python3 scripts/audit_startup_review.py /path/to/runtime-guard-mcp`.

Real authenticated client interrupt/recovery observations are recorded in [the cancellation review](docs/CLIENT_CANCELLATION.md). Claude delivered MCP cancellation in the tested modern path; Codex/Cursor turn cancellation did not imply MCP cancellation. These instrumented development probes do not add a production feature or execution permission.

Developers on Linux can run `python3 scripts/filesystem_full_review.py /path/to/runtime-guard-mcp` to test real filesystem-full rejection and recovery in a private 2 MiB tmpfs. It requires `unshare`, `mount`, `umount` and permitted rootless user/mount namespaces. Controlled CI runners may use the documented `--mount-only` mode with sudo; production installs need neither privilege nor these tools. This tests temporary tmpfs ENOSPC, not host disk filling or universal storage reliability; see the [security evidence](docs/security.md#isolated-real-filesystem-full-evidence).


### Codex cancellation limitation

Codex CLI 0.151.0 acknowledged `turn/interrupt` and recovered in the same server process, but omitted MCP `notifications/cancelled`. Runtime Guard therefore completes the advisory work and may reply; it cannot infer cancellation or undo budget, masker or audit changes. Do not automatically replay stateful calls after an interrupted turn. See the [client-specific recovery procedure](docs/CLIENT_CANCELLATION.md#codex-limitation-and-recovery-procedure). This is a client-path limitation, not a server setting or whole-agent enforcement guarantee.

### Bounded resource regression review

On Linux, run `python3 scripts/sustained_resource_review.py /path/to/venv/bin/runtime-guard-mcp`. It runs a finite installed-server audit-capacity campaign in both protocol eras, samples RSS/CPU/threads/descriptors/database-plus-WAL sizes and checks fail-closed replies plus recovery pings. It uses only a temporary private audit/config directory, no accounts, VM or external target. CI repeats it on each supported Python version. See [scope and measured evidence](docs/SUSTAINED_RESOURCE_EVIDENCE.md); this is not an indefinite soak or a physical disk quota.

# runtime-guard-mcp

[![CI](https://github.com/rhamenator/runtime-guard-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rhamenator/runtime-guard-mcp/actions/workflows/ci.yml) [![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](LICENSE)

An MCP server for **advisory** runtime safety checks in coding agents. It inspects proposed file paths and shell commands, tracks caller budgets, detects repeated actions, and masks common credentials in output. It never executes shell commands or opens the target files. It is separate from [request-guard-mcp](https://github.com/rhamenator/request-guard-mcp), which handles request classification and is being extended for HTTP egress.

Initial release scope is [single-owner, single-process, Linux-tested and stdio-first](docs/INITIAL_RELEASE_SCOPE.md). Codex/Cursor advisory calls and recovery are tested, but MCP cancellation delivery is unsupported in their documented interrupt paths; consuming calls may still complete. Independent human review has not occurred; it is disclosed rather than required under the current [pre-1.0 release policy](docs/RELEASE-READINESS-REVIEW.md). Owner self-review and all applicable production-quality gates remain required.

## Run locally

Python 3.11 or newer; CI exercises Python 3.11 through 3.14. The runtime uses only the standard library. See [dependency decisions](docs/dependencies.md) for the packaging and protocol tradeoffs.

```bash
python3 -m pip install --no-build-isolation -e .
RUNTIME_GUARD_WORKSPACE_ROOT="$PWD" runtime-guard-mcp
```

For a downloaded, checksum/provenance-verified review wheel, use a dedicated environment:

```bash
python3 -m venv .venv-runtime-guard
.venv-runtime-guard/bin/python -m pip install --no-deps /path/to/reviewed.whl
RUNTIME_GUARD_WORKSPACE_ROOT="$PWD" .venv-runtime-guard/bin/runtime-guard-mcp
# After stopping the MCP client/server:
.venv-runtime-guard/bin/python -m pip uninstall runtime-guard-mcp
```

Use the actual wheel filename. Upgrade with `pip install --no-deps --upgrade /path/to/new-reviewed.whl` through that environment's Python, after stopping the server and preserving user configuration/audit data. Package uninstall removes installed code and the entry point, not owner data outside the environment. See [disposable Linux lifecycle evidence and limits](docs/LINUX_PACKAGE_LIFECYCLE.md). Review wheels are pre-1.0 candidates, not stable releases.

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

Blocked tool calls return an MCP tool result with `isError: true`, structured JSON, and a text fallback. Protocol errors use JSON-RPC errors. Initialization requires string `protocolVersion`, object `capabilities`, and `clientInfo` with string `name` and `version`; malformed fields return `-32602`. When `params` is present it must be an object; arrays and scalar values return `-32602`. Modern request IDs are checked before metadata/version dispatch, and optional `clientInfo.title` must be a string. Optional request `_meta` must also be an object; extension keys are preserved. These envelope checks apply to both eras; modern stdio additionally implements the per-request metadata/discovery workflow below. HTTP remains legacy JSON-RPC. Invalid ID types return `-32600` with a null response ID, including malformed request envelopes. Both transports require UTF-8 JSON and return `-32700` for duplicate object keys, non-finite numbers, more than 64 levels of nesting, or more than 8192 structural markers outside strings. [Tool declarations](schemas/tools.json) include input and output schemas.

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


Modern stdio validates known nested client capability shapes before tool dispatch. Experimental/extension settings and sampling/elicitation options must have the documented object shapes; extension IDs require a valid prefix. Unknown object-shaped custom capabilities are accepted without enabling them or granting permissions. The four-tool list is one terminal page with no `nextCursor`; supplied cursors return non-reflective `-32602` errors. See the [partial modern conformance review](docs/MODERN_CONFORMANCE.md) and installed `scripts/modern_validation_review.py` probe. Full conformance remains a release gate.


### Audit database pages and WAL pressure

When audit is enabled, `audit_max_db_bytes` defaults to 67108864 (64 MiB, integer >=8192, rounded down to database pages). Existing files above the page ceiling refuse startup; growth failures return `AUDIT_UNAVAILABLE` and preserve prior rows. `audit_wal_checkpoint_bytes` defaults to 4194304 (4 MiB, integer >=4096): at/above that WAL high-water mark, a successful truncating checkpoint is required before another write. Pinned readers cause `AUDIT_WAL_CAPACITY` until released. This is a checkpoint/admission threshold, **not an exact physical WAL quota**; the crossing transaction or migration can overshoot it. Keep an OS quota for total filesystem use. See [configuration, recovery and concurrent installed tests](docs/AUDIT_STORAGE_LIMITS.md). Policy state may already have changed before either audit denial; do not automatically replay stateful calls.

Modern optional `clientInfo` now validates description/website strings and icon object shapes (source, MIME type, string sizes and light/dark theme) before dispatch. Metadata is self-reported, never used for authorization, fetched or rendered. This is shape validation, not URI trust or image safety certification; see [the partial conformance review](docs/MODERN_CONFORMANCE.md). Invalid metadata returns non-reflective `-32602` without consuming budget.

Modern Runtime Guard calls never issue `input_required` or resumable `requestState`. Omit `requestState`: any supplied value, including an empty string, returns non-reflective `-32602` before tool dispatch. `inputResponses` must be an object if supplied; unknown entries are ignored without granting permission. This is rejection of unsolicited continuation state, not a resume API or deduplication guarantee. See [the conformance review](docs/MODERN_CONFORMANCE.md).

The [2026-10-22 bounded toolset review](docs/LIVE_ADVERSARIAL_EVIDENCE.md#fresh-installed-toolset-review-2026-10-22) reran Wfuzz and Nmap against a fresh installed artifact, including authentication, malformed RPC, injection-like text, secret masking, saturation and audit fail-closed recovery. Installed Wfuzz targets now exclude inherited source/config overrides. These finite loopback checks do not establish full protocol/client conformance or production readiness.

Stdio distinguishes recognizable peer response envelopes from requests. Since Runtime Guard issues no server-initiated RPC requests, uncorrelated peer results/errors are ignored without a reply, queue admission or policy changes—even if their IDs match active client requests. This avoids replying to replies. Malformed requests still receive controlled errors; legacy HTTP behavior is unchanged. This does not add outbound RPC correlation or full message-pattern certification.

A [paced concurrent resource review](docs/SUSTAINED_RESOURCE_EVIDENCE.md#paced-concurrent-mixed-tool-review-2026-10-22) now exercises 1,536 authenticated budget, masker and command inspections across four workers, then checks capacity denials, thread/descriptor recovery and installed audit restart integrity. Run `python3 scripts/concurrent_resource_review.py /path/to/venv/bin/runtime-guard-mcp` on Linux for this optional developer check. It is a finite eight-second campaign, not a long-duration soak or production-readiness claim.

Cancellation notifications with malformed metadata are ignored without a reply. Valid cancellation still suppresses replies only; it does not undo policy state or committed audit records.

`secret_masker` keeps at most 128 unfinished streams and 4,096 distinct secret placeholders per caller. On `STREAM_LIMIT`, finish an existing stream with `final=true` before opening another. On `SECRET_STATE_LIMIT`, discard blocked output; existing secrets can still be masked, but more distinct secrets require a fresh server process, which also resets volatile budgets and masker state. Changing session IDs does not bypass the caller-wide secret limit.

Installed resource regression commands and measured limits, including the fixed two-minute mixed HTTP replay, are documented in [resource evidence](docs/SUSTAINED_RESOURCE_EVIDENCE.md). These tests do not establish an indefinite soak or latency guarantee.

Stdio output is bounded to 32 queued frames and 16 MiB of encoded queued/active data. A frame has five seconds to reach the client; EOF also has a five-second output-drain budget after the existing policy drain. Stalled/disconnected output or exceeded buffering ends the CLI session with exit code 2. Discard a partial response and reconnect; an interrupted decision may already have changed budgets, masker state or audit records. Do not automatically replay stateful calls. No rollback or whole-agent enforcement is provided.

Advertised tool schemas and actual structured decisions are checked with a separate Draft 2020-12 validator in the test-client environment; see [conformance evidence](docs/MODERN_CONFORMANCE.md). This does not certify complete MCP conformance.

Custom clients must use string or integer request IDs. Explicit null, floating-point (including `1.0`), boolean, array and object IDs return `-32600` before policy work in both protocol versions and legacy HTTP. Omit the ID only for a notification, which does not execute tool calls or receive a JSON-RPC reply. This validation is not replay protection or exactly-once execution.

Stdio cancellation also suppresses a completed result still waiting in the output queue. Request IDs and admission slots remain reserved until delivery or cancellation discard. A frame whose pipe write already began cannot be retracted, and cancellation does not undo committed policy/audit effects.

The [frozen core conformance inventory](docs/CORE_CONFORMANCE_INVENTORY.md) records implemented evidence and concrete open release blockers, including mandatory invocation-rate governance beyond the optional budget tool.

## Actual tool invocation limits

Every valid call to any enabled tool consumes one shared process allowance before policy work, regardless of caller, session, tool name or `consume`. The default is 600 invocations per fixed 60-second window measured with a monotonic clock from server startup. Configure a positive integer `invocations_minute` in the server JSON configuration to tune it; there is no disable value. For example: `{"invocations_minute": 600}`. Both stdio versions and legacy HTTP use this gate. Invalid requests, notifications, discovery and ping do not consume it.

Exhaustion returns `BLOCKED` / `INVOCATION_RATE_LIMIT` with `isError: true` and matching text/structured results. Wait up to 60 seconds before retrying. Rejected invocations do not change policy state or write audit rows, so a rejected flood cannot force SQLite writes; audit history therefore does not count every rate denial. Accepted calls retain normal audit behavior. This constant-memory, lock-protected gate is separate from optional caller-reported `budget_guard` accounting. It is shared across HTTP clients, resets on process restart, and permits a burst on each side of a window boundary. Multiple server processes multiply capacity; it is not distributed or per-user throttling, and protocol parsing/concurrency/output limits still apply.

The developer schema-validation probe accepts only bounded inline Draft 2020-12 schemas and refuses all reference retrieval. Run `scripts/offline_schema_review.py` in the documented isolated test-client environment to exercise its loopback canary and recovery before the installed tool-schema probe. This is a test-client safeguard; it does not restrict network access by your coding agent. See [modern conformance evidence](docs/MODERN_CONFORMANCE.md#offline-schema-client-resolution-boundary).

Trace metadata is not an identity or permission signal. Requests with malformed `traceparent` return generic `-32602` before tool admission or policy/audit work; cancellation notifications with malformed values are ignored. Both stdio versions and legacy HTTP check the W3C lowercase hexadecimal core fields, nonzero IDs, forbidden `ff` version and exact version-00 length. Future versions require a compatible core and a dash before any opaque extension; no future extension is interpreted. Values are not echoed, persisted in audit records or used to generate/forward traces. This is partial trace-context validation: context association and propagation review remain release gates.

Supplied `tracestate` also receives bounded grammar validation before tool work or cancellation. Malformed values return generic `-32602` for requests and are ignored on cancellation notifications. The local cap is 32,768 ASCII characters and 32 comma-separated members (including empty members); keys/values are limited to 256 characters, tenant/system portions to 241/14, and duplicate keys reject. Empty/whitespace members and surrounding space/tab separators are accepted. Metadata values remain opaque, unlogged and unauthoritative; no tracing propagation is added.

Supplied `baggage` now receives wire-format validation before tool/cancellation effects. Local caps are 8,192 ASCII characters and 64 comma-separated members. Keys use HTTP token characters; values/properties support valid percent escapes, empty values, duplicate keys, additional equals signs and optional space/tab separators. Malformed escapes, raw control/non-ASCII characters, empty members/strings or excess limits reject; omit baggage when there is none. Values remain encoded and opaque: no decoding, identity mapping, audit retention or forwarding is performed. Invalid requests return generic `-32602`; invalid cancellation metadata is ignored. Context association/propagation and broader release reviews remain open.

Request metadata is not authenticated identity. Changing clientInfo, trace/baggage or vendor role claims cannot change configured roots, tool permissions or shared quotas. Masking tails continue only with the explicit `session_id`/`stream_id` pair; interleave unrelated work with distinct pairs. Handles, placeholder maps and quotas are process-local: after restart discard unfinished output/handles and replay the full logical stream, with external budget accounting as needed. HTTP callers share one owner's namespace and quota; this server is not multi-tenant. See the repository's request-context review for the documented portability limitation and required human release disposition.

Modern stdio discovery/tool-list results use `ttlMs: 0` and `cacheScope: private`; clients should treat them as immediately stale and keep authorization contexts separate. Cache hints or previously learned tool declarations never grant access to operator-disabled tools. Legacy revisions still use initialize-based grammar; discovery's legacy version entry does not advertise modern metadata for that revision. See the repository's version/cache/cancellation review for tested compatibility and remaining client/cancellation limitations.

For an inspectable draft companion ZIP, run `python scripts/package_draft_skill.py --ref HEAD --output /path/to/new-output`. It packages only approved committed skill/license/notice blobs and writes checksums/provenance; local edits are excluded. The artifact is explicitly marked draft and must not be submitted. Server installation remains separate. See [draft packaging](docs/DRAFT_SKILL_PACKAGE.md) for limits and final review gates.

### Inspect a server wheel

Before installing a locally built candidate, run `python scripts/inspect_wheel.py dist/*.whl` from the development checkout (Python 3.11+). The inspector checks the approved source/metadata member set, GPL license and notice, console entry point, absence of runtime requirements, and every RECORD SHA-256/size. It reads the ZIP without extracting it. CI runs it before fresh-install client probes on each supported Python version. This checks artifact consistency; it does not authenticate the publisher or replace source review, source-archive verification, final client testing or human release approval. No extra installed-server permissions or dependencies are introduced.

CI also builds a source archive from a clean clone of the tested commit, compares packaged source bytes with that commit using `scripts/inspect_sdist.py ARCHIVE --ref COMMIT`, then builds the inspected wheel from that archive. The archive includes development probes, documentation, schemas, configuration example and companion skill so downstream source users can reproduce checks. Git and setuptools/wheel are development build requirements; installed-server runtime requirements remain empty. Backend-generated packaging metadata is excluded from the source-byte comparison and is subject to the separate wheel inspection. Archive checks do not authenticate the Git commit or promise byte-identical compressed archives across build environments.

The source inspector requires tracked development probes, tests, documentation, schemas and skill instructions as regular files; an empty directory cannot satisfy a required file. Noncanonical paths, aliases and links reject before extraction. CI additionally unpacks the inspected, locally built archive with Python's `data` extraction filter and runs its tests from that directory, checking that the packaged test workflow works independently of the checkout. These development checks do not expand the server's permissions.

For a bounded developer resource check on Linux, run `timeout 215s python scripts/concurrent_resource_review.py /path/to/installed/runtime-guard-mcp --successful-writes`. Four workers pace 3,072 audited tool calls over 180 seconds and require every call to succeed, exact persisted record counts, secret-free audit bytes, bounded sampled resources, responsive ping and verified restart. This uses temporary operator configuration and authenticated loopback HTTP; it does not change installed defaults or require a VM. It complements the capacity-denial profiles and does not establish production throughput or hours-long soak stability.

Source builds require setuptools 77.0.3 or newer (development/build time only), matching the SPDX license metadata used by this project. Normal isolated pip builds resolve this automatically. For offline or `--no-build-isolation` builds, install that backend and `wheel` first. CI pins the minimum backend on Python 3.11 and uses its installed backend for the source-archive-to-wheel build, preventing an isolated build from silently masking an incompatible minimum. Installed-server runtime dependencies remain empty.

On POSIX development hosts, `timeout 100s python scripts/audit_kill_review.py /path/to/installed/runtime-guard-mcp` performs eight owned-server SIGKILL/restart cycles under audit-writing loopback traffic. It checks acknowledged decisions survive, SQLite integrity holds and a restarted server verifies the hash chain and appends another decision. It uses temporary files and authenticated loopback servers; it is not a power-loss or exact commit-interruption test and does not restore process-local budgets/masking state.

Audit storage uses SQLite affinity, which alone does not guarantee stored field types. Malformed BLOB/noninteger timestamp fields are treated as integrity failures: affected calls return generic `AUDIT_UNAVAILABLE`, verification reports invalid integrity, and startup refuses the corrupt database without reflecting stored values. Preserve the database for review and restore verified storage before retrying. This protects controlled failure behavior; it does not recover prior volatile budget or masking changes.

Use `python scripts/inspect_wheel.py dist/*.whl --ref COMMIT` from a Git checkout to bind the wheel's five runtime modules plus LICENSE/NOTICE bytes to an immutable source commit. CI requires this comparison before installation. Without `--ref`, inspection still checks internal RECORD consistency and reports source verification as false. Recomputing RECORD after changing a payload cannot satisfy the committed-source comparison. This does not authenticate the Git publisher or compare generated packaging metadata byte for byte.

The `Release artifacts` workflow uploads review packages, not a published GitHub/PyPI release. It builds a real source archive, verifies source bytes, runs the packaged tests, rebuilds/binds the wheel, and runs fresh installed stdio/API probes before upload. The bundle includes source/wheel inspection JSON, the installed API report and verified SHA256SUMS covering packages and reports. These reports identify the tested commit; the accompanying provenance authenticates workflow identity and does not replace the matrix/client gates or human release approval. A manually dispatched run or matching tag must not be treated as stable-release authorization.

Review bundles now include GitHub/Sigstore build provenance, verified against the source commit/ref and signing workflow before upload. See [artifact provenance](docs/ARTIFACT_PROVENANCE.md) for consumer verification and trust limits. Signed branch artifacts remain review material; a signature does not authorize stable release or replace independent human approval. Server runtime dependencies remain empty.

Legacy HTTP now returns a correlated, generic JSON-RPC `-32603` (`Internal error`) if unexpected dispatch/policy failure occurs, matching the stdio error boundary. Valid notifications still receive no JSON-RPC reply; ping and later requests can recover in the same process. An internal error leaves the tool outcome unknown: do not infer rollback or automatically replay consuming budgets/masking chunks. Exception text is not returned. Installed fault-fixture checks run in CI; HTTP remains legacy JSON-RPC, not Streamable HTTP.

Path checks return `BLOCKED` / `PATH_RESOLUTION_FAILED` when filesystem resolution reports a symlink loop, access failure or other resolution error. Unresolved target/exception text is not returned. Missing targets remain valid advisory candidates after resolving their accessible prefix, so checks can describe proposed new files. This does not prove later access will succeed or prevent filesystem races; tools never open the target's contents or grant host permissions.

Read-oriented command names can have side effects. Explicit Git `--output`, find file-output actions and ripgrep `--pre`/`--hostname-bin` options require confirmation. This is conservative text inspection, including option-like quoted operands; configuration, aliases, external helpers and unrecognized syntax can still change effects. Never execute solely because the advisory result is `SAFE`.

Shell background/control characters, input redirection and parentheses also require confirmation, including when quoted as literal operands. This deliberately conservative check covers process-substitution text without evaluating shell syntax. A plain read-oriented command result still cannot account for aliases, configuration or external helpers.

With `inspect_wheel.py --ref COMMIT`, package Name, Version and Requires-Python must also match that commit's `pyproject.toml`. Duplicate/missing identity headers and directory/metadata version conflicts reject. This supplements runtime/license byte binding; it does not validate every generated backend metadata field or replace provenance and human review.

Legacy stdio clients must complete `initialize` followed by `notifications/initialized` before `tools/list` or `tools/call`; otherwise error `1002` requests the handshake. Malformed/early initialization notifications do not unlock tools; a repeated successful legacy initialization returns `-32600` and requires a fresh connection. Ping is available before initialization. Modern per-request metadata remains independent; the custom HTTP endpoint retains its existing JSON-RPC behavior. These checks add no execution permissions or rollback.

Assignment masking also recognizes quoted JSON-style password/api-key/secret/token keys and quoted values (including spaces and escaped characters), bounded to 8–256 matched value units. It operates on text, not a JSON decoder; replacement text need not preserve JSON structure. Short, encoded, unknown or longer formats can remain unmasked. Keep the signature-only limitation and inspect output before sharing it.

Initialization notifications remain silent even when admission is full. A saturated notification may be dropped without advancing legacy state; after capacity clears, resend `notifications/initialized` or reconnect if legacy tools still return `1002`. Quoted assignment masking also handles a final unterminated quote (including an unfinished escape), within the same 8–256 value-unit bound; intermediate stream tails stay buffered until later input or final flush.

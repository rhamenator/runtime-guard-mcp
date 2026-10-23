# Modern stdio conformance review

Status: partial implementation review, not a full conformance certification. Modern HTTP is not advertised; the HTTP endpoint remains legacy JSON-RPC over HTTP.

## Reference snapshot

Reviewed the authoritative [2026-07-28 schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/schema/2026-07-28/schema.ts) on 2026-10-22. Retrieved schema SHA-256: `742750af0bb8c716e7030c4977c992b55d1adc4407e9e66997db5846baedc2cd`. Relevant definitions: `RequestMetaObject`, `ClientCapabilities`, `DiscoverResult`, `PaginatedRequestParams`, `ListToolsResult`, `CallToolResult`. Also reviewed [base messages](https://modelcontextprotocol.io/specification/2026-07-28/basic) and [pagination](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/pagination).

## Reviewed behavior and evidence

| Area | Current behavior | Verification |
| --- | --- | --- |
| Version and request metadata | Modern stdio requires version and per-request capabilities; unsupported versions return supported/requested details; no prior-request capability inheritance | `test_modern_stdio.py`, installed `modern_stdio_smoke.py` |
| Capability shape | Known nested experimental/extension settings must be objects; extension identifiers follow prefixed metadata grammar; sampling context/tools and elicitation form/url must be objects | `test_modern_stdio.py`, installed `modern_validation_review.py` |
| Extension interpretation | Object-shaped custom capabilities/settings remain accepted without enabling a feature or granting permissions | Valid extension fixtures; no extension advertised by discovery |
| Discovery and results | Tools capability, supported versions, complete result envelopes, server identity; private/zero-TTL discovery/list hints | Installed modern smoke and official SDK workflows |
| List ordering/pagination | Deterministic modern ordering; all four tools fit one terminal page, no nextCursor; every supplied cursor is invalid because none is issued, including empty strings | Installed validation: modern/legacy cursor errors and next valid request |
| Invalid request side effects | Nested capability errors precede dispatch and consume no budget; errors omit input markers | Installed validation preserves a full 120-command reservation after eight malformed consuming calls |
| Cancellation | Matching notification skips queued work/suppresses active replies; no forced interruption/rollback; tested client delivery varies | Dispatcher/wire fixtures and `CLIENT_CANCELLATION.md` |

`modern_validation_review.py` sends 20 rejected frames and four successful recovery frames through an installed entry point in one connection, with legacy/modern interleaving. It requires no account, VM, network target or optional package. Run `python3 scripts/modern_validation_review.py /path/to/venv/bin/runtime-guard-mcp`; CI repeats against each supported Python version.

## Remaining review

The table covers selected implemented paths, not every normative clause. Complete request/result/notification schema review (including URI-format semantics and multi-round-trip input fields), message-pattern behavior, unsupported capability/feature handling, transport/backpressure behavior and exact-candidate official-client testing remain open. Optional features are not implemented merely because their capability declarations can be parsed. Do not infer full modern conformance or client cancellation support from this review.


## Optional client implementation metadata

Modern `clientInfo` validates required name/version and optional title, description, website URL string types. Optional icons require object entries with a string source; MIME type, string-array sizes and light/dark theme are checked when supplied. Unknown future fields remain uninterpreted. No URI is fetched/rendered, no identity field authenticates a caller, and no URI-format/trust or image-safety guarantee is added. Legacy initialization behavior is unchanged.

`implementation_metadata_review.py` reuses the installed-frame harness: ten malformed consuming requests return non-reflective errors, then a complete valid metadata declaration can consume the full untouched budget and a legacy ping succeeds. CI repeats the twelve-frame sequence on Python 3.11–3.14. Source reference remains the pinned `Implementation`, `Icons` and `Icon` definitions above. This closes this shape-validation slice, not the full normative gate.

[Installed probe evidence](evidence/implementation-metadata-2026-10-22.json) records the source revision and wheel/probe checksums.


## Unsolicited continuation boundary

Runtime Guard's current tools complete synchronously; no method issues `input_required`, `inputRequests` or `requestState`. Modern requests carrying any `requestState` are rejected with `-32602` before tool dispatch, including empty strings and apparently approved/opaque state. Nothing is decoded as a permission grant or treated as fresh stateful work. A supplied `inputResponses` must be an object; unknown response entries are ignored because this server requested none. No nested response is interpreted or used to authorize an action. Legacy extension handling is unchanged.

This follows the [MRTR state/response boundary](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr): state is untrusted and clients only echo state actually issued by the server; unexpected response information can be ignored. This change does not implement a resumable service, cryptographic state validation, exactly-once behavior or deduplication of independent requests. Complete MRTR/schema and message-pattern review remains open.

The installed `request_state_review.py` reuses the bounded frame harness. It rejects 14 frames (seven unsolicited states, four malformed response containers and state on ping/list/discovery), then accepts a full untouched 120-command reservation with unknown input responses and a legacy recovery ping. Errors and results do not echo the supplied marker. CI repeats the 16-frame review on all supported Python versions.

[Installed continuation-boundary evidence](evidence/request-state-2026-10-22.json) records the source revision and wheel/probe checksums.


## Uncorrelated stdio response boundary

[JSON-RPC response objects](https://www.jsonrpc.org/specification#response_object) are distinct from method-bearing requests. Runtime Guard issues no server-initiated RPC requests, so recognizable peer responses have no pending outbound request to complete. Stdio now ignores those response envelopes before client-request ID tracking or work admission, without replying or interpreting their content. Peer result/error IDs cannot collide with, cancel, or complete an active client request. Error envelopes with null/absent IDs are ignored when their code/message shape is recognizable; malformed requests still receive controlled errors.

A paused dispatcher fixture receives response IDs matching an active client call, then proves the original call and recovery complete exactly once. The installed `peer_response_review.py` sends 200 uncorrelated result/error frames followed by one malformed request and two recovery calls; it expects exactly one request error and successful full-budget/legacy-ping recovery, without reflecting a synthetic marker. CI repeats against all supported Python versions.

This is response-envelope classification, not full validation of result contents or support for server-initiated calls. Any future outbound RPC feature needs explicit correlation rather than reusing client-request IDs. Legacy HTTP remains request-only JSON-RPC; full modern message-pattern/schema/client review stays open.

[Installed peer-response evidence](evidence/peer-response-2026-10-22.json) records the source revision and wheel/probe checksums.

## Cancellation notification metadata boundary

Metadata key grammar and the optional subscription ID type are checked before a cancellation can affect pending work. Invalid notifications receive no reply and cannot suppress a pending reply. Unknown valid extension keys remain accepted; string/integer subscription IDs are shape checks, not authenticated stream identities.

The source-pinned schema remains `271ecc9accafdd9b83a3c869fa67c22953b2af80`, SHA-256 `742750af0bb8c716e7030c4977c992b55d1adc4407e9e66997db5846baedc2cd`, re-fetched 2026-10-22. See [NotificationMetaObject](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/schema/2026-07-28/schema.ts).

`cancellation_metadata_review.py` runs against a fresh installed Python environment with a test-only 300 ms policy pause. Six malformed metadata variants preserve the active reply; a valid extension/subscription notification suppresses it, and both processes recover with ping. Unit tests cover pending-event preservation and valid queued cancellation. CI repeats the installed probe on Python 3.11–3.14. This is not forced preemption, real-client cancellation delivery, or full conformance certification.

## Advertised tool schemas and actual structured decisions

`tool_schema_review.py` validates the running installed server's four input/output schema pairs with `jsonschema==4.26.0`'s Draft 2020-12 engine, then validates sixteen actual structured results per protocol era. The [tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) defaults undeclared schema dialects to 2020-12 and requires structured results to conform to an advertised output schema. The validator's [documented API](https://python-jsonschema.readthedocs.io/en/stable/validate/) supplies schema checks and instance validation; no custom schema interpreter is added to runtime code.

Cases cover all four tools, SAFE/NEEDS_CONFIRMATION/BLOCKED, scalar/object budget remaining values, invalid bounded-budget decisions, one-shot/split secret masking, and audit-capacity errors for each tool. Every result must match its text mirror and isError flag. Four schema-invalid inputs return -32602 without audit writes, unknown tool/method errors remain distinct, exactly twelve decisions persist, the synthetic secret is absent from responses/audit sidecars, and same-process ping recovers. Modern resultType/serverInfo are checked. The skill's stale array-parameter instruction is corrected to match installed behavior.

Run `timeout 40s /path/to/test-client/python scripts/tool_schema_review.py /path/to/server/bin/runtime-guard-mcp` with jsonschema 4.26.0 installed only in the test-client environment. CI runs alongside the official SDK probes on Python 3.12; the server still installs with zero dependencies. [Machine-readable evidence](evidence/tool-schema-2026-10-22.json) records source/wheel/probe identity. This finite fixture set does not prove all policy branches, all MCP normative clauses, URI-format semantics, native clients or independent human review.

## Shared request-ID admission boundary

Both [2025-06-18 base messages](https://modelcontextprotocol.io/specification/2025-06-18/basic) and [2026-07-28 base messages](https://modelcontextprotocol.io/specification/2026-07-28/basic) require string/integer request IDs and exclude null IDs. The shared handler now rejects all explicitly supplied IDs outside strict string/integer types before dispatch, including legacy requests that previously accepted null/finite floats. This avoids stateful tool calls that cannot be tracked by the bounded cancellation dispatcher. Modern validation remains strict; invalid IDs return a generic -32600 with null response ID. Valid negative integers, zero and empty strings remain accepted. Null IDs on error responses are a separate peer-response boundary and remain supported.

`request_id_review.py` sends six invalid consuming requests through installed legacy stdio, modern stdio and authenticated legacy HTTP. A missing-ID tool notification is ignored without consuming budget (HTTP 202, no JSON-RPC reply); a full 120-command reservation then succeeds, followed by valid-ID recovery pings. Each route yields ten responses for eleven inputs, and malformed object markers are absent from errors. CI repeats on Python 3.11–3.14. Direct handler regression checks both protocol eras. This is a compatibility tightening for malformed/custom clients, not ID-history/replay tracking, transport session authentication or full normative conformance.

The authorized Wfuzz loopback corpus also includes null, fractional and integral-float IDs on consuming budget calls. The fresh installed artifact passed this enlarged scanner/direct-response campaign plus 68 adversarial API/stdio checks. [Durable evidence](evidence/request-id-2026-10-22.json) records wheel/probe identity and scanner/resource results. This is not final release-candidate certification.

## Frozen core inventory and queued cancellation

[CORE_CONFORMANCE_INVENTORY.md](CORE_CONFORMANCE_INVENTORY.md) freezes five upstream source pages with hashes, maps applicable server/client/conditional obligations, and identifies concrete open work. In particular, mandatory rate governance for every actual tool invocation is not satisfied by an optional budget tool or concurrent-admission caps; T06 is the next implementation blocker. This is not a full conformance certification.

The review also found that policy completion retired cancellation IDs before queued output was written. IDs/admission slots now stay live until writer completion/discard, and the writer skips canceled frames that have not begun delivery. The installed `queued_cancellation_review.py` blocks a large first frame, proves later policy progress through persistent audit markers, cancels a completed queued budget result, and then drains intact responses 1/3/4/5 with no result 2. The reservation remains consumed and all five audit records survive restart integrity verification. Both eras pass; a pre-fix installed artifact fails this negative control. Existing in-progress frames are not retracted, Python work is not preempted and effects are not rolled back.

## Offline schema-client resolution boundary

The installed-tool schema probe now admits only inline Draft 2020-12 schemas (default or the exact `https://json-schema.org/draft/2020-12/schema` dialect). A stdlib preflight rejects `$ref`, `$dynamicRef` and `$recursiveRef` anywhere in the schema tree, including literal annotation values, and limits traversal to 8,192 values and 64 levels. This intentionally narrow test client also rejects local references; adding reference support requires an explicit offline registry design and new evidence.

After preflight, the validator uses an explicit `referencing.Registry` whose retrieval callback always refuses I/O, following the [documented registry interface](https://python-jsonschema.readthedocs.io/en/stable/referencing/). It never falls back to implicit network retrieval. `offline_schema_review.py` starts an authorized loopback schema canary: the previous default validator fetches it once as a negative control; thirteen hostile nested-reference/dialect fixtures are then rejected, bypassing preflight still fails registry resolution, no guarded HTTP fetch occurs, and inline validation recovers. CI runs this in the isolated test-client environment before validating the real installed server's eight declarations and 32 decisions across both eras.

Run `timeout 15s /path/to/test-client/python scripts/offline_schema_review.py`, then the existing installed `tool_schema_review.py` command. No server runtime dependency or transport is added. This proves a finite client-harness resolution boundary, not operating-system network isolation, native coding-client behavior, or complete MCP conformance. The server still accepts no caller-provided schema. Remaining release gates and human review stay open.

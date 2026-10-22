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

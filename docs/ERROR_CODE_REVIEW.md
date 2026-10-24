# RPC error allocation review

Reviewed 2026-10-24 against runtime source `14c1edd54f35db1fe5d3a01d8c3d0fd3ede28390` (unchanged in documentation baseline `59a99ad`). This is a scoped self-review for inventory B03, not independent release approval.

## Normative basis

The pinned [MCP basic error-code section](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/basic/index.mdx#error-codes) requires integer codes, standard JSON-RPC meanings, and specification-defined meanings in -32020 through -32099. It prohibits allocating new legacy-range codes and emitting retired -32002/-32042. Application allocations should use the integer space outside -32768 through -32000.

## Complete emitted-code allocation inventory

A source search of every `rpc_error` call in `src/runtime_guard_mcp/server.py` finds these seven allocations. No other runtime module constructs RPC error envelopes. This inventory covers allocations and their branch categories; it does not claim every branch has an independent wire test.

| Code | All emitting branch categories | Assessment / existing evidence |
| --- | --- | --- |
| -32700 | Stdio JSON decode failure; HTTP JSON decode failure | Parse error. Existing transport/adversarial fixtures exercise malformed JSON. |
| -32600 | Invalid request ID/envelope; duplicate in-flight ID; oversized stdio request | Invalid request. Request-ID and queued/dispatcher tests cover malformed IDs and duplicate admission. Oversized frames are rejected before policy dispatch. |
| -32601 | Unknown method; initialize used with modern per-request metadata | Method unavailable for the selected protocol. Modern validation and smoke tests cover method discovery boundaries. |
| -32602 | Params/meta types; trace fields; required version/capability metadata; implementation/capabilities/log/progress/meta keys; unsolicited state/input-response shape; legacy initialize fields; cursor; tool name/enabled state/argument names, required fields and types; policy KeyError/TypeError/ValueError | Invalid parameters, including unavailable tools. Existing modern validation, request-context, state, schema and installed adversarial fixtures cover representative families. |
| -32603 | Unexpected stdio worker exception; unexpected HTTP dispatch exception | Generic internal error with correlated readable request ID. Installed `http_error_review.py` proves private exception suppression, notification silence and subsequent recovery for HTTP; dispatcher tests cover stdio. |
| -32022 | Unsupported requested modern version or modern request on legacy HTTP | Specification-defined UnsupportedProtocolVersion only. Carries requested and supported versions; version/cache probes cover transport/version boundaries. |
| 1001 | Stdio request admission capacity exhausted | Application request-capacity error outside the reserved interval. Dispatcher/resource probes cover exhaustion and recovery. This is a peer response, not an SDK-local timeout. |

Policy denials such as AUDIT_UNAVAILABLE, PATH_RESOLUTION_FAILED and INVOCATION_RATE_LIMIT are successful RPC tool-result envelopes with `isError` and structured policy fields. They do not allocate JSON-RPC numeric codes. HTTP authentication, origin, host and framing rejection can use HTTP status responses before RPC dispatch; this table does not reclassify those as RPC errors.

## Findings and limits

No conflicting, retired or newly allocated legacy-range code was found. HeaderMismatch and MissingRequiredClientCapability are not emitted: this server does not implement header-mapped modern HTTP or server-originated capability-dependent input requests. Adding those features requires a fresh requirements review.

B03 allocation review is now recorded for this exact runtime. It remains a self-review: malformed-envelope classification, exhaustive branch coverage, future specification changes and the broader R01 normative review still require disposition in the release packet. No runtime behavior, transport support or signed baseline artifact changed.

# Frozen modern core conformance inventory

Source commit: `271ecc9accafdd9b83a3c869fa67c22953b2af80`, retrieved 2026-10-22. This is a self-review inventory of the current advisory server surface, not independent review or release approval. `OBSERVED` links bounded code/test evidence; `OPEN` is unresolved implementation/review work; `CONDITIONAL` identifies obligations for features not implemented or advertised. Client obligations are separated from server obligations. This inventory does not claim every normative statement in the full specification has been reviewed.

## Frozen sources

| Source | SHA-256 |
| --- | --- |
| [basic](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/basic/index.mdx) | `ce6b16e0b22544bb7efc201b09906b5f3efb6d55a83881766b36b8a71cfbeb95` |
| [stdio](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/basic/transports/stdio.mdx) | `6fd49766c40dc093d1f5993ab584bad0a06cbb496c2d3019c50f8fe3c8171e57` |
| [tools](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/server/tools.mdx) | `ed550806a58eb7744b858fb9f26001aa5e55dac9e2babe88317cc81d9d4c490d` |
| [mrtr](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/basic/patterns/mrtr.mdx) | `a8671eb2a0d292c0dcbae19666ff4fc3d97f294ce8107e9f38259cc5a02a066b` |
| [pagination](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/server/utilities/pagination.mdx) | `c4c7b674ae9ce16c012b5da35559d35768f6b7a508ceb5d2d71393a9f46afd2b` |

## Applicable surface and open decisions

| ID | Source / obligation (paraphrased) | Status / evidence or required work |
| --- | --- | --- |
| B01 | basic: request IDs are non-null strings/integers | OBSERVED: `request_id_review.py`, both stdio eras and legacy HTTP. |
| B02 | basic: correlated result/error envelopes and complete result types | OBSERVED: protocol tests, modern smoke and SDK probes. |
| B03 | basic: integer error codes and reserved-code meanings | OBSERVED: generic errors, version error, seeded stdio corpus; exhaustive branch review remains part of final packet. |
| B04 | basic: no response to notifications | OBSERVED: request-ID and cancellation probes; malformed envelopes are distinct. |
| B05 | basic: per-request version/capabilities, required-field errors | OBSERVED: modern validation, unsupported-version smoke; no capability inheritance. |
| B06 | basic: metadata identifier grammar | OBSERVED: linear key validator and malformed request/notification tests. |
| B07 | basic: application state explicitly referenced; no inferred conversation context | OPEN REVIEW: distinguish process-scoped caller budgets from explicit session/stream handles; do not claim cross-process persistence or per-user identity. |
| B08 | basic: schemas use declared/default supported dialect | OBSERVED for fixed tool schemas: independent Draft 2020-12 client fixture campaign; not a general remote-schema engine. |
| B09 | basic: no automatic external schema-reference fetching | CONDITIONAL on server: no incoming schema API or external refs in declared schemas. OBSERVED in the test client: bounded inline-only preflight plus explicit no-retrieval registry; loopback negative control, thirteen hostile schema rejections, registry refusal and zero guarded HTTP fetches. References (including local ones) and other dialects are deliberately unsupported; not a general schema engine or native-client guarantee. |
| B10 | basic: trace-context value semantics | PARTIAL: traceparent core/version-00 admission and future-prefix compatibility observed in installed three-route rejection/budget recovery and cancellation fixtures. No trace emission/forwarding. Bounded tracestate grammar additionally observed on all three routes and cancellation. Baggage grammar and full propagation obligations remain OPEN; do not claim complete trace-context conformance. |
| S01 | stdio: UTF-8, newline frames, MCP-only stdout | OBSERVED: parser, frame/drain tests, installed transport/SDK probes. Partial frame on failed output requires session discard. |
| S02 | stdio: no server-originated RPC requests | OBSERVED by source: only replies; uncorrelated peer responses ignored. |
| S03 | stdio: cancel work/replies, including waiting output | OBSERVED after queued-output fix: `queued_cancellation_review.py`, active/queued dispatcher tests. A frame already being written is not retracted; policy effects are not rolled back. |
| S04 | stdio: bounded EOF/disconnect shutdown recommendation | OBSERVED: installed backpressure/EOF probes; no native-platform certification. |
| T01 | tools: advertise capability and available tool list | OBSERVED: discover/list SDK probes, configured enabled-tool tests. No prior-request changes to tool visibility. |
| T02 | tools: deterministic ordering recommendation | OBSERVED: modern sorted list; fixed legacy order. |
| T03 | tools: valid schemas, conforming structured results | OBSERVED finite fixtures: `tool_schema_review.py`, all tools/statuses and audit-capacity outcomes. |
| T04 | tools: serialized text compatibility recommendation | OBSERVED: text/structured mirrors checked by SDK/schema/adversarial probes. |
| T05 | tools: validate inputs, access controls, sanitize outputs | OBSERVED within advisory/single-owner scope: schema/argument checks, configured roots/tools, HTTP auth/origin/host, masker/audit fixtures. Final security review must accept residuals; these are not host action permissions. |
| T06 | tools: rate-limit actual invocations | OBSERVED within one process: constant-memory atomic fixed-minute invocation gate covers all tools/callers/transports, independent of optional reported budgets. Unit concurrency/state-isolation and installed legacy/modern real-minute recovery probes; distributed limits and final security acceptance remain outside this evidence. |
| M01 | mrtr: do not send forbidden/undeclared input requests | OBSERVED by source: only complete results; no server input requests. |
| M02 | mrtr: treat resumed state as untrusted | OBSERVED: every unsolicited requestState rejects before dispatch; unknown input responses cannot grant permission. |
| M03 | mrtr: signed state/unique input keys/capability-dependent prompts | CONDITIONAL: no resumable/input_required service. Implement before advertising those features. |
| P01 | pagination: required metadata and invalid-cursor errors | OBSERVED: one terminal list; no continuation issued; supplied cursors reject. |
| P02 | pagination: opaque-cursor client handling | CLIENT: not a server implementation claim; terminal-list tests do not certify all clients. |

## Explicit boundaries and next closure work

Modern Streamable HTTP, subscriptions, roots/sampling/elicitation execution, prompts/resources, embedded resources, icons rendering/fetching and header-mapped tool parameters are not advertised server features. Their conditional requirements are not waived if those features are added. The server accepts self-reported implementation metadata as data, not authenticated identity.

This frozen five-source inventory is not the complete protocol universe. Versioning/compatibility, caching and the full cancellation-pattern page still require a dedicated clause review against this same source revision. Native-client/platform probes, exact-candidate adversarial/build/package evidence, application-state/trust decisions and independent human review remain open. T06 now has bounded implementation evidence; remaining clause review and final acceptance still apply.

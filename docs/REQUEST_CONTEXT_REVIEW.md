# Request context and application state review

Self-review of the advisory single-owner server, 2026-10-23. This is a scoped design disposition and finite evidence, not independent release approval. The [frozen basic protocol](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/271ecc9accafdd9b83a3c869fa67c22953b2af80/docs/specification/2026-07-28/basic/index.mdx#statelessness) separates per-request protocol context from application handles. The server validates modern version/capabilities on every request and never derives them, identity or conversation membership from an earlier request.

## State classification

| State | Reference and scope | Decision / limit |
| --- | --- | --- |
| Protocol version/capabilities/clientInfo | Supplied `_meta` on each modern request | No inheritance; clientInfo, trace metadata and vendor identity claims never select caller, roots or permissions. |
| Unfinished masking tail | Explicit `session_id` and `stream_id`, within the server's caller scope | Requests may interleave; only the same handle pair continues a tail. `final` releases it. IDs are routing handles, not authenticated identities. |
| Masking placeholder namespace | Caller scope shared by explicit masking operations | Stable placeholders across sessions are deliberate. No per-conversation or multi-user secrecy guarantee. |
| Budget/rate governors | Server-instance resource scope; budget session/fingerprint arguments are explicit | Changing sessions, clientInfo, trace values or claimed roles cannot reset quota or grant access. This is resource admission, not inferred conversation context. |
| Audit records/configured roots/tools | Operator configuration, optional persistent SQLite decision metadata | Not client-controlled conversation state; raw trace/identity metadata is not recorded. |
| Active request/cancellation IDs | Explicit JSON-RPC request ID, until delivery/discard | Connection-local outstanding work only; cancellation does not undo committed policy/audit effects. |

`stdio` and `http` caller labels are server-selected scopes, not verified people. HTTP uses the configured bearer boundary for one owner; multiple authenticated callers share the same quota and masking namespace. This is not a multi-tenant service. Request-supplied `clientInfo`, baggage or vendor identity fields cannot change that boundary.

## Local-state exception and release disposition

The protocol recommends related operations should not require connection/process reuse. HTTP related operations work across separate connections to one instance. Application handles and resource quotas here remain in memory in that instance: another process/restart cannot resume an unfinished masking tail or preserve budgets/placeholder mappings. Clients must discard unfinished masking output/handles after restart, restart the complete logical stream and re-establish any external budget accounting. Never treat reconnecting or reusing a session name as proof of persistence.

This is an intentional limitation of the dependency-free single-owner component, not a claim that process identity is conversation identity. Independent human release review must accept this documented departure from the portability recommendation or require explicit portable storage/instance-aware handles before release. No such approval is claimed here.

## Trace association and propagation

Trace metadata is syntactically admitted, then ignored for policy, routing and authorization. It is never used to link conversations or select masking handles. The server makes no downstream tool/HTTP/MCP requests: proposed paths/commands are assessed, not executed. Forwarding obligations become applicable if that surface changes; implement and test propagation/privacy before advertising downstream tracing. This disposition does not certify future trace extension semantics, tracing instrumentation or arbitrary clients.

## Reproducible evidence

Run `python scripts/context_isolation_review.py /path/to/server/bin/runtime-guard-mcp`. The fresh installed legacy/modern stdio and legacy HTTP campaign changes client/capability/trace/vendor claims between operations, checks shared quota and configured-root denial, interleaves two sessions and two stream IDs, finishes a split synthetic secret under changed metadata, checks final-tail release, rejects missing modern capabilities and recovers with ping. CI runs all three routes on Python 3.11–3.14. HTTP uses a fresh connection for each request.

This finite campaign does not prove portable restart semantics, multiple authenticated-user isolation, all metadata combinations or whole-agent enforcement. Remaining normative and exact release-candidate/native-client/adversarial/package evidence and human review stay open.

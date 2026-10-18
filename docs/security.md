# Security model

The server is advisory. A model may ignore a result and use another tool. For hard containment, configure the agent host to make this server the route for relevant operations and apply OS sandbox or policy controls.

The path tool checks a proposed path after `Path.resolve`; it rejects traversal beyond configured roots and sensitive names. It cannot prevent time-of-check/time-of-use races or detect all sensitive filenames. Do not treat its verdict as a capability token.

The command tool never executes. Pattern and `shlex` checks can miss shell language constructs, aliases, environment expansions, and platform-specific syntax. Unknown and compound commands require review. Any `SAFE` result means only that the current heuristics found no listed risk.

Budget counts are caller-reported. The server cannot independently know model token usage or actions made outside it. In memory windows reset on restart, and multiple replicas do not share limits. The optional SQLite database stores only redacted decision metadata in a SHA-256 hash chain. `AuditLog.verify_integrity()` detects altered and deleted interior rows; it cannot prove the last row was not deleted without an external anchor. Configure filesystem permissions and retention externally.

Masking is best effort. It recognizes several credential forms, email addresses, and US Social Security number shapes, but cannot identify every secret or private identifier. Raw secrets are not logged or persisted; the in-memory lookup stores hashes to keep placeholders stable. Buffered raw stream tails are removed when `final=true`; clients should always flush or terminate abandoned streams. The process memory can still contain transient sensitive data, so run it under the user's account and restrict access.

HTTP defaults to loopback. Exposing it beyond loopback requires a bearer token and TLS proxy. The HTTP server limits active handlers to 32, returns 503 when all slots are occupied, and closes sockets after five seconds of inactivity, including incomplete headers or bodies. These are process-level resource bounds, not caller quotas; a client can still consume all slots for short intervals, and the listen backlog and upstream proxy need their own limits. For production, add per-client identity, stronger HTTP transport compatibility checks, and a sandbox around any future active executor.

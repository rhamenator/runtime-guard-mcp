# Runtime Guard release quality bar

Status: acceptance criteria, not a completion claim. Every stable-release gate needs a passing test, reproducible command, or durable review record linked from a release issue.

See the [prioritized release work queue](RELEASE_GATES.md) for current blockers and closure evidence.

## Boundary and correctness

- `audit_path_access`, `dry_run_command`, `budget_guard`, and `secret_masker` return deterministic, bounded, schema-valid decisions. Inputs with malformed types, extreme sizes, invalid Unicode, and conflicting fields produce controlled errors rather than crashes.
- Path checks cover traversal, symlinks, junctions where supported, missing targets, race conditions, and configured roots. Results state that later filesystem operations are not authorized by an advisory check.
- Command checks cover quoting, pipelines, substitutions, encoding, nested interpreters, platform differences, and known bypasses. A `SAFE` result never claims semantic proof. The server never executes a proposed command.
- Budget reservations are atomic per caller and survive or explicitly fail through concurrency, restart, and store failure according to documented policy. Secret masking covers chunk boundaries, high-risk token formats, false positives, and bounded buffer retention. Audit records are redacted, tamper-evident, scoped, and retention-limited.

## Protocol and clients

- Implement the [MCP 2026-07-28 protocol](https://modelcontextprotocol.io/specification/2026-07-28) on each advertised transport, including required per-request `_meta`, deterministic tool ordering, structured results, cancellation, and compatible older-client negotiation where needed. Stdio is the primary transport. Call JSON-RPC-over-HTTP by its accurate name until full Streamable HTTP conformance is proven.
- Probe with an official SDK/Inspector and perform fresh-install smoke tests in supported Codex, Claude Code, and Cursor versions. Give copyable setup, expected first result, permissions, and troubleshooting steps for each.
- Never advertise a resource, prompt, tool, version, or transport that is absent or only partially implemented.

## Security and reliability evidence

- A repeatable adversarial test against the actual exposed MCP transport is the principal production-readiness gate. The release record must include the exact revision and commands, tool versions, bounded targets and traffic, pass/fail evidence, findings and fixes, and remaining limits. Cover authentication and origin boundaries, malformed MCP/JSON-RPC, injection attempts, resource exhaustion, secret exposure, and recovery after failure. Run the automated loopback probe in CI and an authorized pentesting-toolset review before a release candidate. A green unit suite alone does not satisfy this gate.
- Adversarial fixtures and fuzz/property tests cover parsers, schemas, path edges, command syntax, secret formats, caller isolation, budgets, audit integrity, and malformed JSON-RPC. Stress tests show bounded memory, file descriptors, threads, CPU, and disk usage.
- The threat model maps each security claim to a code path and test, identifies bypass routes via other MCP servers and host tools, and records residual risks and false positives. No real secret appears in logs, errors, or audit resources.
- Configuration is schema-validated with safe defaults and clear startup errors. Non-loopback serving requires tested authentication, origin handling, TLS deployment guidance, and abuse limits.

## Product finish

- No third-party runtime dependencies unless a documented security or reliability gap justifies one. CI tests all supported Python versions, builds installable artifacts, runs CodeQL and dependency review, and keeps actions pinned. Releases have checksums, provenance, changelog, GPL-3.0-or-later notice, support and vulnerability reporting, and machine-readable registry metadata when submitted.
- A release candidate passes the repository's human release-readiness review. Only then may documentation call the server production-ready or publish a stable tag.

Outbound Guard remains a separate HTTP egress server. Runtime Guard installs and operates without it or Request Guard.

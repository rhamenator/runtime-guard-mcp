# Prioritized release gates

Reviewed 2026-10-21, base revision `7068ddb`. This is a work queue, not release approval. The authoritative acceptance policy remains [QUALITY_BAR.md](QUALITY_BAR.md).

| Priority | Remaining gate | Evidence required to close |
| --- | --- | --- |
| 1 | MCP 2026-07-28 conformance | Implement version-aware per-request metadata/capability negotiation, result envelopes, discovery ordering, and cancellation; test normative requirements through installed stdio and each advertised transport. Preserve verified older-client negotiation. Stdio now implements initial modern per-request metadata, discovery, result envelopes, and bounded cancellation dispatch while preserving 2025-06-18 clients. Complete normative-schema review and modern real-client evidence remain open; HTTP remains legacy. |
| 2 | Sustained resource bounds and audit retention | Repeatable soak with CPU, RSS, descriptors, threads and disk measurements; explicit storage cap/retention behavior and fail-closed disk failure/recovery. Existing snapshots and handler saturation are bounded evidence only; audit storage currently grows. |
| 3 | Release-candidate client and adversarial evidence | Fresh artifact probes in versioned Codex, Claude Code and Cursor, including cancellation/recovery; rerun authorized Wfuzz/Nmap and adversarial API corpus against that artifact, review findings and residual risks. Existing probes cover earlier revisions and limited workflows. |
| 4 | Distribution and human review | Build/inspect wheel, source archive and companion skill ZIP; verify clean installation, checksums/provenance, changelog and claim-to-test mapping. Link evidence in a release issue and obtain human readiness approval before stable tagging. |

## Current foundation

Main CI and CodeQL passed for `7068ddb`. CI covers Python 3.11–3.14, source and installed adversarial probes, wheel installation without third-party runtime requirements, and an isolated official Python SDK client. The previous PR #32 is merged; only two dependency-update PRs were open at this review.

The HTTP endpoint remains legacy JSON-RPC over HTTP. Full Streamable HTTP support is an additional implementation gate if advertised. Runtime Guard provides advisory decisions; it does not intercept arbitrary host actions.

## Current bounded protocol change

Reject array request parameters and non-object optional `_meta` before dispatch, returning generic `-32602` errors. Regression evidence checks rejected budget requests consume no budget, do not echo the supplied marker, and allow the next valid stdio request. Extension metadata remains accepted; required 2026 metadata semantics and negotiation are still open.

Sources: [2026 specification](https://modelcontextprotocol.io/specification/2026-07-28) and [authoritative schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts). This change retains the advertised 2025 protocol version.

## Version-aware stdio milestone

The next change adds modern stdio discovery and per-request dispatch, deterministic modern tool ordering, result/cache envelopes, unsupported-version diagnostics, and a bounded single-worker dispatcher. Focused tests exercise malformed metadata, legacy interleaving, saturated queue cancellation, skipped queued work, suppressed active replies, ID reuse and recovery. A subprocess fixture delays an advisory function to make in-flight cancellation reproducible; it is test instrumentation, not a production delay feature or an authenticated coding-client probe. The installed modern smoke probe runs in CI on all supported Python versions, and the isolated official Python SDK 2.3.0 runs the advisory workflow in both protocol eras on Python 3.12. It proves wire behavior, not complete modern conformance.

Cancellation does not forcibly stop Python policy work, undo already consumed budgets, erase masker state or roll back committed audit records. Audit growth, retention semantics and storage-failure evidence remain priority 2. Startup/integrity scans now stream rows; see [audit resource evidence](AUDIT_RESOURCE_EVIDENCE.md).

## Audit storage milestone

Real SQLite busy/full fixtures now verify controlled tool errors, unchanged audit counts on failed writes, intact hash chains, and recovery after lock/capacity restoration. The exposed HTTP probe covers contention, no append and recovery on source and installed builds. A 250 ms SQLite busy timeout replaces the default five seconds. Actual filesystem-full behavior, retention/storage caps, total latency and sustained resource evidence remain open; see [security model](security.md#audit-storage-failure-and-recovery).

## Finite stdio corpus milestone

A seeded installed-server campaign now rejects 95 legacy and 109 modern hostile frames, checking recovery after each. It identified/fixed modern ID validation order and optional client title validation. See [evidence](STDIO_ADVERSARIAL_EVIDENCE.md); full schema, cancellation/client and sustained resource gates remain open.

## Audit capacity milestone

Audit now defaults to a 100,000-record limit, configurable as positive `audit_max_records`. At capacity, tools fail closed with `AUDIT_CAPACITY`; records are preserved and the count survives restart. Concurrency, above-cap startup, backup preservation and fresh-file recovery are tested. CI runs the installed workflow in both protocol eras. This is deliberate stop-and-archive retention: byte quotas, automatic rotation, cross-file anchors/signatures, sustained resources and real filesystem-full evidence remain open.

## Audit startup milestone

Startup migrations now commit atomically after verification, with rollback/connection cleanup on failure and non-reflective CLI diagnostics before transport startup. Real trigger failure and repair/retry are tested on source and installed builds. Power-loss/forced-kill, actual filesystem-full and remaining physical-resource gates stay open.

## Real-client cancellation milestone

Fresh-wheel client-control probes with a test-only policy pause now cover Claude (modern, matching cancellation, suppressed reply, recovery) and Cursor (legacy, no MCP cancellation, recovery), each with one server process. Initial Codex recovery omitted MCP cancellation; its added-marker replay was provider-limited and remains inconclusive. See [scope and evidence](CLIENT_CANCELLATION.md). Do not waive Codex/Cursor cancellation delivery or modern-client replay gates from these observations.

## Actual filesystem-full milestone

An installed-server probe now exercises real ENOSPC in a private 2 MiB tmpfs: fail-closed tool response, responsive ping, unchanged prior records and recovery after space restoration, in both protocol eras. CI repeats on every Python matrix version. Physical block-device/inode/power-loss cases and remaining quota/provenance/resource gates stay open.

# Prioritized release gates

Reviewed 2026-10-21, base revision `7068ddb`. This is a work queue, not release approval. The authoritative acceptance policy remains [QUALITY_BAR.md](QUALITY_BAR.md).

| Priority | Remaining gate | Evidence required to close |
| --- | --- | --- |
| 1 | MCP 2026-07-28 conformance | Implement version-aware per-request metadata/capability negotiation, result envelopes, discovery ordering, and cancellation; test normative requirements through installed stdio and each advertised transport. Preserve verified older-client negotiation. Current server advertises 2025-06-18. |
| 2 | Sustained resource bounds and audit retention | Repeatable soak with CPU, RSS, descriptors, threads and disk measurements; explicit storage cap/retention behavior and fail-closed disk failure/recovery. Existing snapshots and handler saturation are bounded evidence only; audit storage currently grows. |
| 3 | Release-candidate client and adversarial evidence | Fresh artifact probes in versioned Codex, Claude Code and Cursor, including cancellation/recovery; rerun authorized Wfuzz/Nmap and adversarial API corpus against that artifact, review findings and residual risks. Existing probes cover earlier revisions and limited workflows. |
| 4 | Distribution and human review | Build/inspect wheel, source archive and companion skill ZIP; verify clean installation, checksums/provenance, changelog and claim-to-test mapping. Link evidence in a release issue and obtain human readiness approval before stable tagging. |

## Current foundation

Main CI and CodeQL passed for `7068ddb`. CI covers Python 3.11–3.14, source and installed adversarial probes, wheel installation without third-party runtime requirements, and an isolated official Python SDK client. The previous PR #32 is merged; only two dependency-update PRs were open at this review.

The HTTP endpoint remains legacy JSON-RPC over HTTP. Full Streamable HTTP support is an additional implementation gate if advertised. Runtime Guard provides advisory decisions; it does not intercept arbitrary host actions.

## Current bounded protocol change

Reject array request parameters and non-object optional `_meta` before dispatch, returning generic `-32602` errors. Regression evidence checks rejected budget requests consume no budget, do not echo the supplied marker, and allow the next valid stdio request. Extension metadata remains accepted; required 2026 metadata semantics and negotiation are still open.

Sources: [2026 specification](https://modelcontextprotocol.io/specification/2026-07-28) and [authoritative schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2026-07-28/schema.ts). This change retains the advertised 2025 protocol version.

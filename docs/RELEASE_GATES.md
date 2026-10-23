# Prioritized release gates

Reviewed 2026-10-21, base revision `7068ddb`. This is a work queue, not release approval. The authoritative acceptance policy remains [QUALITY_BAR.md](QUALITY_BAR.md).

| Priority | Remaining gate | Evidence required to close |
| --- | --- | --- |
| 1 | MCP 2026-07-28 conformance | Implement version-aware per-request metadata/capability negotiation, result envelopes, discovery ordering, and cancellation; test normative requirements through installed stdio and each advertised transport. Preserve verified older-client negotiation. Stdio now implements initial modern per-request metadata, discovery, result envelopes, and bounded cancellation dispatch while preserving 2025-06-18 clients. T06 actual invocation-rate governance now has bounded implementation and installed recovery evidence. Next: complete frozen-source versioning/caching/full-cancellation clause review and application-state/tracing decisions; final modern real-client evidence remains open; HTTP remains legacy. |
| 2 | Sustained resource bounds and audit retention | Repeatable soak with CPU, RSS, descriptors, threads and disk measurements; explicit storage cap/retention behavior and fail-closed disk failure/recovery. A default record cap and actual tmpfs ENOSPC recovery are tested; physical byte/WAL quotas and longer mixed/concurrent load remain open. |
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

Fresh-wheel client-control probes with a test-only policy pause now cover Claude (modern, matching cancellation, suppressed reply, recovery) and Cursor (legacy, no MCP cancellation, recovery), each with one server process. Initial Codex recovery omitted MCP cancellation; its added-marker replay remains inconclusive with an unverified rate-limit indicator. See [scope and evidence](CLIENT_CANCELLATION.md). Do not waive Codex/Cursor cancellation delivery or modern-client replay gates from these observations.

## Actual filesystem-full milestone

An installed-server probe now exercises real ENOSPC in a private 2 MiB tmpfs: fail-closed tool response, responsive ping, unchanged prior records and recovery after space restoration, in both protocol eras. CI repeats on every Python matrix version. Physical block-device/inode/power-loss cases and remaining quota/provenance/resource gates stay open.

A subsequent bounded Codex replay passed with process/protocol markers: one process, legacy MCP, interruption acknowledged, recovery successful, no MCP cancellation notification. The earlier inconclusive run remains in evidence with unknown cause.


## Cancellation boundary and finite resource regression

The Codex CLI 0.151.0 app-server path recovers but omits MCP cancellation. The [client-specific recovery procedure](CLIENT_CANCELLATION.md#codex-limitation-and-recovery-procedure) now documents unknown outcomes, unsafe stateful replay and restart semantics. An unrelated client notification must not cancel valid work; a dispatcher regression test protects that boundary. Actual client notification delivery remains an external compatibility limitation, not a configurable server feature.

A fresh installed server now survives 65,536 audit-capacity denials per protocol era with periodic pings, preserved record counts and sampled CPU/RSS/FD/thread/audit-size regression thresholds. See [resource evidence](SUSTAINED_RESOURCE_EVIDENCE.md). CI repeats this finite campaign; it does not close longer mixed/concurrent-load, physical-byte quota, output-backpressure or provenance gates.


## Modern capability and pagination review

Known nested client capability shapes and prefixed extension identifiers are validated before dispatch; malformed metadata cannot consume budget. The terminal four-tool list rejects all supplied continuation cursors with non-reflective errors. The installed 24-frame validation campaign checks recovery and legacy interleaving in CI. See [review mapping and remaining scope](MODERN_CONFORMANCE.md); this does not certify all modern normative requirements.


## Database-page ceiling and concurrent WAL-pressure recovery

A default 64 MiB SQLite page ceiling and 4 MiB WAL checkpoint/admission threshold now complement the record cap. Actual page-ceiling exhaustion preserves rows; pinned readers deny new writes until reclamation succeeds. Installed loopback tests cover four concurrent denials, responsive ping, controlled startup refusal, then 128 successful concurrent writes after release. See [storage policy and scope](AUDIT_STORAGE_LIMITS.md). Exact physical WAL/total-disk quotas, longer mixed/concurrent soaks, power-loss and cross-file provenance remain open.


## Optional modern client metadata validation

Optional client description/website/icon metadata is shape-validated before dispatch. Ten malformed consuming requests, full-budget recovery and legacy interleaving are tested against an installed build, reusing the existing frame harness. Identity/URLs remain untrusted and are neither fetched nor rendered; URI-format/trust and remaining normative/message-pattern review stay open. See `MODERN_CONFORMANCE.md`.


## Unsolicited modern continuation state

Modern requests reject all supplied requestState values before dispatch because the server issues none. Malformed inputResponses containers are rejected; unknown response entries are ignored without granting permission. Installed rejection/budget-preservation/recovery tests run in CI. This closes a fail-closed continuation boundary, not full MRTR, idempotency or modern conformance; see `MODERN_CONFORMANCE.md`.


## Refreshed installed adversarial toolset evidence

Wfuzz 3.1.0 and Nmap 7.98 were rerun against a fresh installed artifact of `2b8c1be`, with 18 scanner requests and 68 API checks. A harness source-shadow isolation defect was fixed and regression-tested. Scope, measured snapshots and limitations are recorded in `LIVE_ADVERSARIAL_EVIDENCE.md`; final exact-candidate/client/TLS/long-load/package and human-review gates remain open.


## Stdio peer response classification

Uncorrelated response envelopes no longer become invalid-request replies or collide with pending client-request IDs. They are ignored before admission because this server issues no outbound RPCs. Active-ID collision and a 200-response installed campaign verify no policy work, no feedback replies and successful recovery. This is a bounded message-pattern fix, not full result-schema validation, outbound RPC support or conformance certification.


## Finite concurrent mixed-tool resource evidence

An installed four-worker, eight-second campaign now covers 1,536 budget/masker/command requests, atomic shared-budget enforcement, audit-capacity denials, secret non-exposure, sampled resources and successful post-load/restart-integrity pings. CI runs the extra paced test on Python 3.12. See `SUSTAINED_RESOURCE_EVIDENCE.md`; longer soaks, many callers/secret churn, broader workloads and physical quota guarantees remain open.

## Cancellation metadata validation

Malformed cancellation notification metadata cannot suppress pending replies. Installed reader/worker tests cover rejection, valid extension cancellation and ping recovery; see MODERN_CONFORMANCE.md. Full normative review and the remaining resource, exact-candidate and human-review gates remain open.

## Installed secret-map and unfinished-stream saturation

A fresh installed artifact now fills the production 4,096-secret map and 128 unfinished-stream limits in both stdio eras. Repeated fail-closed denials, stable existing placeholders, released-slot reuse, complete stream flush, resources and ping recovery are checked in CI. See SUSTAINED_RESOURCE_EVIDENCE.md. Longer soak, multiple callers, output backpressure and the remaining release gates remain open.

## Extended concurrent replay

A fixed two-minute, 24,576-call installed HTTP profile now repeats the mixed workload and fail-closed audit-capacity path, with sampled resource budgets, post-load ping and restart verification. CI runs both short and extended profiles on Python 3.12. See SUSTAINED_RESOURCE_EVIDENCE.md. This adds duration evidence without closing hours-long soak, output backpressure, exact physical storage or final release review.

## Bounded stdio output backpressure

Queued output has frame/byte limits and delivery/drain deadlines. Real installed pipe tests cover stalled and disconnected readers with stdin held open, plus resumed reading and ping recovery in both eras. See OUTPUT_BACKPRESSURE.md. Native-platform/real-client slow-reader and longer-soak coverage remain open; this does not waive final candidate/human review.

## Installed tool schema/result validation

An isolated Draft 2020-12 validator now checks the installed tool schema pairs and sixteen real structured decisions per protocol era, including all four audit-capacity error results and all three advisory statuses. CI runs this alongside the official SDK probes without adding server dependencies. See MODERN_CONFORMANCE.md; remaining normative and exact-candidate/human-review gates stay open.

## Common request-ID validation

The handler now rejects null/float and other invalid explicit request IDs before policy work across both stdio eras and legacy HTTP. Installed tests prove budget preservation, notification silence and valid-ID recovery on all three routes. See MODERN_CONFORMANCE.md. Full normative review, final candidate evidence and human release approval remain open.

## Core inventory exposes concrete MUST-level work

See CORE_CONFORMANCE_INVENTORY.md for frozen source hashes, observed/conditional/open obligations and explicit exclusions. Immediate next implementation priority T06 is bounded governance of actual tool invocations over time; optional caller-reported budget checks and concurrency caps do not satisfy it. The queued-output cancellation defect found during review is fixed and tested against installed persistent-audit pipe fixtures. Remaining versioning/caching/full-cancellation clause review and final candidate/human gates stay open.

## Process-wide invocation admission

T06 now has a constant-memory atomic fixed-minute governor before all tool policy dispatch. See README actual invocation limits for defaults, configuration, audit-denial omission and process/burst limitations. Unit races and installed two-era real-minute recovery cover bounded admission and unchanged budget state on denial. Resource saturation probes explicitly raise this allowance to isolate their existing audit/masker capacity targets. Remaining frozen-source clause review (versioning, caching, full cancellation), application-state/trust decisions, broader/native-client and final exact-candidate adversarial/package evidence, and independent human release review remain open.

## Offline schema-client boundary

B09 now has explicit no-retrieval client-harness evidence: bounded inline-only schema admission, an explicit refusing registry, an authorized loopback negative control, thirteen rejected hostile schemas and inline recovery. The real installed schema/result probe uses this constructor. See MODERN_CONFORMANCE.md for commands, scope and deliberately unsupported references/dialects. Versioning/caching/full-cancellation clause review, application-state/tracing decisions, final candidate/client/adversarial/package evidence and independent human release approval remain open.

## Traceparent admission

Malformed traceparent values now reject before policy/admission on all request routes and cannot cancel active stdio replies. Installed three-route budget preservation/recovery and reader/worker cancellation fixtures cover this bounded milestone. B10 remains partial: finish tracestate/baggage grammar and propagation review; no tracing or authentication claim is added. See MODERN_CONFORMANCE.md. Remaining versioning/caching/full-cancellation review, application-state decisions and exact candidate/client/adversarial/package/human-review gates stay open.

## Tracestate admission

Bounded tracestate grammar now rejects before policy/cancellation effects, with installed three-route rejection, budget preservation/recovery, boundary and cancellation fixtures. B10 remains partial: baggage grammar and context association/propagation disposition stay open. See MODERN_CONFORMANCE.md. Versioning/caching/full-cancellation clause review, application-state decisions, final candidate/client/adversarial/package evidence and independent human review remain required.

## Baggage wire admission

Bounded baggage wire grammar now rejects malformed input before policy/cancellation effects, with installed three-route preservation/recovery and combined-context cancellation fixtures. Metadata stays encoded/opaque, with no decoding, identity authority or forwarding. B10 still needs context association/propagation disposition; broader versioning/caching/full-cancellation review, application-state decisions and exact candidate/client/adversarial/package/human-review gates remain open. See MODERN_CONFORMANCE.md.

## Explicit request-context disposition

REQUEST_CONTEXT_REVIEW.md now maps protocol context, masking handles, caller-wide resource admission and persistent operator state to their actual scopes. Installed three-route metadata-spoofing/interleaving fixtures verify the boundary; no runtime behavior changes. Process-local portability remains a documented recommendation departure for human release disposition. Trace association grants no identity and downstream propagation is conditional on future forwarding. Next technical priority is the frozen versioning/caching/full-cancellation clause review, followed by exact candidate/client/adversarial/resource/package evidence and human review.

## Frozen version/cache/cancellation review

VERSION_CACHE_CANCELLATION_REVIEW.md maps the four newly frozen sources to current server, client and conditional obligations. Installed full/filtered configurations verify version recovery, discovery, private zero-TTL cache hints, extension core fallback and disabled-tool denial across legacy/modern interleaving. Cancellation nonpreemption/reason-logging and process-state portability recommendation limits remain for human disposition. This closes the previously missing scoped page review, not full protocol/native-client certification. Next: final candidate/client/adversarial/resource/package/provenance evidence and independent human review, with residual normative/schema gaps explicitly reviewed.

## Deterministic draft companion package

DRAFT_SKILL_PACKAGE.md documents an allowlisted immutable-Git-source ZIP builder, injected draft warning, content inspection, external checksums/provenance and reproducibility comparisons. Dirty/untracked source contamination and overwrite regressions are tested. CI pairs draft inspection with fresh installed-server client/API probes. This is not marketplace submission or stable readiness: final source-archive/wheel, native-client/adversarial/package claims and human release approval remain required.

## Wheel inspection (2026-10-23)

The CI-built wheel now has a bounded, non-extracting standard-library inspector (`scripts/inspect_wheel.py`). It rejects unexpected/missing/duplicate members, nonregular/encrypted/oversized entries, runtime dependencies, incorrect license/entry-point metadata and RECORD integrity failures. Regression fixtures include traversal-style extra files, omitted notice, injected dependency and modified source bytes. Inspection precedes the existing installed-client/API tests on Python 3.11–3.14. This is consistency evidence, not authenticated provenance. Clean source-archive reconstruction, exact-candidate native-client/adversarial evidence and independent human review remain open; no stable release or submission is authorized by this check.

## Source archive round trip (2026-10-23)

CI now starts packaging in a clean clone at the tested commit, builds the source archive, checks regular source-file bytes against Git without extracting the archive, and builds the installed/probed wheel from that archive. The explicit manifest carries the development probes, documentation, schemas, example configuration and skill. Unknown or modified source files, unsafe paths, duplicate roots/members and oversized/nonregular members reject. Required runtime modules and installation/probe materials must be present. Backend-generated PKG-INFO, setup.cfg and egg-info are exempt from Git-byte comparisons; the resulting wheel still undergoes the separate metadata/RECORD check. This closes a missing pipeline path, not the exact final release candidate or publisher-authentication gate. Native-client/adversarial final-candidate verification and independent human review remain required.

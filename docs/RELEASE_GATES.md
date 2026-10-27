# Prioritized release gates

Reviewed 2026-10-23 against `bd56eca`. This current queue supersedes stale “next” items in the historical milestones below. It is not release approval; [QUALITY_BAR.md](QUALITY_BAR.md) remains authoritative.

| Priority | Remaining gate | Evidence required to close |
| --- | --- | --- |
| 1 | Modern protocol and native-client acceptance | Nine frozen-source pages now have scoped reviews; version/context/cache/cancellation probes pass. Finish independent disposition of remaining normative/schema coverage and process-local state portability/nonpreemption departures. A fresh inspected `cd2dd7d` artifact now has versioned Codex/Claude/Cursor control-path cancellation/recovery replay; only Claude has modern cancellation-delivery evidence. Bind the eventual designated candidate and complete native UI/all-tool/platform coverage or explicitly accept scope limits. Codex/Cursor tested paths recover but omit cancellation. HTTP remains legacy. |
| 2 | Resource and storage acceptance | Byte/WAL admission caps, output backpressure, actual tmpfs ENOSPC, concurrent load and a two-minute mixed replay are implemented/tested. A three-minute all-successful audited-write profile now complements the capacity-denial replay. Longer agreed soak and deployment/native-platform acceptance remain; review physical-disk/inode/power-loss and externally anchored audit limitations. No exact total-disk quota or automatic retention rotation is claimed. |
| 3 | Exact candidate adversarial evidence | The installed source-to-wheel artifact at `bd56eca` now has fresh bounded Wfuzz/Nmap/API evidence (see below). Bind the eventual designated candidate and its native-client/resource/package evidence to immutable artifacts, review findings and explicitly accept residual risk. A finite loopback corpus does not certify all attacks or deployments. |
| 4 | Final distribution and human approval | Source/wheel inspection and round-trip tests plus deterministic draft skill ZIP checks now run in CI. Assemble final checksums/provenance, changelog and claim-to-test mapping for the designated candidate; obtain independent human readiness approval before stable tagging or skill submission. Generated backend metadata, unsigned provenance and draft packaging limitations remain explicit. |

For the latest immutable source, signed artifacts, fresh scanner/native-client replay and open human decisions, use [the current review baseline](CURRENT_REVIEW_BASELINE.md). Historical milestone identities below are retained.

## Separate-model review follow-up, 2026-10-27

Owner-accepted scope is in INITIAL_RELEASE_SCOPE.md. The separate requested Daybreak Blue/xhigh report is in reviews/DAYBREAK_BLUE_2026-10-27.md; it recommends no stable release yet. Next technical priorities: (1) validate and enforce the legacy stdio initialization admission boundary with state-preservation/modern-interleaving evidence; the cited lifecycle includes client obligations, so do not call this an authentication bypass, (2) decide and test explicit quoted JSON assignment masking coverage, then (3) refresh exact-candidate affected protocol/client/artifact evidence. The reported README contradiction is corrected in this documentation change. Model findings and source checks do not satisfy independent qualified human approval. Initial scope acceptance does not waive workload/retention sizing or all residual-risk dispositions.

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

## Source archive adversarial admission and self-contained tests (2026-10-23)

Follow-up artifact review found that the first source inspector counted directories as satisfying required source-file names. It now counts only regular files, requires every tracked Python probe/test and packaged documentation/schema/skill file, and rejects noncanonical path aliases. New adversarial fixtures cover directory substitution, omitted downstream materials, traversal/absolute paths, duplicate paths, multiple roots, symlinks and hardlinks. CI runs the suite from the inspected/unpacked archive as well as the checkout before rebuilding/installing its wheel. No runtime behavior changes; source consistency remains distinct from authenticated provenance and final candidate/human review.

## Installed scanner replay, 2026-10-23

[Recorded evidence](evidence/installed-scanner-replay-2026-10-23.json) binds the clean committed-source archive, rebuilt wheel, probe digests, versions, actual measurements and limits for `bd56eca`. Wfuzz and the API/Nmap corpus passed against fresh installed entry points on owned ephemeral loopback targets. Authentication/origin/host/framing, malformed RPC, injection, secret redaction, resource exhaustion, audit tamper/fail-closed and recovery checks passed. This refreshes principal adversarial evidence after packaging changes; it does not close final native-client, long-soak, normative risk disposition or human release gates.

## Successful-write concurrency milestone

A paced 180-second four-worker profile requires all 3,072 tool decisions to succeed and persist, exact budget/result counts, secret-free audit bytes, sampled resource bounds and post-load/restart integrity recovery. It passes locally and runs in the Python 3.12 installed CI job. See [scope, commands and measurements](SUSTAINED_RESOURCE_EVIDENCE.md#successful-audited-write-profile-2026-10-23). This addresses the earlier denial-heavy workload gap; hours-long/deployment acceptance, final native-client and human review remain open.

## Refreshed native-client cancellation/recovery evidence

All three authenticated CLI/control probes completed against a fresh inspected source-to-wheel installation at `cd2dd7d`, without retry. Claude delivered matching modern cancellation and suppressed the interrupted response; Codex and Cursor recovered but again omitted legacy MCP cancellation. The [artifact-bound observations](CLIENT_CANCELLATION.md#fresh-source-to-wheel-replay-2026-10-23) preserve that distinction. This reduces stale-client-evidence risk but does not waive those compatibility limitations, native UI/all-tool coverage, final candidate designation or independent human approval.

## Minimum build-backend compatibility

A negative control with the formerly declared setuptools 68.0.0 floor fails to parse the project's SPDX string `project.license`; the tested 77.0.3 backend builds a wheel that passes license/notice/RECORD inspection and fresh installed stdio smoke. The declared build floor is now 77.0.3. Python 3.11 CI pins that exact backend and source-to-wheel building disables a second implicit build environment so the minimum is actually exercised; other Python versions use a current compatible backend. This fixes build metadata compatibility without adding runtime dependencies. Final provenance, native/platform scope and independent human review remain open.

## Forced-process audit recovery

Eight installed-server SIGKILL cycles under audited request traffic now check acknowledged-write retention, SQLite integrity, startup hash verification and successful subsequent audit append. The campaign runs in all supported Python CI jobs. See [scope and limits](AUDIT_RESOURCE_EVIDENCE.md#forced-process-termination-during-write-traffic). This addresses the prior missing forced-kill evidence; exact commit interruption, physical power-loss/inode/storage failure and volatile application-state recovery remain explicitly unproven.

## Stored audit-field corruption fix

SQLite BLOB corruption formerly escaped as a serialization TypeError. Hash input types now fail through the controlled integrity/rollback path; verification and startup reject malformed rows. Five-field corruption/repair, restart and atomic legacy-migration regression fixtures plus installed HTTP/stdio refusal/recovery evidence cover the change. No stronger continuous-chain or policy rollback claim is made. Final candidate scope, protocol risk disposition and independent human approval remain open.

## Wheel payload-to-source binding

The wheel inspector now optionally resolves a Git commit once and compares every packaged runtime module plus license/notice bytes to committed blobs. CI requires this mode for all supported Python versions. Regression fixtures alter module/notice bytes and recompute a fully consistent RECORD: standalone consistency inspection passes, committed-source binding rejects. The result records whether source comparison occurred and the resolved commit. This connects inspected source-to-wheel payload identity; it is not signed publisher provenance or generated-metadata reproduction. Final candidate acceptance and independent human release approval remain open.

## Review-artifact workflow alignment

The tag/manual artifact workflow now builds and inspects an actual source archive, tests its unpacked contents, rebuilds/binds the wheel to the workflow commit, and runs fresh installed stdio/API checks. Only then does it checksum packages plus machine-readable inspection/API reports and upload the review bundle. This replaces an unverified wheel plus `pip download .` path that did not establish the required source-distribution round trip. It does not publish a GitHub/PyPI release, enforce human approval or supply signed attestations. Those release acceptance/provenance gates stay open; no tag or manual release run is created by this change.

## Signed review provenance

The review-artifact workflow now signs the wheel/source/report subjects with pinned GitHub Actions provenance and verifies repository, workflow, source commit/ref and hosted-runner identity before upload. The public Sigstore/GitHub trust model and consumer verification commands are documented in ARTIFACT_PROVENANCE.md. This supplies workflow identity evidence, not source correctness, reproducibility, human acceptance or stable-release authorization. Branch-only verification and downloaded-bundle positive/negative controls are required before merging this milestone.

## Local provenance verification resolution

The prior local verifier failure was reproduced as a static Go CLI direct-DNS timeout, despite working native host resolution. A temporary, two-host-only loopback CONNECT relay selected per invocation preserved end-to-end TLS and default trust roots. All five signed review subjects then verified locally and all four negative controls rejected. ARTIFACT_PROVENANCE.md documents the diagnosed scope and evidence; no global resolver/cache setting or server behavior changed. This closes that bundle's unexplained local verification observation, not general network portability, offline verification or independent human release approval.

## HTTP unexpected-error recovery

An installed fault fixture reproduced a connection close instead of a JSON-RPC result when legacy HTTP policy dispatch raised unexpectedly. The HTTP boundary now uses a generic correlated -32603 response, suppresses notification replies and permits ping/tool recovery; private exception text is not reflected. CI runs the fixture against installed packages on all four Python versions. This closes the HTTP/stdio internal-error parity gap; it does not promise rollback or modern HTTP conformance. Final candidate and independent human review remain open.

## Path-resolution fail-closed consistency

Real loop fixtures reproduced SAFE decisions on non-strict resolution in newer Python and exceptions in older/error paths. Path policy now attempts strict resolution, falls back only for absent targets, and blocks reported resolution faults generically. Candidate/configured-root loop, injected permission/OS/runtime fault and missing-target recovery tests cover the change; installed POSIX API checks require blocked loop/no marker reflection and a subsequent valid new-file advisory decision. Native Windows junction and race/slow-filesystem limitations remain open; this does not authorize actual file access.

## Assembled technical review baseline

REVIEW_BASELINE_2026-10-24.md binds source `14c1edd`, its passing matrix CI and a newly built signed main-ref review bundle to fresh local signature controls, Wfuzz/Nmap/API and all three native-client control observations on the same downloaded wheel. It maps implementation claims to evidence and enumerates unaccepted normative/state/client/platform/soak/distribution/human decisions. This is a concrete review packet, not stable release approval; reviewer identity and all R01–R07 dispositions are pending. Runtime changes after the baseline require affected evidence to be refreshed.

## RPC error allocation review

ERROR_CODE_REVIEW.md records every emitted numeric allocation and its branch categories against the immutable runtime baseline. All seven use standard/specification-defined meanings or the application integer space; no retired or newly allocated legacy-range code was found. B03 now has a concrete allocation review. This documentation adds no runtime behavior and does not close exhaustive branch coverage, R01 normative acceptance or independent human review.

## Explicit command side-effect options

Inspection found SAFE classifications for explicit Git file output, find file-output actions and ripgrep subprocess options. These now require confirmation; benign plain-command controls remain advisory SAFE. Unit text fixtures and installed API checks cover the regression without executing submitted commands. This does not solve shell semantics, configuration-dependent helpers or whole-agent enforcement. Runtime changes invalidate the earlier immutable review baseline for affected claims; a new candidate replay is required before release.

## Signed command-option fix refresh

COMMAND_OPTION_REVIEW_REFRESH.md binds PR #104 runtime source 825ca1b to successful main CI, a new signed main-ref review build, local signature negative controls and fresh downloaded-wheel API/scanner/stdio checks. It closes the stale artifact evidence for the affected explicit-option claim. Earlier native-client observations remain tied to the earlier wheel; R01–R07 and final candidate/human acceptance remain open.

## Shell control syntax review

String-only regression fixtures reproduced SAFE results for background command lists and process substitution following read-oriented command names. The conservative compound-command check now additionally requires confirmation for single ampersands, input redirection, parentheses and carriage returns across all three accepted shell labels. Quoted literals can require confirmation as documented. Installed API checks cover background and process-substitution strings without executing either. This changes runtime classification after source 825ca1b; the signed supplement remains historical and affected candidate evidence must be refreshed before release. Shell parsing, configuration-dependent effects and host enforcement remain outside these heuristics.

## Companion instruction consistency review

A bounded R06 review removed stale companion statements that called modern negotiation unfinished, implied all clients require legacy initialization, treated tested Cursor cancellation omission as unobserved, and obscured separate audit storage limits. Cancellation instructions now explicitly exclude an already-writing response frame. These corrections retain draft status, historical client-version evidence and independent release review requirements. Fresh installed legacy/modern smoke and inspected draft ZIP evidence verify the documented workflows; this does not approve marketplace submission or resolve every final claims/platform decision.

## Generated wheel identity metadata binding

The wheel inspector now compares Name, Version and Requires-Python with the exact committed pyproject.toml when --ref is supplied, rejects duplicate/missing identity headers and requires the dist-info directory version to match METADATA. Synthetic wheels with recomputed valid RECORD hashes demonstrate that altered Python requirements or a coherently renamed version can pass consistency-only inspection but fail committed-source identity checks. Runtime/license byte comparison remains separate. This narrows generated metadata uncertainty; it does not validate every backend field, authenticate the publisher or grant independent release approval.

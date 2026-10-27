# Runtime Guard separate-model technical review

**Review date (UTC):** 2026-10-27  
**Documentation/review checkout:** `2241e974e2ce6fbddc867b2cf563f8c9ca40b06c`  
**Signed runtime/source baseline:** `c945f65138dfcc5494cc20bb3055b6aa0838a0f2`  
**Package/version:** `runtime-guard-mcp` 0.1.0  
**Requested execution configuration:** `gpt-daybreak-blue-latest`, `xhigh`

The model and effort above are the configuration supplied in the trusted task-dispatch metadata. This worker has no independent runtime-identity introspection endpoint, so I cannot cryptographically or externally attest that identity from inside the review. I observed no substitute model identifier. This is a separate-model technical assessment, not review by a qualified independent human and not satisfaction of `docs/RELEASE-READINESS-REVIEW.md`.

## Executive assessment

The implementation is unusually explicit about its advisory boundary and has substantial exact-source, installed-artifact, malformed-input, resource, audit, and client-control evidence. Within the owner-accepted single-owner, single-process, Linux-tested, stdio-first scope, I found no critical or high-severity security defect. Authentication/Host/Origin admission for the optional legacy HTTP endpoint, fail-closed audit-result handling, bounded queues/state, and the four tools' non-execution boundary are coherent with the documented limits.

I reproduced one **medium-severity legacy protocol lifecycle defect**: legacy stdio tool calls execute and can mutate budget/masker/audit state before `initialize`, and the server never records the required `notifications/initialized` transition. This contradicts the advertised legacy initialization workflow and the MCP 2025-06-18 lifecycle. I also found one low-severity README contradiction about modern support. A common JSON password assignment is not masked, but because the README expressly says the masker is signature-based and unknown formats can remain, I classify that as a source/coverage concern rather than a breach of a precise completeness guarantee.

**Technical recommendation:** do not designate a stable/release candidate or represent the legacy stdio surface as conformant until the lifecycle defect is fixed and regression-tested, the README contradiction is corrected, and a new exact-candidate affected replay is recorded. After that, the current evidence is a reasonable basis for a qualified human to consider the deliberately narrow initial scope. It is not a basis for public/non-loopback/TLS, Windows/macOS, desktop-control, multi-tenant, distributed-state, rollback, indefinite-retention, or production-workload claims.

## Scope, independence, and method

I reviewed only the detached checkout `/tmp/rg-daybreak-review-20261027`. I did not modify it, the owner's working repository, an existing report, a VM, an external target, or a model account. I did not use subagents, run authenticated native-client probes, run a soak, publish anything, or implement fixes.

I read the required brief and scope plus `AGENTS.md`, the quality bar, release-readiness policy, current and historical review baselines, cancellation guidance, architecture/security/conformance records, source, focused tests, packaging/provenance workflows, draft skill, and machine-readable baseline evidence. I checked the pinned MCP primary material at upstream commit `271ecc9accafdd9b83a3c869fa67c22953b2af80` and the MCP 2025-06-18 lifecycle page.

The five runtime modules in the documentation checkout are byte-identical to the signed baseline. Their SHA-256 values match the baseline packet:

| Runtime module | SHA-256 |
| --- | --- |
| `src/runtime_guard_mcp/__init__.py` | `eb750cd101e5546421dda639405ffb4ccdea9401f0fb184d07a966cad604f67d` |
| `src/runtime_guard_mcp/audit.py` | `756a3c44a4da62af1681afa55ae6769d74a2c683f8fa049060bd6839a217e7ce` |
| `src/runtime_guard_mcp/policy.py` | `aa75d3b1a4954c5b745cfe91bb17141650373c609428086fc99c4c66a2cb8e2a` |
| `src/runtime_guard_mcp/server.py` | `9bb10408bce4508db0053e3343bc46c83353e5129567503d5fee6aa0f1f72305` |
| `src/runtime_guard_mcp/stdio.py` | `81aea4300625a1dd552d6b768d278e55e50bd5ddc70bd58853fbd4fa4883c74f` |

I reused the exact-baseline record of 117 tests, 82 installed API checks, 21 Wfuzz requests, signed source/wheel inspection, and bounded client/resource evidence rather than rerunning the full matrix. I ran two focused, benign local checks for concrete findings: an actual source stdio lifecycle sequence and a synthetic masker-format check. No real secret or target data was used.

## Reproduced findings

### F1 — Legacy stdio executes stateful tool calls before initialization completes

**Severity:** Medium (protocol correctness/conformance; low direct security impact in the accepted trusted-owner stdio model)  
**Confidence:** High  
**Affected code:** `src/runtime_guard_mcp/server.py:335-434`, especially `:341-342`, `:389-399`, and `:409-429`; `src/runtime_guard_mcp/server.py:450-494`

**Failure and impact**

`RuntimeGuard.handle()` treats every no-ID message as a notification and immediately returns at lines 341-342. Consequently `notifications/initialized` is a no-op. Neither `RuntimeGuard` nor `StdioDispatcher` has legacy lifecycle state; `StdioDispatcher.initializations` only prevents cancellation of a currently executing `initialize` request. A legacy request with no modern per-request metadata is therefore dispatched normally before any initialization exchange.

This is observable state mutation, not merely discovery: a first-frame `budget_guard` call with `consume=true` succeeded, then `initialize` succeeded, then another budget reservation succeeded without an intervening `notifications/initialized`. Masker and audit effects are reachable through the same route. Under the accepted scope this does not grant filesystem or command execution and is not an authentication bypass: the stdio peer is already the trusted client process. It does, however, violate the advertised legacy lifecycle, permits malformed/out-of-order clients to consume state before version/capability agreement, and leaves no server-side enforcement of the required transition.

**Focused evidence**

Against the exact checked-out source entry point, I sent three newline-delimited frames in this order:

1. legacy `tools/call` → `budget_guard`, one command, `consume=true`;
2. legacy `initialize` offering `2025-06-18`;
3. legacy `tools/call` → `budget_guard`, 119 commands, `consume=true`;

The process exited 0 with no stderr. Responses were:

```text
id=1 result_rule=WITHIN_BUDGET
id=2 protocolVersion=2025-06-18
id=3 result_rule=WITHIN_BUDGET
```

The first mutation occurred before initialization. The third call also ran without the required initialized notification.

The MCP 2025-06-18 lifecycle states that initialization **MUST** be the first client/server interaction, that the client **MUST** initiate it with `initialize`, and that after a successful response the client **MUST** send `notifications/initialized`: <https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle>. The repository itself tells legacy clients they must initialize (`skills/runtime-guard/SKILL.md:29`) and describes legacy initialization support (`README.md:51-57`), but the current frozen modern inventory does not review or test legacy lifecycle enforcement.

**Remediation**

Track legacy stdio lifecycle independently of modern stateless requests. Before legacy initialization, admit only the protocol-permitted pre-initialization operations (at minimum the `initialize` flow and any deliberately supported ping behavior); reject or defer legacy `tools/list` and `tools/call`. After the initialize response, require a valid `notifications/initialized` transition before normal legacy operation. Preserve modern requests' per-request stateless dispatch and define behavior for duplicate initialize/initialized messages and legacy/modern interleaving. Do not use client-supplied identity as authorization.

Because the optional HTTP endpoint is explicitly non-Streamable legacy JSON-RPC rather than a conforming MCP HTTP transport, either keep this fix specifically scoped to stdio or document an intentional custom HTTP lifecycle separately; do not imply that custom HTTP behavior certifies MCP transport conformance.

**Focused verification plan**

- Add installed stdio negative fixtures proving pre-initialize `tools/list`/`tools/call` cannot mutate invocation, budget, masker, or audit state.
- Prove that `initialize` alone is insufficient and `notifications/initialized` opens legacy operation.
- Test malformed, duplicate, and out-of-order initialization notifications; require controlled non-reflective behavior and recovery.
- Interleave modern requests before/during/after the legacy handshake to prove modern stateless behavior is unaffected.
- Repeat official legacy SDK smoke, modern SDK smoke, native-client affected replay, and the source-bound wheel/API checks on the exact candidate.

### F2 — README simultaneously denies and advertises implemented modern negotiation

**Severity:** Low (documentation/claim accuracy)  
**Confidence:** High  
**Affected documentation:** `README.md:39` versus `README.md:49-65`

**Failure and impact**

Line 39 says: “This validates the legacy envelope and does not implement 2026 per-request negotiation.” Lines 51-57 then accurately state that stdio accepts MCP `2026-07-28` per-request metadata, implements `server/discover`, and emits modern results. The source implements the latter. The earlier sentence is stale or too broadly worded and can cause operators/reviewers to misclassify the advertised surface.

This does not change runtime behavior, but it weakens R01/R06 claim review and can lead a downstream reviewer to omit modern obligations or assume that modern support is absent.

**Remediation**

Rewrite line 39 narrowly, for example: “The legacy envelope checks in this paragraph do not by themselves establish full 2026 conformance; modern stdio support and its limits are described below.” Keep the existing explicit statement that HTTP is not modern Streamable HTTP.

**Focused verification plan**

Run a documentation claim sweep for `modern`, `2026-07-28`, `initialize`, `negotiation`, and `conformance` across README, compatibility docs, draft skill, example configs, and release notes. Cross-check each surviving claim against the source-bound modern and legacy smoke tests.

## Source-only concern, not classified as a confirmed advertised-behavior defect

### S1 — Common quoted JSON password assignments remain unmasked

**Severity if relied upon as complete redaction:** Medium; **classification here:** disclosed limitation / coverage concern  
**Confidence:** High  
**Affected code:** `src/runtime_guard_mcp/policy.py:182-190`, particularly the `PASSWORD_ASSIGNMENT` pattern at line 187; masking logic at `:204-237`

The `PASSWORD_ASSIGNMENT` signature expects `password`, `api_key`, `secret`, or `token` to be followed directly by optional whitespace and `:`/`=`. It does not allow the closing quote in a common serialized form. A synthetic final chunk containing:

```json
{"password":"SyntheticPass123!"}
```

returned `SAFE / MASKED`, `secret_types: []`, and preserved the complete input.

This is material because JSON/config/log output is a likely masker input. I do **not** classify it as a violation of a precise completeness promise: `README.md:37` expressly says masking is signature-based and unknown formats can remain unmasked, and the tool description says “common credentials,” not “all credentials.” No raw input is stored in the audit record. The stream-tail design is otherwise bounded and the existing tests cover split recognized signatures.

**Suggested remediation and verification**

Either add narrowly bounded signatures/tests for quoted JSON/YAML-like keys (while measuring false positives), or publish an exact supported-format inventory and explicitly list serialized-key false negatives. Add whole-chunk and one-character-at-a-time tests for each claimed form, including escaped quotes, upper/lower case, split delimiters, and buffer/state-limit failure. Consider whether the rule name `MASKED` with zero detected types is sufficiently clear to clients; it must not be interpreted as a completeness attestation.

## Areas reviewed without an additional confirmed defect

### Authentication, Host/Origin, and malformed JSON-RPC

The optional HTTP route is accurately described as legacy JSON-RPC over HTTP. Within the accepted loopback/one-owner boundary, the code uses constant-time bearer comparison, rejects duplicate Authorization/Host/Content-Length/Content-Type, rejects transfer encoding, bounds length/handlers/deadlines, checks Host and Origin syntax/allowlists, and keeps parser/error text non-reflective. The baseline evidence includes missing/wrong/near-match/non-ASCII bearer cases, hostile Host/Origin, byte-drip, saturation/recovery, malformed UTF-8/JSON/numbers/nesting/IDs, and audit corruption. I found no additional concrete bypass in that bounded surface. This is not evidence for public deployment, browser CORS semantics, reverse-proxy correctness, TLS, or multi-user identity.

### Path and command advisory tools

Path resolution follows existing symlinks, blocks sensitive resolved components and configured-root escapes, catches loops/resolution faults, and explicitly disclaims authorization and TOCTOU protection. Native Windows junctions and later filesystem races are not certified. The command classifier remains heuristic. Potential helper/config semantics and unrecognized syntax are explicitly disclosed; compound/control syntax is escalated to confirmation, and no submitted command is executed. I did not convert those disclosed limits into whole-agent enforcement requirements.

### Budget, masking, resource, and audit state

Budget accounting and invocation admission are lock-protected and bounded per process; masking has explicit stream/secret caps and conservative tail retention. Caller labels are transport scopes, not user identities. Audit writes use a single-writer lock, record/page/WAL admission, a process-local tip, startup chain verification, and fail-closed result replacement. The important unknown-outcome behavior is accurately documented: budget/masker state can change before an audit denial, cancellation, output loss, or internal error, and is not rolled back. Hash-chain evidence is tamper-evident within its stated limitations, not externally anchored append-only storage. No exact physical disk quota, automatic rotation, cross-file chain, power-loss guarantee, or retention policy is proven.

### Modern stdio and cancellation

The pinned 2026-07-28 primary sources require per-request version/capabilities, `server/discover`, complete result types, and stdio cancellation notification handling. The reviewed code and evidence cover those selected paths, version errors, tool schemas/results, bounded dispatch/output, queued/active reply suppression, and no capability inheritance. Optional prompts/resources/sampling/elicitation/subscriptions/modern HTTP are not advertised and should remain conditional rather than being counted as missing implemented features.

Cancellation delivery remains a client compatibility limitation, not a passing server/client gate: Claude's tested modern path delivered a matching notification; the tested Codex and Cursor legacy control paths did not. Running Python policy work is not forcibly preempted; a frame already being written cannot be retracted; committed effects remain. Those limits are clearly documented and are acceptable only if explicitly retained in the final narrow scope. The cancellation-reason logging recommendation is intentionally declined for data minimization and still needs human disposition.

### Packaging, wheel/source binding, provenance, and draft skill

The packet identifies the signed baseline source, ref, wheel (`c61dcaf4a770674cc50a6f3aabc270e28221603fff1fd347ed40557a0eac7c1d`), source archive, reports, and provenance. The evidence records five positive signature verifications and four wrong-identity/changed-byte rejections. The wheel reports no runtime dependencies, and current runtime bytes match that baseline exactly. Later workflow-pin and documentation commits are not silently substituted for the signed artifact.

The deterministic draft skill builder reads only committed `SKILL.md`, LICENSE, and NOTICE blobs, injects a draft notice, and records hashes. The inspected baseline ZIP has no server binary and no marketplace approval claim. Its client instructions correctly preserve the advisory, cancellation, audit, and execution-permission limitations. It must stay draft until claim review and exact-candidate/human gates are complete.

The artifact is a finite-retention workflow artifact, not a permanent release. Preserve a verified copy and its trust material/record before relying on it. The signed baseline is also not yet a final candidate following this review finding; an affected replay is required after any lifecycle fix.

## Claim/evidence gaps

1. **Legacy lifecycle enforcement:** no current test or conformance inventory item covers pre-initialize and pre-`notifications/initialized` rejection; F1 reproduces the gap.
2. **Full normative/schema review:** the nine-source modern inventory is intentionally partial. URI-format semantics for optional implementation metadata, all message-pattern/schema combinations, future extensions, and exhaustive error branches remain outside certification.
3. **Exact final candidate:** the signed baseline is immutable and runtime-identical to the docs checkout, but no candidate incorporating this review's required lifecycle/doc corrections has source-bound wheel, scanner, SDK, native-client, and provenance evidence.
4. **Native-client scope:** real-client evidence is one delayed command tool through specified CLI/control paths. It does not cover desktop Stop/Escape, all four tools, saturated client queues, later client versions, or modern Codex/Cursor cancellation delivery.
5. **Platform/deployment scope:** Linux Python 3.11-3.14 is evidenced. Windows/macOS/native desktop and public/non-loopback/TLS/reverse-proxy deployments are not certified.
6. **Workload acceptance:** finite eight-second, two/three/ten-minute profiles are useful regressions, not a production throughput/latency/SLA or hours-long soak. The owner has not supplied a production workload envelope for acceptance.
7. **Audit durability/retention:** one-writer SQLite, bounded record/page/WAL behavior, SIGKILL cycles, and temporary ENOSPC are tested. Physical power loss, exact commit interruption, external anchoring, cross-file continuity, retention duration, archival custody, and total filesystem quota remain decisions.
8. **Secret format coverage:** split recognized tokens are tested, but no enumerated coverage contract exists; the JSON password example demonstrates a likely false-negative class consistent with the current caveat.
9. **Human release record:** reviewer identity/qualifications, owner dispositions, final workload/retention decision, and approved/limited/not-approved recommendation are absent by design.

## Proposed R01-R07 dispositions

These are recommendations to the owner and qualified reviewer, not risk acceptance or approval on their behalf.

| ID | Proposed disposition |
| --- | --- |
| **R01** | **REQUIRE CHANGE; remain open.** Fix F1 and add installed legacy lifecycle/state-preservation tests. Correct F2. Then complete a qualified applicability review of the advertised legacy and modern stdio surface, retaining explicit partial/conditional items rather than claiming full MCP certification. |
| **R02** | **HUMAN DECISION REQUIRED; technically supportable only for the written single-instance scope.** Process-local budget/masker handles and restart reset are clearly documented and consistent with the owner's initial scope, but this model does not accept the portability recommendation departure. Require portable state or instance-aware handles before any multi-process/distributed claim. |
| **R03** | **LIMIT CLAIMS; human decision required.** Keep Codex/Cursor cancellation delivery explicitly unsupported in the tested paths; retain unknown-outcome/no-replay guidance and nonpreemption/no-rollback limits. Do not turn recovery evidence into cancellation-delivery support. Require new versioned client evidence if delivery becomes a release requirement. |
| **R04** | **NARROW SCOPE.** Limit initial claims to Linux Python 3.11-3.14, stdio-first advisory use, and the specifically tested CLI/control paths. Exclude Windows/macOS/native UI and public/non-loopback/TLS deployment until separate acceptance and evidence exist. |
| **R05** | **REMAIN OPEN pending owner workload and retention requirements.** Define calls/minute, successful-write mix, duration, audit size/retention/archive/anchor requirements, and recovery objectives. Compare those requirements to the finite evidence; add tests or narrow the scope. Do not infer production durability from the current campaigns. |
| **R06** | **NOT FINAL.** Preserve the verified signed baseline and provenance record, keep the changelog unreleased and companion skill draft/non-submittable, correct the contradictory README claim, and produce a new exact-candidate affected/full replay after fixes. No stable tag, marketplace submission, or distribution claim is justified yet. |
| **R07** | **QUALIFIED HUMAN REVIEW STILL REQUIRED; no approval supplied here.** This model review recommends “not yet ready for stable release” because F1, final-candidate evidence, workload/retention decisions, and the independent-human gate remain open. A qualified human must record final severity/dispositions and an approved/limited/not-approved recommendation. |

## Unanswered questions for the owner/human reviewer

- What exact production workload and retention/archive period must the initial release sustain?
- Is strict legacy lifecycle enforcement required, or is the intended claim to be narrowed to interoperability with well-behaved tested clients? Narrowing the claim would not erase the current malformed-sequence state-mutation risk.
- Which exact post-fix commit and immutable wheel/source/provenance bundle will be designated the release candidate?
- Who is the qualified independent reviewer, what relevant qualifications do they have, and where will their durable disposition record live?
- Is the JSON/config password false-negative class acceptable under the present signature-only promise, or should the initial supported-format contract include common serialized assignments?

## Final recommendation and independence statement

The code is credible for continued development and bounded owner-operated advisory testing, with unusually good evidence hygiene and honest scope documentation. It is **not yet technically ready for a stable release designation**: correct the legacy lifecycle defect, repair the README contradiction, decide whether to improve or more precisely inventory masking signatures, and replay affected evidence on an exact candidate. Preserve the explicit cancellation, state-portability, audit, deployment, and workload limits.

This report is an independent second-model assessment in the limited sense of a separately requested model pass. It is not independent qualified human approval, does not accept residual risk for the owner, and cannot satisfy the repository's human release gate.

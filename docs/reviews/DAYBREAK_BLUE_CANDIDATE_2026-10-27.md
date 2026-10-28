# Runtime Guard adversarial candidate review — 2026-10-27

## Review identity

- Repository: `/home/rich/dev/runtime-guard-mcp`
- Requested candidate: `46b7d73`
- Resolved candidate: `46b7d73e6bc7c62c7d4687e6d5997360e88bc3a6`
- Signed runtime source used by the supplied artifact evidence: `2fe923267dd6648b999b94e3f58a1ed600625943`
- Review snapshot: detached `git archive` at the resolved candidate, extracted to `/tmp/rg-candidate-46b7d73-readonly` and made read-only
- Requested reviewer configuration: Daybreak Blue (`gpt-daybreak-blue-latest`), extra-high (`xhigh`) reasoning
- Observable reviewer configuration: the exact serving-model identifier and reasoning-effort setting are not exposed inside this session. The session exposes only a generic GPT-5-based Codex identity, so the requested model/effort cannot be independently attested by the reviewer.
- Independence: fresh bounded source review in a separate model session; no human technical review occurred. Current project policy explicitly recommends but does not require independent human review (`docs/RELEASE-READINESS-REVIEW.md:5-7`).

## Technical verdict

**READY WITH LIMITATIONS** for the documented pre-1.0, single-trusted-owner, one-process/one-audit-writer, Linux Python 3.11–3.14, stdio-first advisory scope.

I found no runtime source defect that blocks that narrow scope. The reviewed runtime modules are byte-identical to the signed source, and the focused repeated tests passed. The verdict does **not** certify complete MCP conformance, Streamable HTTP, public/non-loopback deployment, multi-tenancy, whole-agent enforcement, rollback, an indefinite workload SLA, macOS, Windows, or native desktop UI behavior.

The exact `46b7d73e...` distribution is not yet publication-ready: the supplied signed wheel/source bundle and lifecycle/resource records identify `2fe9232...`, not the complete candidate source tree. An exact-candidate build/provenance record remains required, and the active README's stale human-approval wording should be corrected before that build is designated final. Neither limitation invalidates the inherited runtime evidence because the runtime and package contract bytes did not change.

This is a technical recommendation, not authorization to publish, tag a stable v1, use a `latest` designation, or broaden the accepted scope.

## Findings

### F-01 — Medium — Supplied signed distribution is not bound to the complete `46b7d73` candidate

**Files/lines**

- `docs/evidence/review-baseline-2026-10-27.json:2-4`
- `docs/evidence/current-runtime-ten-minute-2026-10-27.json:43-46`
- `docs/evidence/linux-package-lifecycle-2026-10-27.json:15-16`
- `docs/evidence/review-bundle-retrieval-2026-10-27.json:4-9`
- `docs/CANDIDATE_OWNER_REVIEW.md:9,25`
- `.github/workflows/release.yml:42,50,78`

**Evidence**

Every supplied signed-artifact, ten-minute, package-lifecycle, and retrieval record identifies source `2fe923267dd6648b999b94e3f58a1ed600625943` and workflow run `40595971974`. Candidate `46b7d73e...` adds documentation, tests, review scripts, and workflow changes. The five runtime modules, schemas, `pyproject.toml`, and example configuration are unchanged, but the source distribution inspector intentionally includes committed docs/scripts/tests; therefore the existing signed sdist is not the complete source distribution of `46b7d73e...`. No signed run/ref/digests for the full candidate were present in the reviewed repository packet.

The release workflow is designed to bind newly built sdist/wheel inspection reports and attestations to `$GITHUB_SHA`, so the mechanism for closing this gap exists. The current packet itself warns that later changes must be checked before candidate designation and that final distribution claims must bind the designated candidate.

**Impact**

The signed wheel is strong inherited evidence for runtime behavior because the shipped runtime bytes and package identity contract are unchanged. It cannot, however, be represented as an exact signed build of the full `46b7d73e...` candidate or its changed documentation/review tooling. Doing so would overstate artifact provenance and final-distribution coverage.

**Required disposition**

After resolving F-02, build and inspect the sdist/wheel from exact `46b7d73e...` (or a clearly identified documentation-only successor), record exact run/ref/digests and provenance, repeat the bounded installed smoke/package-lifecycle checks against that artifact, and verify retrieval against the final trusted record. The unchanged-runtime ten-minute core replay need not be repeated unless the resulting runtime bytes or relevant build/package behavior differ.

**Confidence:** High.

### F-02 — Low — Active README contradicts the current independent-human-review policy

**File/lines**

- `README.md:154,162,178,180`
- Governing policy: `docs/RELEASE-READINESS-REVIEW.md:5-7,13-17`
- Correct summary elsewhere in the same README: `README.md:7`

**Evidence**

The governing policy says independent human technical review is recommended, has not occurred, and is not a hard blocker. `README.md:7` accurately reflects that. Later active README text nevertheless says candidate inspection/provenance does not replace “human release approval,” requires a “human release disposition,” and, most explicitly, says a signed bundle does not replace “independent human approval.” Those statements are not confined to an immutable historical evidence record.

**Impact**

The contradiction does not weaken runtime controls, but it makes the candidate's release-gate claims internally inconsistent and can cause reviewers or users to infer a mandatory gate that the accepted policy explicitly removed.

**Required disposition**

Replace the stale wording with the actual gates: adversarial LLM technical review, disclosure that no independent human review occurred, and separate owner publication authorization. Independent human review may remain described as recommended.

**Confidence:** High.

## Source and control review

### Exact source identity

`git diff --exit-code 2fe923267dd6648b999b94e3f58a1ed600625943..46b7d73e6bc7c62c7d4687e6d5997360e88bc3a6 -- src schemas pyproject.toml runtime-guard.example.json` returned zero. Independent SHA-256 calculation of all five runtime modules matched `docs/evidence/review-baseline-2026-10-27.json:232-236`:

| Module | SHA-256 |
|---|---|
| `src/runtime_guard_mcp/__init__.py` | `eb750cd101e5546421dda639405ffb4ccdea9401f0fb184d07a966cad604f67d` |
| `src/runtime_guard_mcp/audit.py` | `756a3c44a4da62af1681afa55ae6769d74a2c683f8fa049060bd6839a217e7ce` |
| `src/runtime_guard_mcp/policy.py` | `80ed17c33eac5a771ea0e393dc3806d2b0d393fc4bf4349a61a9657f03ee1ec9` |
| `src/runtime_guard_mcp/server.py` | `a9cc1d50b445f4e4ecd3815b6895c687be1d4eb7fde97f123d5a536a6f4042bd` |
| `src/runtime_guard_mcp/stdio.py` | `81aea4300625a1dd552d6b768d278e55e50bd5ddc70bd58853fbd4fa4883c74f` |

### Protocol and lifecycle

- Legacy stdio phase ownership is serialized by the dispatcher; legacy tools remain gated until successful `initialize` followed by `notifications/initialized` (`src/runtime_guard_mcp/server.py:484-545`). A saturated initialization notification remains silent and may be retried, as documented.
- Modern stdio request metadata/version dispatch is per-request. Optional HTTP remains a custom legacy JSON-RPC endpoint, not MCP Streamable HTTP, and is excluded from the supported public/TLS claim.
- Request/frame sizes, JSON nesting/structural markers, pending work, stdio output frames/bytes, handler count, and deadlines are bounded. The advisory tools do not execute shell commands or open target-file contents.
- Cancellation suppresses eligible queued/in-flight replies but does not preempt completed policy work or roll back budgets, masking state, or audit writes (`src/runtime_guard_mcp/server.py:475-480`; `README.md:71`). This is accurately disclosed.

### Masking

- The quoted/unquoted assignment pattern at `src/runtime_guard_mcp/policy.py:187` covers the accepted balanced, final-unterminated, escape, space, and punctuation cases. State is bounded to 128 unfinished streams and 4,096 distinct placeholders per transport caller.
- The masker remains signature-based and intentionally cannot guarantee removal of short, encoded, unknown, or overlength secret formats. Replacement output need not preserve JSON syntax. These limitations are explicit and appropriate for an advisory tool, not a data-loss-prevention boundary.

### Audit and resource failures

- SQLite uses WAL, an in-process writer lock, startup chain verification, record and page ceilings, and a WAL checkpoint admission threshold (`src/runtime_guard_mcp/audit.py:32-150`). Capacity, WAL-capacity, integrity, and general SQLite failures fail closed with generic tool results.
- Policy/budget/masker state can change before an audit write fails (`src/runtime_guard_mcp/server.py:308-333`). The project correctly warns against automatic replay. Full-capacity denials cannot append their own audit row.
- Hash chaining detects mutation/reordering within retained records but is not externally anchored; deletion of the entire tail across restarts is outside its guarantee. Recovery requires a verified SQLite backup and a new chain when changing files.
- The fresh ten-minute evidence covers 9,600 audited core calls in 600.019 seconds with restart/integrity and bounded observed resources, but it raises the invocation allowance and uses legacy custom HTTP. It is valid core policy/audit evidence, not a stdio-specific ten-minute transport run or an indefinite SLA. Separate bounded stdio lifecycle, adversarial-frame, cancellation, and output-backpressure evidence covers the primary transport.

### Package, provenance, and backup claims

- Wheel inspection restricts members, rejects encrypted/nonregular/oversized entries, checks source bytes, identity metadata, no runtime dependencies, entry point, licenses, and every `RECORD` digest/size (`scripts/inspect_wheel.py`).
- Sdist inspection rejects traversal, multiple roots, duplicates, nonregular/oversized members, modified/uncommitted source, and missing committed runtime/docs/scripts/tests (`scripts/inspect_sdist.py`).
- The package-lifecycle probe reports clean Linux install/launch/uninstall, a synthetic distinct-version upgrade, zero file residue under the tested prefix, and owner-data preservation. It does not claim a native installer, historical data migration, or absence of empty-directory residue.
- The bundle verifier safely bounds and hashes the trusted seven-member review directory. The retrieval record explicitly does not re-verify signatures or establish independent/off-device durability.
- Accepted backup policy is satisfied only at its stated level: 90-day policy-constrained GitHub artifact retention plus a verified owner-account local copy. There is no permanent-retention, independent-backup, physical-power-loss, or owner-custody acceptance claim. No new backup design is required by the governing policy.

## Repeated versus supplied evidence

### Repeated independently in this review

- Resolved the exact commit and created a detached read-only archive snapshot.
- Reviewed `docs/LLM_REVIEW_PROTOCOL.md`, accepted scope/policy, runtime source, changed workflows/scripts/tests, package inspectors, and current evidence records.
- Confirmed zero diff for runtime modules, schemas, package identity contract, and example configuration between signed source and candidate.
- Recomputed and matched all five runtime-module hashes.
- Counted 127 candidate test methods in the exact snapshot.
- Ran 54 selected, bounded, non-network unit tests covering the prior fixes, bundle validation, masking/policy, stdio I/O, audit startup/storage/capacity/memory/field types, invocation limits, and sdist/wheel inspection: all passed.
- Attempted selected protocol tests. Five loopback HTTP cases could not create sockets because the review sandbox returned `PermissionError: [Errno 1] Operation not permitted`; those cases were not treated as fresh validation. No external targets were contacted.
- Observed Python 3.14 `ResourceWarning` messages for unclosed SQLite connections in tests that repeatedly construct runtime objects. This is test/lifecycle hygiene rather than a scoped service leak: the supported server creates one audit connection for process lifetime, and the supplied ten-minute evidence reports stable descriptors. It is not elevated to a release finding for the accepted one-process scope.

### Supplied but not repeated here

- Signed GitHub artifact run `40595971974`, Sigstore/GitHub attestation verification, negative provenance checks, and exact wheel digest `625472727e2bc950d3d7a6400f28e8aba10b3cc433ff330b4c0ffdab9ce808b5`.
- The full 123-test signed-source run and the broader 127-test candidate claim. This review repeated a focused 54-test subset only.
- The 9,600-call/ten-minute exact-wheel replay, installed API/scanner probes, filesystem-full/kill/resource campaigns, and native Claude/Codex/Cursor observations.
- Disposable Linux container lifecycle result and container image digest. No Docker container or VM was started in this review.
- Private owner-account archive custody. Only the checked-in retrieval record and verifier implementation/tests were reviewed; no account access or private path was used.

## R01–R07 disposition

| Decision | Disposition |
|---|---|
| R01 protocol coverage | **Accept with limitations.** Modern and legacy stdio are supported only within the documented partial conformance. HTTP is custom legacy JSON-RPC, not Streamable HTTP. No complete MCP certification is claimed. |
| R02 process/local identity | **Accept with limitations.** State, quotas, masking namespaces, and audit ownership are process-local and appropriate only for one trusted owner. Metadata is not authentication; multi-tenancy is excluded. |
| R03 cancellation | **Accept with limitations.** Claude's tested path delivered matching MCP cancellation; tested Codex/Cursor interrupt paths did not. No preemption, rollback, or safe automatic replay is claimed. |
| R04 platform/deployment | **Accept with limitations.** Linux Python wheel and stdio only. Public/non-loopback/TLS, Windows, macOS, native desktop UI, and multi-tenant deployment remain excluded. Experimental macOS work outside this revision is not reviewed and must not be described as supported. |
| R05 workload/storage | **Accept with limitations.** Defaults are admission/storage bounds, not performance promises. Finite core and stdio-specific campaigns support bounded pre-1.0 use; they do not establish an indefinite SLA, physical-power-loss durability, or externally anchored audit history. |
| R06 distribution/backup | **Open for exact-candidate closure.** Existing signed runtime evidence and accepted backup arrangements are usable, but F-01 prevents calling the current bundle the exact final `46b7d73e...` distribution. F-02 should be corrected before final claims are captured. |
| R07 recommendation | **Ready with limitations.** No human technical review occurred or is required under current policy. Resolve F-01/F-02 before exact artifact designation/publication; do not broaden the accepted scope. |

## Remaining gates

1. Correct the active README's stale independent-human-approval wording.
2. Build, inspect, test, attest, checksum, retain, and retrieve an exact candidate bundle bound to the final commit/ref; capture its new run and digests.
3. Confirm the exact-candidate wheel/runtime hashes still match the reviewed bytes. If they differ, repeat affected runtime, lifecycle, and resource evidence rather than inheriting it.
4. Record final owner publication authorization separately. This is not technical human review and does not authorize stable v1/`latest` or unsupported platforms.

No repository files were changed, no artifacts were published, no VM/container was started, and no other chat was messaged.

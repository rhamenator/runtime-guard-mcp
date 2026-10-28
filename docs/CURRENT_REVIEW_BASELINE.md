> Policy update, 2026-10-27: the [current release policy](RELEASE-READINESS-REVIEW.md) supersedes this packet's earlier mandatory-human-approval wording. Independent human review has not occurred. Owner self-review and all applicable production-quality gates remain required for a pre-1.0 candidate. Historical evidence and model reports are unchanged.

# Current technical review baseline

Status: **REVIEW BASELINE, NOT APPROVED**. Owner self-review: **PENDING**. Independent human review: **NOT PERFORMED**. This is the current assembled self-review packet; the [earlier baseline](REVIEW_BASELINE_2026-10-24.md) and [affected-claim supplement](COMMAND_OPTION_REVIEW_REFRESH.md) retain their historical source/artifact identities. No stable release, tag or marketplace submission is approved.

The owner accepted the limited [initial scope](INITIAL_RELEASE_SCOPE.md) on 2026-10-27. The [original Daybreak Blue review](reviews/DAYBREAK_BLUE_2026-10-27.md) identified follow-up defects. PR #115 fixed them; the [focused fix review](reviews/DAYBREAK_BLUE_FIXES_2026-10-27.md) and [punctuation delta review](reviews/DAYBREAK_BLUE_PUNCTUATION_2026-10-27.md) found no remaining findings within their stated scopes. These reports retain their original revisions, pending-CI observations and limitations; subsequent CI completion is recorded below. The immutable baseline below retains its exact source/artifact identity; model review and scope acceptance are separate from final owner self-review and publication authorization.

## Exact material

Source: `2fe923267dd6648b999b94e3f58a1ed600625943`, version 0.1.0, build ref `refs/heads/codex/legacy-handshake-json-masking`. [Signed review build](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40595971974) passed; its package job ran 22:37:56–22:39:15 UTC on 2026-10-27 (79 seconds; 232 seconds including workflow queue). This is a branch review artifact, not a stable release. PR #115 integrated it at `a0c084654ce5cd5d4f4fa3a9a2d06ced8c193b2d`; [main CI](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40597024396) and associated checks passed. All five runtime modules match the reviewed artifact source byte for byte; the packet records their hashes.

Download `runtime-guard-mcp-review-packages` from that build. Follow [provenance verification](ARTIFACT_PROVENANCE.md), requiring this exact source commit, branch ref and `release.yml`. Wheel SHA-256: `625472727e2bc950d3d7a6400f28e8aba10b3cc433ff330b4c0ffdab9ce808b5`. The [machine-readable packet](evidence/review-baseline-2026-10-27.json) records artifact digests, signatures, scanner/client results, review report hashes and measured timings. The [previous packet](evidence/current-review-baseline-2026-10-24.json) remains historical. Artifact retention requests 90 days, subject to repository policy; preserve a verified copy and record archive custody under the provenance instructions.

All subject checksums matched. Five signatures verified locally and four wrong-identity/changed-byte controls rejected, using the documented temporary two-host CONNECT relay with unchanged TLS/trust checks. Source/wheel inspections matched Git, including generated package identity checks added in PR #109; no server runtime dependencies were found. Local suite: 123 tests (11.87 seconds wall time); wheel build: 2.19 seconds. The skill remains draft; this packet does not qualify a final marketplace ZIP.

## Fresh evidence on this downloaded wheel

A new no-dependency venv installation passed 83 API checks including optional owned-loopback Nmap, command regressions and legacy initialization checks. The dedicated installed lifecycle probe rejected eight premature tool calls while preserving budget, masker and invocation state, then recorded three authorized audit decisions. Wfuzz passed 21 scanner requests plus auth, framing, policy, redaction, saturation, audit-tamper and recovery checks. Submitted shell text is inspected, never executed by the server or command-regression fixtures.

All three account-backed native control probes completed sequentially without retry on this wheel:

| Client/control | Protocol | Matching cancellation | Recovery |
| --- | --- | --- | --- |
| Claude Code 2.1.301 / stream-JSON interrupt | 2026-07-28 | Delivered; delayed reply suppressed | SAFE second call; one process, two audit decisions |
| Codex CLI 0.151.0 / app-server interrupt | 2025-06-18 | Omitted; original call replied | SAFE second call; one process, two audit decisions |
| Cursor 2026.10.19-6bbf2c4 / ACP cancel | 2025-06-18 | Omitted; original call replied | SAFE second call; one process, two audit decisions |

These expose one advisory command tool with a test-only first-call delay. They do not certify desktop Stop/Escape, every native tool, saturated client queues, preemption or rollback. Negative Codex/Cursor observations do not pass cancellation delivery. See [client recovery guidance](CLIENT_CANCELLATION.md).

## Resource evidence distinction

A [fresh exact-wheel ten-minute replay](SUSTAINED_RESOURCE_EVIDENCE.md#current-signed-wheel-ten-minute-replay-2026-10-27) now completed all 9,600 successful audited calls in 600.019 seconds with integrity, resource and restart checks passing. It used this packet's exact wheel and records source/probe/module identities. The historical [earlier run](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40118875726) at `0dc582b959e9c178e0cabe626dbd3692fb10943d` remains separate and predates the runtime fixes. Both are finite campaigns, not a production SLA or owner workload acceptance. The invocation allowance is raised in these successful-write fixtures to isolate storage/state bounds; default admission limits are unchanged.

## Open release decisions

The seven [required decisions R01–R07](REVIEW_BASELINE_2026-10-24.md#required-decisions-and-review-record) still require an owner disposition within the accepted initial scope: normative/schema review, process-local portability, cancellation/nonpreemption limits, native UI/platform/TLS scope, production workload/audit durability and retention, final distribution claims, and the independent recommendation. The bounded single-owner advisory boundary remains unchanged; HTTP is legacy JSON-RPC, not Streamable HTTP. The owner must record scope, findings/severity, dispositions and recommendation under [release policy](RELEASE-READINESS-REVIEW.md), using the [prepared worksheet](CANDIDATE_OWNER_REVIEW.md). Independent human review has not occurred and is not a hard blocker for Runtime Guard. Passing checks and signed artifacts do not substitute for that decision.

# Runtime Guard reviewer brief

Review type: separate-model technical review requested by the owner; qualified human release approval remains pending. Target runtime/source baseline: c945f65138dfcc5494cc20bb3055b6aa0838a0f2. Also review the exact documentation commit containing this brief and INITIAL_RELEASE_SCOPE.md; record both commits in the report. Later main changes through fc862aed86ff5d02e921e67255f39324b2839369 update signing/CodeQL workflow pins only and do not silently replace the signed baseline.

## Objective and inputs

Assess fitness for the owner-accepted single-owner, single-process, Linux-tested, stdio-first advisory scope in INITIAL_RELEASE_SCOPE.md. Read AGENTS.md, QUALITY_BAR.md, RELEASE-READINESS-REVIEW.md and CURRENT_REVIEW_BASELINE.md, then the relevant security/conformance/source/test evidence. Use narrow reads and reuse exact-head evidence. The signed baseline machine record is docs/evidence/current-review-baseline-2026-10-24.json. Do not infer correctness from green CI or earlier model conclusions.

## Priority review questions

1. Find concrete correctness/security defects in advertised behavior and fail-closed boundaries; inspect authentication/host/origin, malformed JSON-RPC, input validation, state isolation and audit-failure behavior within the intended owner model.
2. Check modern stdio normative applicability, version/error/cancellation requirements and advertised capabilities. Separate unsupported optional features from missing mandatory requirements; cite pinned primary specification material for normative findings.
3. Examine bounded state/output/resource/audit admission, concurrency, hash-chain limitations and recovery. Distinguish observed tests from unproven guarantees, especially process-local portability and no rollback.
4. Check command/path advisory limits and secret-masker false negatives/stream handling against precise documented claims. Do not demand whole-agent enforcement that the product disclaims.
5. Reconcile Codex/Cursor cancellation limitations with setup/skill instructions and accepted scope. Treat omitted wire notifications as unsupported cancellation delivery, not a passing delivery test.
6. Check packaging/source/wheel/provenance and draft skill claims. Record missing final-candidate replay, retention and workload/human decisions without converting them to approvals.

## Safe, economical verification

Read-only review of a detached exact-source checkout. Do not modify the implementation checkout, user's dirty files, main branch or existing reports. You may write only your report to an explicitly separate output path. Use synthetic fixtures and owned temporary loopback processes for bounded defensive checks; no third-party targets, credential harvesting, offensive framework workflows, live model account probes, VMs, heavy soak or stable publishing. No need to rerun every test if exact-head evidence is valid; run focused checks only for concrete findings. Follow shared usage policy. Other chats being active is not a lock.

## Required report

State actual model/effort, UTC date, exact source/docs heads, review scope and independence limitations. For each finding give severity, file/line, concrete failure/impact, evidence, confidence, remediation and a focused verification plan. Separate reproduced findings, source-only concerns and unanswered questions. Include a claim/evidence gap list and proposed R01–R07 dispositions; do not accept residual risk on behalf of the owner/human reviewer. End with a technical recommendation for the limited scope, explicitly not independent-human release approval. An empty finding list must state what was and was not reviewed. Do not message other chats or launch subagents; the originating task will read the report.

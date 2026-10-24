# Current technical review baseline

Status: **REVIEW BASELINE, NOT APPROVED**. Independent reviewer: **UNASSIGNED**. This is the current assembled self-review packet; the [earlier baseline](REVIEW_BASELINE_2026-10-24.md) and [affected-claim supplement](COMMAND_OPTION_REVIEW_REFRESH.md) retain their historical source/artifact identities. No stable release, tag or marketplace submission is approved.

## Exact material

Source: `c945f65138dfcc5494cc20bb3055b6aa0838a0f2`, version 0.1.0, build ref `refs/heads/main`. [Main matrix CI](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40126650509) passed all four supported Python versions. [Signed review build](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40132714702) ran 21:05:59–21:07:16 UTC (77 seconds), including packaged tests, installed API inspection and signature controls.

Download `runtime-guard-mcp-review-packages` from that build. Follow [provenance verification](ARTIFACT_PROVENANCE.md), requiring this exact commit/ref and `release.yml`. Wheel SHA-256: `c61dcaf4a770674cc50a6f3aabc270e28221603fff1fd347ed40557a0eac7c1d`. The [machine-readable packet](evidence/current-review-baseline-2026-10-24.json) records every downloaded artifact digest, inspections, signatures, scanner/client results and measured timings. Artifact retention is finite; preserve a verified copy for the review record.

All subject checksums matched. Five signatures verified locally and four wrong-identity/changed-byte controls rejected, using the documented temporary two-host CONNECT relay with unchanged TLS/trust checks. Source/wheel inspections matched Git, including generated package identity checks added in PR #109; no server runtime dependencies were found. Local suite: 117 tests. An inspected draft ZIP contains only skill instructions, LICENSE and NOTICE; no marketplace approval is implied.

## Fresh evidence on this downloaded wheel

A new no-dependency venv installation passed 82 API checks including optional owned-loopback Nmap and the background/process-substitution/explicit-option command regressions. Wfuzz passed 21 scanner requests plus auth, framing, policy, redaction, saturation, audit-tamper and recovery checks. Submitted shell text is inspected, never executed by the server or command-regression fixtures.

All three account-backed native control probes completed sequentially without retry on this wheel:

| Client/control | Protocol | Matching cancellation | Recovery |
| --- | --- | --- | --- |
| Claude Code 2.1.301 / stream-JSON interrupt | 2026-07-28 | Delivered; delayed reply suppressed | SAFE second call; one process, two audit decisions |
| Codex CLI 0.151.0 / app-server interrupt | 2025-06-18 | Omitted; original call replied | SAFE second call; one process, two audit decisions |
| Cursor 2026.10.19-6bbf2c4 / ACP cancel | 2025-06-18 | Omitted; original call replied | SAFE second call; one process, two audit decisions |

These expose one advisory command tool with a test-only first-call delay. They do not certify desktop Stop/Escape, every native tool, saturated client queues, preemption or rollback. Negative Codex/Cursor observations do not pass cancellation delivery. See [client recovery guidance](CLIENT_CANCELLATION.md).

## Resource evidence distinction

The earlier [ten-minute run](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40118875726) completed 9,600 successful audited calls, integrity/resource assertions and restart recovery. Its source `0dc582b959e9c178e0cabe626dbd3692fb10943d` has byte-identical copies of all five runtime modules at this baseline; the packet records their hashes. That run did **not** install this downloaded wheel, and its development/packaging sources differ. Treat it as relevant runtime evidence, not an exact-artifact soak. The exact-source matrix also repeats the shorter resource profiles.

## Open release decisions

All seven [required decisions R01–R07](REVIEW_BASELINE_2026-10-24.md#required-decisions-and-review-record) remain unaccepted: normative/schema review, process-local portability, cancellation/nonpreemption limits, native UI/platform/TLS scope, production workload/audit durability and retention, final distribution claims, and the independent recommendation. The bounded single-owner advisory boundary remains unchanged; HTTP is legacy JSON-RPC, not Streamable HTTP. A qualified human must record scope, findings/severity, dispositions and recommendation under [release policy](RELEASE-READINESS-REVIEW.md). Passing checks and signed artifacts do not substitute for that decision.

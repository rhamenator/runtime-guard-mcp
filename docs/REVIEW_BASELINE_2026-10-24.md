# Technical review baseline: 2026-10-24

Status: **REVIEW BASELINE, NOT APPROVED**. Reviewer: **UNASSIGNED**. This packet assembles evidence for the independent review required by [release policy](RELEASE-READINESS-REVIEW.md). It authorizes no stable tag, GitHub/PyPI release or marketplace submission. Findings and risk decisions remain pending; automated checks and this packet are self-review evidence.

## Exact material to review

- Source: `14c1edd54f35db1fe5d3a01d8c3d0fd3ede28390`, package version `0.1.0`, source ref `refs/heads/main` at build time. Review this commit, not a moving branch tip.
- [Signed review artifact run](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40081020664): source archive, wheel, three inspection/API reports, SHA256SUMS and provenance bundle. This was a manual review build, without a stable tag or publication.
- [Exact-source matrix CI](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40076053646): Python 3.11–3.14 passed, including source/archive tests, source-bound wheel inspection, installed protocol/API/resource probes and the isolated SDK/schema client.
- [Machine-readable record](evidence/review-baseline-2026-10-24.json): exact archive/wheel/bundle/report digests, source bindings, signatures, scanner/client results and actual local timing. Workflow artifact retention is finite; preserve a verified copy for the review record.

Download the named `runtime-guard-mcp-review-packages` artifact. Verify SHA256SUMS, then follow [provenance verification](ARTIFACT_PROVENANCE.md), requiring the exact commit above, `refs/heads/main` and the repository's `release.yml` signing identity. Check runtime/license bytes against Git with `inspect_wheel.py --ref COMMIT` and source files with `inspect_sdist.py --ref COMMIT`. Signature trust is workflow identity, not human approval or proof of source correctness. The local DNS workaround preserved end-to-end TLS and default roots; it is documented environment-specific tooling.

## Intended scope and trust boundaries

The four tools are `audit_path_access`, `dry_run_command`, `budget_guard` and `secret_masker`. They return advisory decisions and do not execute commands, open target contents, fetch external URLs or intercept other agent tools. Path checks inspect filesystem metadata. Host authorization remains external. Runtime Guard installs without Request Guard or Outbound Guard.

Stdio supports modern 2026-07-28 requests and legacy 2025-06-18 clients. HTTP is explicitly legacy JSON-RPC over HTTP, with bearer/host/origin admission; it is not Streamable HTTP. The intended operator is a single trusted owner. Transport caller labels are not identities for multiple authenticated people. Budgets/masking handles are process local; SQLite audit state persists. Cross-replica/portable-state and externally anchored audit guarantees are not implemented.

Review [architecture/security](security.md), [modern conformance](MODERN_CONFORMANCE.md), [frozen core inventory](CORE_CONFORMANCE_INVENTORY.md), [version/cache/cancellation review](VERSION_CACHE_CANCELLATION_REVIEW.md) and [request context disposition](REQUEST_CONTEXT_REVIEW.md). The inventory covers nine pinned sources and does not certify the full normative/schema universe.

## Claim-to-evidence map

| Claim area | Evidence at this baseline | Limits requiring review |
| --- | --- | --- |
| Path boundary | Unit and installed real symlink-loop/missing-target/error fixtures; configured-root containment | Advisory metadata check; no TOCTOU prevention or native Windows junction certification |
| Command inspection | Policy fixtures and actual API/scanner injection corpus; no command execution | Heuristic text classification, with documented false positives/negatives |
| Budget/masking | Atomic concurrency, bounded maps/streams, split-secret/schema/context tests in exact-source CI | Caller-reported usage, shared owner scope, restart resets, unknown outcomes after audit failure |
| Audit | Capacity/page/WAL/busy/ENOSPC/type-tamper fixtures; eight SIGKILL recovery cycles; startup hash checks | No external chain anchor, automatic rotation, exact total disk quota, guaranteed commit-interruption or physical power-loss proof |
| Protocol/errors | Installed legacy/modern validation, sorted discovery/cache/version/context, bounded I/O/cancellation and HTTP internal-error recovery | Scoped self-review; no modern HTTP, forced preemption or rollback of committed effects |
| Principal adversarial replay | Fresh downloaded signed wheel: Wfuzz 21 scanner requests plus policy/security/recovery fixtures; 77 local API checks including actual owned-loopback Nmap | Finite same-host corpus; not a comprehensive penetration test or Internet/TLS deployment certification |
| Resource bounds | Exact-source CI includes denial-heavy 120-second load and 180-second/3,072 successful audited calls, state/output/storage bounds and recovery | Sampled finite regression budgets, not hours-long soak or throughput/latency SLA |
| Distribution | Inspected source archive, source-bound wheel, empty runtime requirements, signatures/identity/tampering rejection controls | Trusted GitHub/Sigstore infrastructure and reviewed source required; no reproducible compressed-byte claim |

The downloaded wheel was installed in a new venv without dependencies. All five provenance subjects verified locally and four wrong-identity/modified-byte cases rejected. No new server runtime dependency was introduced; build/verification/client tools are separate development dependencies. Local tests passed at this source; hosted reports can have fewer checks when optional Nmap is unavailable. The local principal replay explicitly includes Nmap.

## Real-client observations on the same wheel

| Client/control path | Observed protocol | Matching MCP cancellation | Recovery |
| --- | --- | --- | --- |
| Claude Code 2.1.301, stream-JSON interrupt | 2026-07-28 | Delivered; reply suppressed | SAFE second call, one live server process, two audit decisions |
| Codex CLI 0.151.0, app-server interrupt | 2025-06-18 | Omitted; original call replied | SAFE second call, one live server process, two audit decisions |
| Cursor CLI 2026.10.19-6bbf2c4, ACP cancel | 2025-06-18 | Omitted; original call replied | SAFE second call, one live server process, two audit decisions |

All three completed sequentially against this downloaded wheel without retry. This fixture exposes only `dry_run_command` and pauses its first call to create a cancellation window. It proves native control-path observations, not desktop Stop/Escape controls, all native tool workflows, saturated queues or OS-I/O preemption. Completed negative observations for Codex/Cursor do not pass a cancellation-delivery gate. See [recovery guidance](CLIENT_CANCELLATION.md); consuming state must not be blindly replayed. Authenticated probes use normal model accounts and may incur cost.

## Required decisions and review record

No decision below is accepted by this packet. Record the reviewer name/qualifications, date, exact source/artifact digests, findings/severity, evidence, owner, limitations and disposition for every item. Blocking high-severity findings require resolution before approval.

| ID | Open decision/work | Required disposition |
| --- | --- | --- |
| R01 | Remaining normative/schema applicability and error/trace/cancellation coverage | Complete qualified review of advertised scope, identify missing requirements and require fixes where needed |
| R02 | Process-local handles/budgets and portability recommendation departure | Accept explicit single-instance/restart limits for intended use or require portable state implementation |
| R03 | Nonpreemption/committed effects and Codex/Cursor cancellation omission | Accept clearly limited client compatibility or require verified client/server changes; do not label omitted delivery supported |
| R04 | Native UI/all-tool/platform and non-loopback/TLS deployment scope | Identify supported scope and require missing evidence or narrow claims; no Windows/macOS/deployment waiver is implied |
| R05 | Finite load coverage and audit physical durability/anchor/retention limits | Define the required production workload/duration and resolve remaining soak/storage evidence or explicitly limit intended scope |
| R06 | Final claims, changelog, signed artifact retention and companion skill | Recheck against approved scope; keep skill draft until the marketplace/quality gates pass |
| R07 | Independent recommendation | Record approved, approved with limitations, or not approved, with explicit residual-risk dispositions under release policy |

Further runtime changes require a new baseline and artifact replay for affected claims. Documentation-only follow-ups must retain this immutable source/artifact identity and must not silently substitute a new candidate. The periodic readiness work remains active because these release gates are not proven complete.

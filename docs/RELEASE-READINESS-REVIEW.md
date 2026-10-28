# Pre-1.0 Release-Readiness Review

## Purpose

Policy update received 2026-10-27: official candidates remain below 1.0 and must meet the same technical, security, compatibility, documentation, artifact and adversarial LLM review gates as a production release. Independent human review is recommended but is not a hard blocker for Runtime Guard. Disclose explicitly when it has not occurred; model review is not human review. Earlier immutable review reports retain their historical policy statements.

Before publication, record the adversarial LLM review and disposition of every applicable release gate. The owner has stated they cannot perform technical human review; do not require them to substitute for a security reviewer. Do not publish stable v1 or a latest designation. A pre-1.0 version alone does not establish readiness or authorize publication.

Every claimed supported platform needs a native installer or recognized package artifact; portable archives alone are insufficient. The initial scope claims Linux only, with Python wheel packaging. Qualify clean install, launch, upgrade, uninstall and residue in a disposable Linux environment before an official candidate. Windows/macOS remain outside the claimed scope; adding either requires corresponding installer and native disposable-system evidence. Clearly label unsigned installer candidates, supply checksums and provenance where available. Commercial Windows/macOS signing and notarization may await funding; installer implementation may not.

## Shared MCP backup and owner-decision rules

Owner instructions, 2026-10-27: use the same backup and release-decision rules as companion MCP stacks. Subsequent clarification delegates technical readiness review to an adversarial LLM workflow, locally or on GitHub, with Claude permitted as an additional reviewer. Independent human technical review is not required and must not be implied. See [review procedure](LLM_REVIEW_PROTOCOL.md). R01–R07 organize that single evidence-backed review; previously accepted scope is not reopened without an affected change.

GitHub Actions builds and retains release-artifact backups; build locally as well. Use supported-platform runners when additional platforms are claimed. Runtime Guard's current accepted platform remains Linux; Windows/macOS are excluded until their implementation, package and native lifecycle gates pass. Hosted artifact retention currently requests 90 days and is policy constrained, not permanent. Preserve exact candidate commit/ref, checksums, inspection reports and attestations. A separate off-device backup plan or whole-user backup is not an additional gate.

Continue technical work and adversarial scenarios autonomously using disposable containers or VMs when useful. Record review findings, fixes, retests and limitations against exact revisions. LLM recommendations are technical readiness decisions, not a human review or silent authorization to publish stable v1/latest. Building/retaining artifacts does not itself publish an official release.

## Review packet

Provide the reviewer with:

1. the intended scope, requirements, assumptions, and documented exclusions;
2. the architecture, trust boundaries, interfaces, and important design decisions;
3. traceability from requirements or objectives to implementation and verification;
4. automated and manual test evidence, coverage claims, and known test limitations;
5. security analysis, dependency state, static-analysis results, and unresolved alerts;
6. known defects, deferred work, compatibility constraints, and residual risks;
7. reproducible build and release instructions plus artifact provenance; and
8. the exact source revision and release candidate being reviewed.

## Review record

Use the [prepared owner-review worksheet](CANDIDATE_OWNER_REVIEW.md) to record concrete dispositions against the evidence. Its blank fields are intentionally not approvals.

Archive the following in a release issue, release notes, or another durable repository record:

- reviewer model/tool, configuration when observable, date and independence limits; identify any actual human review separately;
- review date, scope, source revision, and release candidate;
- findings and their severity;
- resolution or explicit risk acceptance for each finding;
- limitations of the review; and
- the final recommendation: approved, approved with limitations, or not approved.

Do not claim independent review while blocking high-severity findings remain unresolved or without an explicit, documented risk disposition.

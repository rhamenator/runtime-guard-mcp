# Release-Readiness Human Review

## Purpose

Policy update received 2026-10-27: official candidates remain below 1.0 and must meet the same technical, security, compatibility, documentation, artifact, adversarial and owner self-review gates as a production release. Independent human review is recommended but is not a hard blocker for Runtime Guard. Disclose explicitly when it has not occurred; model review is not human review. Earlier immutable review reports retain their historical policy statements.

Before publication, record the owner's self-review and disposition of every applicable release gate. Do not publish stable v1 or a latest designation. A pre-1.0 version alone does not establish readiness or authorize publication.

Every claimed supported platform needs a native installer or recognized package artifact; portable archives alone are insufficient. The initial scope claims Linux only, with Python wheel packaging. Qualify clean install, launch, upgrade, uninstall and residue in a disposable Linux environment before an official candidate. Windows/macOS remain outside the claimed scope; adding either requires corresponding installer and native disposable-system evidence. Clearly label unsigned installer candidates, supply checksums and provenance where available. Commercial Windows/macOS signing and notarization may await funding; installer implementation may not.

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

- reviewer name and relevant qualifications, identifying owner self-review, model review and independent human review separately;
- review date, scope, source revision, and release candidate;
- findings and their severity;
- resolution or explicit risk acceptance for each finding;
- limitations of the review; and
- the final recommendation: approved, approved with limitations, or not approved.

Do not claim independent review while blocking high-severity findings remain unresolved or without an explicit, documented risk disposition.

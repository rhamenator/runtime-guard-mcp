# Pre-1.0 candidate owner review

Status: **DRAFT — owner self-review and publication authorization not recorded**.
Independent human review has not occurred. It is not mandatory for Runtime Guard under the [current policy](RELEASE-READINESS-REVIEW.md). The archived Daybreak Blue technical reviews are model reviews, with exact revisions and scoped limitations.

## Material to review

- [Accepted initial scope](INITIAL_RELEASE_SCOPE.md): single trusted owner, one process/SQLite writer, Linux/Python 3.11–3.14, stdio first, four advisory tools. This scope decision is already recorded; it is not a new request to approve that scope again.
- [Immutable review baseline](CURRENT_REVIEW_BASELINE.md): source `2fe923267dd6648b999b94e3f58a1ed600625943`, signed build `40595971974`, wheel digest `625472727e2bc950d3d7a6400f28e8aba10b3cc433ff330b4c0ffdab9ce808b5`. Later development changes must be checked for affected evidence before designating an official candidate.
- [Linux package lifecycle](LINUX_PACKAGE_LIFECYCLE.md): disposable unprivileged container plus CI on all supported Python versions; upgrade uses a synthetic lower-version fixture, not a historical release or database migration.
- [Archive retrieval](ARTIFACT_PROVENANCE.md#repeatable-retrieval-integrity-check): complete signed review bundle retrieved and checked against trusted hashes; a local owner-account copy is retained. This is not an independent backup or permanent-retention guarantee.
- [Protocol applicability inventory](CORE_CONFORMANCE_INVENTORY.md), [client cancellation limits](CLIENT_CANCELLATION.md), [resource evidence](SUSTAINED_RESOURCE_EVIDENCE.md), and [prioritized gates](RELEASE_GATES.md).

## Dispositions to record

These are proposed dispositions for final owner self-review, not completed approvals. The technical maintainer may prepare evidence and recommendations; it must not write the owner's signature or invent the owner's workload/backup requirements.

| Decision | Prepared recommendation | Owner disposition still needed |
| --- | --- | --- |
| R01: protocol coverage | Retain the explicit partial modern/legacy stdio claim. HTTP is custom legacy JSON-RPC, not Streamable HTTP. Use the frozen-source inventory and regression evidence; do not claim complete MCP certification. | Identify any remaining normative requirement that is essential to the intended use and require a fix or narrow the claim. |
| R02: volatile state | Retain single-instance budgets, caller labels and masking handles; restart loses process-local state. No distributed quota or identity guarantee. | Confirm these residual limits meet the intended workflow, or require persistent/portable state work. |
| R03: cancellation | Preserve the already accepted client scope: Claude's tested control path delivers matching cancellation; tested Codex/Cursor paths omit it. No forced policy preemption, rollback or retraction of already-writing replies. | Record the final risk disposition; do not reinterpret recovery as cancellation delivery or automatically replay consuming calls. |
| R04: platforms and deployment | Retain Linux wheel/stdio scope with tested Python versions. Native Windows/macOS/UI, public TLS and multi-tenant deployment are excluded. | Check final candidate claims stay inside the accepted scope. New platform claims require native installer or recognized package and disposable native lifecycle evidence. |
| R05: workload and storage | Use defaults as admission bounds, not performance promises: 600 tool invocations/minute, 100,000 audit rows, 64 MiB database pages and 4 MiB WAL admission threshold. Fail closed at capacity; one writer. Finite stress campaigns are evidence, not an indefinite SLA. | Specify intended sustained/burst workload and duration, acceptable recovery behavior, archive/retention period, backup owner/storage and a retrieval schedule. Decide whether further soak/disk/power-loss evidence is necessary. |
| R06: distribution | Keep the companion skill draft and use exact checksums/provenance. Preserve the complete bundle, not only source archives. Final claim/changelog/package review must bind the designated candidate. | Confirm archive custody and backup requirements; approve the exact final distribution and claims after applicable evidence passes. |
| R07: recommendation | Technical evidence supports reviewing the limited pre-1.0 scope; no official candidate or publication approval is asserted here. | Record owner name, date, exact source/artifact, findings and severity, each disposition, and recommendation: approved, approved with limitations, or not approved. Disclose absent independent human review. |

Defaults above describe configured admission ceilings, not exact combined-disk quotas or sustained throughput. No external audit anchor, automatic rotation, rollback, power-loss durability or historical migration guarantee is implied. Do not use an arbitrary successful stress rate as the production workload target: the successful-write probe raises its invocation allowance deliberately.

## Final record

Leave these fields unfilled until the owner has actually reviewed the evidence:

- Owner/reviewer and date:
- Exact designated candidate version (below 1.0), source, artifact run/ref and digests:
- Workload/duration and recovery expectations:
- Audit/archive retention, backup owner/storage and retrieval plan (private paths stay private):
- R01–R07 findings, severity and resolution/explicit risk acceptance:
- Remaining excluded claims and review limitations:
- Recommendation:
- Publication authorization, if any:

No stable v1/latest designation is permitted. Passing the gates and recording a recommendation do not silently authorize marketplace submission or publication.

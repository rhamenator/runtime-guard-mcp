# Signed command-option fix review supplement

Status: **AFFECTED-CLAIM REFRESH, NOT APPROVED**. This supplements [the earlier review baseline](REVIEW_BASELINE_2026-10-24.md); it does not silently replace its artifact identity or independent review record.

## Exact source and artifacts

Source `825ca1bb10a107dd0e95f097cec10f64a1ec1a53` includes PR #104's explicit command side-effect option fix and the B03 allocation documentation. [Main matrix CI](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40093231859) passed. A fresh manual [signed review build](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40099041612) ran 13:38:58–13:40:25 UTC (87 seconds), with source/archive tests, inspected build, installed API checks and signature identity controls. It created no stable release or tag.

Download `runtime-guard-mcp-review-packages` from that run. Require this exact source commit, `refs/heads/main` and `release.yml` under [the provenance procedure](ARTIFACT_PROVENANCE.md). Wheel SHA-256: `1572b70be69392c9710dcd89a6721a091f334554f761a2c48afe3509b4402c0c`. [Machine-readable evidence](evidence/command-option-refresh-2026-10-24.json) records every downloaded artifact digest, source bindings, signature controls and local replay.

## Affected claim and verification

Explicit Git `--output`, find file-output actions and ripgrep subprocess options now return NEEDS_CONFIRMATION instead of SAFE. Nine unit examples and four ordinary-command controls exercise classification; the installed API adds three representative regression cases. No submitted shell commands are executed by those fixtures or by Runtime Guard. Option-like operands can trigger conservative confirmation; configuration, aliases and helpers remain outside semantic guarantees.

All downloaded subject checksums matched. Local verification accepted all five signed subjects and rejected four wrong-identity/modified-byte controls, using the previously documented two-host CONNECT relay without TLS interception or relaxed trust. Source archive and wheel inspections matched the exact Git source and reported no server runtime dependencies. A fresh no-dependency wheel installation passed 80 local API checks (including optional owned-loopback Nmap), Wfuzz's 21 scanner requests plus recovery/security checks, and stdio initialization/discovery/tool-call smoke. Hosted checks can omit optional Nmap. Full local suite: 115 tests, 11.59 seconds; signature replay 37.66 seconds, API 8.47 seconds, Wfuzz 5.79 seconds.

## Retained limits and release decisions

This is bounded replay for the changed command-inspection claim. Claude/Codex/Cursor model-account probes were not repeated; their earlier control-path/cancellation observations remain tied to the earlier wheel. Do not present them as observations on this artifact. This supplement does not establish all-client, all-platform, non-loopback TLS or long-duration load compatibility.

The earlier baseline's R01–R07 dispositions remain OPEN, including independent qualified human review, intended workload/platform scope, process-local state, cancellation omissions, audit durability/retention and final distribution claims. A final reviewer must select an exact candidate and require missing affected/full replay before approving stable use. Artifact signatures and passing CI do not constitute that approval.

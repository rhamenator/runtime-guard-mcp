# Accepted initial release scope

Owner decision: 2026-10-27. This defines intended scope, not production approval or a stable-release authorization.

- Single trusted owner, one Runtime Guard process and one writer per configured audit database. No multi-tenant identity, shared distributed quota or cross-process masking state guarantee.
- Linux-tested Python 3.11–3.14; stdio is the primary client transport. Windows/macOS/native desktop UI compatibility is not certified by this initial scope.
- Four advisory tools only: audit_path_access, dry_run_command, budget_guard and secret_masker. They do not execute commands, open target contents, fetch external URLs or intercept arbitrary agent actions. Host permissions remain external.
- Modern 2026-07-28 and legacy 2025-06-18 stdio within documented conformance limits. Optional HTTP remains legacy JSON-RPC, not Streamable HTTP. This initial scope does not certify public/non-loopback/TLS deployment; such deployment needs separate acceptance and evidence.
- Codex CLI 0.151.0 app-server and Cursor 2026.10.19-6bbf2c4 ACP have tested advisory calls and recovery, but omit MCP cancellation in their tested interrupt paths. Cancellation delivery is unsupported for those paths. An interrupted call may complete, reply and change budget/masker/audit state. Never automatically replay consuming calls; restart is not rollback. Claude Code 2.1.301 delivered matching cancellation in its tested modern control path. None is a desktop Stop/Escape or every-version guarantee.
- Cancellation does not forcibly preempt Python policy work, retract an already-writing frame or undo committed state. See CLIENT_CANCELLATION.md for recovery.

The owner accepted this limited compatibility scope and requested clear cancellation documentation. This is not acceptance of undiscovered defects, every R01–R07 residual risk or a particular production workload. Final candidate evidence and the single adversarial LLM review disposition remain required; measured workload limits are disclosed and existing backup arrangements apply under RELEASE-READINESS-REVIEW.md.

## Separate model review

A separate Daybreak Blue instance is requested for an independent second-model technical review at extra-high reasoning effort. Its report must identify the actual model/effort/source, findings, evidence and limits. It cannot identify itself as a qualified human. Under the updated release policy, independent human review is recommended and its absence must be disclosed, but it is not a hard blocker for Runtime Guard.

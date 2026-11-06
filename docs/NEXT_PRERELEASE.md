# Post-release review and next prerelease queue

Reviewed 2026-11-06 against released/main source `1844501` (0.1.0).
GitHub search found no new issue or PR activity dated on or after October 28.
The two open dependency PRs predate the release; issue #54 remains the release
evidence tracker. Latest main CI (41423107071) and CodeQL (41791946474) passed.
The release remains a prerelease with its ten installer/evidence assets present.
These observations are a snapshot, not proof that users have encountered no bugs.

## Priorities

1. **Command safety classification.** Reproduced `SAFE` for explicit
   `git diff --ext-diff`, `git log --ext-diff -p`, and
   `git show --textconv HEAD:README.md` on 0.1.0. Git can execute configured
   helpers; conversion can also be implicit. The current patch requires both
   explicit disables for diff/log/show before a path separator, respecting later
   enables. It also closes quoted PowerShell output-option classification.
   Focused tests cover all three accepted shells, incomplete disables, ordering,
   path separators, structured handler replies, and recovery. Commands are only
   classified, never executed. This does not certify all Git configuration,
   environment, pager, shell-resolution or submodule behavior. Review other
   read-oriented programs and configuration-driven effects next.
2. **Masking boundary clarity and coverage.** Short, unknown, encoded and
   assignments longer than 256 value units remain unsupported. Evaluate bounded
   fail-closed handling for recognizable oversized assignments before widening
   signatures; preserve chunk-boundary, overlap, capacity and false-positive
   tests. Do not imply that signature masking is universal secret prevention.
3. **Candidate evidence and protocol maintenance.** Replace the stale current
   release-queue/baseline descriptions with the published 0.1.0 evidence and then
   bind new evidence to the successor revision. Review changes against the
   relevant official protocol source before advertising broader conformance.
   Repeat affected installed/client/adversarial checks and local plus hosted
   package lifecycle builds before publication. macOS remains experimental;
   Codex/Cursor cancellation delivery limitations remain disclosed.

No successor version is published or authorized by this development review.
The initial Linux/stdio/single-owner/advisory scope remains in effect. The patch
adds no runtime dependencies or command execution permissions.

Reference: [Git diff helper options](https://git-scm.com/docs/git-diff).

# Runtime Guard MCP: adversarial LLM source review

**Recommendation: ready with limitations** for the accepted limited Linux, single-owner, stdio, pre-1.0 advisory scope. I found no Critical, High or blocking Medium defect. I found two Low masking defects and two Low documentation/claim issues. Fixing F1 and F2 before publication is advisable but not blocking.

This is not human review and not owner approval. It does not authorize publication, a stable/v1 tag or a "latest" designation. Independent human review has not occurred.

## Reviewer identity and method

- **Model:** my environment configuration says Claude Opus 5.5 (`claude-opus-5-5`). That is configuration-supplied; I have no independent way to prove which model ran.
- **Tools:** read-only file reading and search only. I had no shell, so I ran nothing: no tests, no probes, no hashing, no network access. I made no edits and invoked no other agents.
- **Snapshot identity:** `/tmp/rg-candidate-llm-review` is not a git repository, so I could not observe source `46b7d73…` directly. I also could not hash the five runtime modules to confirm they equal `2fe9232`. Both rest on the evidence packet's hashes (`review-baseline-2026-10-27.json:231-237`, `current-runtime-ten-minute-2026-10-27.json:48-54`), which agree with each other.
- **Read:** both required documents first, then all five runtime modules in full, `security.md`, `CLIENT_CANCELLATION.md`, the release-readiness review, the current baseline, the three Daybreak reports, and the baseline, ten-minute and package-lifecycle evidence JSON.
- **Supplied evidence, not rerun by me:** 123 tests, API83, Wfuzz/Nmap, signatures, native-client observations, the 9,600-call ten-minute replay and the Linux package lifecycle run.

## Findings

### F1: Unquoted assignment values over 256 characters are only partly masked (Low, high confidence)

- **Where:** `policy.py:187`. The unquoted branch `[^\s'"]{8,256}` has nothing after it forcing the value to end.
- **What happens:** `token=<600-character JWT or long key>` matches only the first 256 characters. The remaining ~344 characters, including the JWT signature, are returned in clear. The result still says `SAFE/MASKED` with `secret_types: ["PASSWORD_ASSIGNMENT"]`.
- **Claim mismatch:** README:194 says longer formats "can remain unmasked", which implies all-or-nothing. In reality the value is partly masked and reported as detected. Quoted values over 256 characters do fail as a whole, matching the "257 units remain unmasked" boundary Daybreak tested; Daybreak only tested the quoted form.
- **Fix:** add a lookahead such as `(?=[\s'"]|$)` after the unquoted body so it is all-or-nothing, or keep matching to the end of the non-whitespace run. Then document which behaviour applies.
- **Verify:** whole-chunk and every-split tests at 255, 256, 257 and 600 units, plus a test across the 16 KiB streaming tail.

### F2: Overlapping matches from different patterns can leak the uncovered part of the later one (Low, high confidence)

- **Where:** `policy.py:208-226`. Matches are sorted by `(start, -end)`, and any match starting before the cursor is skipped entirely, even if it extends past the cursor.
- **Examples (traced by hand, not executed):**
  - `ops@corp.token=Hunter2Hunter2` → `[REDACTED_EMAIL_ADDRESS_1]=Hunter2Hunter2`
  - `sk-<20+ chars>-password=…` behaves the same way.
- **Impact:** these inputs are contrived, so exposure is low. It is still a correctness gap in a redaction boundary.
- **Fix:** merge overlapping spans into one replacement.
- **Verify:** add overlap fixtures for email/assignment and OpenAI-key/assignment, in both streaming and final mode.

### F3: Stale limitation in the machine-readable baseline (Low, documentation, high confidence)

- `review-baseline-2026-10-27.json:240` says "Historical ten-minute resource evidence predates these runtime fixes; not exact-runtime or exact-artifact evidence."
- `CURRENT_REVIEW_BASELINE.md:33`, `SUSTAINED_RESOURCE_EVIDENCE.md:78-84` and `current-runtime-ten-minute-2026-10-27.json` now record a run on the exact `2fe9232` wheel (`625472…`), with matching module hashes.
- **Fix:** update the limitation, or add an addendum that links to the new record. Note that the replay used legacy HTTP only, not stdio.

### F4: The command tool misses obvious credential paths that the path tool blocks (Low, coverage, high confidence)

- **Where:** `policy.py:71`. The pattern only recognises `~/` or `/home/<user>/` in front of `.ssh` and similar directories.
- **Rated SAFE / `READ_ONLY_COMMAND`:**
  - `cat /root/.ssh/id_rsa`
  - `cat ~/./.ssh/id_rsa`
  - `cat ~root/.ssh/id_rsa`
  - `cat ".env"`
  - `cat $HOME/.ssh/id_rsa`
- `audit_path_access` blocks the equivalent paths through resolved-component checks (`policy.py:50`).
- This falls within the disclosed heuristic and environment-expansion limits (`security.md:7`), so it is not blocking.
- **Fix:** run a component check like `SENSITIVE_PARTS`/`SENSITIVE_FILES` on the `shlex` tokens, after removing quotes and `.` segments.

## Areas reviewed with no defect found

- **Protocol and lifecycle:** the legacy handshake gate (`server.py:536-551`) blocks tool calls before `initialize` and before `notifications/initialized`, and rejects a second `initialize`. A legacy request cannot get past the gate by adding modern metadata, because modern mode then requires full per-request version and capability checks (`:356-378`). The modern-mode tests in `_handle` and `handle` are the same. Daybreak's earlier findings (the handshake gate and the README F2 wording) are resolved; the old README sentence is gone.
- **Cancellation:**
  - Cancellation is processed when the message is received, in arrival order.
  - Queued work is skipped, and the reply is suppressed both before it is queued and before it is written (`stdio.py:53`).
  - `initialize` cannot be cancelled. Unknown or late cancellations are ignored.
  - A request ID stays in use until its output finishes, so IDs cannot be reused early.
  - I found no lock-order deadlock: output completion takes the dispatcher lock only after the output lock is released.
  - The docs accurately state that running work is not preempted and nothing is rolled back.
- **Resource bounds:**
  - 32 admission slots, a matching queue and a 32-frame output queue.
  - A 16 MiB / 5 s output deadline that fails stop (exit 2).
  - A 1 MiB frame limit with drain.
  - JSON depth and structure caps applied before decoding.
  - Bounded budget, fingerprint and masker state.
- **Audit:**
  - Each append runs under the lock in one `BEGIN IMMEDIATE` transaction, checks the latest hash and the in-process tip, and stays within the record, page and WAL caps.
  - Any error replaces the tool result with `BLOCKED` without the computed result.
  - Startup migration and verification are atomic.
  - The unkeyed hash chain, the lack of tail-deletion detection after restart, and the fact that policy state may change before an audit failure are all disclosed (`security.md:9,23,31,37`).
- **Packaging:** no runtime dependencies (`pyproject.toml`). The version is 0.1.0 in both files. Supplied Linux lifecycle evidence covers install, upgrade, uninstall and leftover files.

## Limitations and exclusions

- Nothing was executed; every behavioural statement comes from reading source.
- Out of scope: HTTP beyond loopback/legacy, Windows, macOS (planned, not supported), desktop Stop/Escape, multiple processes or tenants, cancellation delivery from Codex/Cursor (documented as unsupported), production workload/SLA, and power loss.
- I did not review the full normative MCP schema or certify regex performance.

## Recommendation

**Ready with limitations** for the accepted narrow scope, keeping all documented cancellation, no-rollback, audit-anchoring, single-writer and platform limits. Fix F1 and F2 with regression tests, correct F3, and decide whether F4 should be fixed or just disclosed. Only the changed masking code would then need another review. Publication authorization stays with the owner.

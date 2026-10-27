# Runtime Guard final focused fix re-review — 2026-10-27

## Verdict

**All three findings from the `a2b3893` focused review are resolved at `96cafe2c303326183e08da786617e69133836ccf`.** I found no new Critical, High, Medium, or Low defect in the requested final scope.

This is a focused technical acceptance of the fixes, not stable-release approval. The exact-head CI run was still in progress according to the supplied handoff, and final human approval remains a separate mandatory gate.

## Revision, dispatch, and scope

- Reviewed head: `96cafe2c303326183e08da786617e69133836ccf` (`Exclude one-way initialization notification from direct-handler assertions`)
- Comparison base: `a2b38932f94f2cde7464c35395a0260dd2fe5068`
- Detached checkout: `/tmp/rg-daybreak-fixes-final-v2-20261027`
- Checkout state: clean before and after review
- Diff: 10 files, 71 insertions, 8 deletions; `git diff --check` clean
- Fix commits:
  - `a2106ae` — explicit legacy handshakes in version/rate probes
  - `4936d43` — silent saturated initialization notifications
  - `06aa6f0` — final unterminated quoted-assignment masking
  - `96cafe2` — filter one-way notification in direct-handler assertion
- Dispatch model/effort: `gpt-daybreak-blue-latest`, `xhigh`
- Dispatch source: retained task dispatch plus explicit follow-up delegation from source thread `01a14ff8-0df7-7d43-8130-4b165f3ae7bb`; no independent in-band model self-attestation API was available
- No implementation changes, subagents, VMs, external targets, live accounts, model-account probes, third-party services, or heavy soak were used.
- The original report `/tmp/rg-daybreak-fix-review-20261027.md` was preserved unchanged.

## Prior finding status

### 1. Development clients omitted the completed legacy handshake — Resolved

The three previously failing paths now establish the lifecycle state required by the gate:

- `scripts/version_cache_review.py:25-36` inserts a one-way `notifications/initialized` frame immediately after the explicit initialize frame. It has no request ID, so the existing request IDs remain `0..15` and the assertion still expects 16 replies.
- `scripts/invocation_rate_review.py:71-75` waits for the successful initialize reply, sends `notifications/initialized`, and then performs the first legacy tool call.
- `scripts/masker_state_review.py:1-2,50-54` uses the shared real-server handshake helper before the legacy warm-up/tool sequence; the modern branch remains uninitialized.
- `scripts/stdio_adversarial_review.py:99-100` initializes only the legacy corpus. The redundant second legacy initialize was removed, and the modern corpus remains initialization-free.
- `tests/test_version_cache.py:9-13` filters the intentionally response-free notification when exercising `RuntimeGuard.handle` directly.

Focused evidence:

```text
PYTHONPATH=scripts timeout 25s python3 scripts/version_cache_review.py /tmp/rg-final-fixes-server/bin/runtime-guard-mcp
PASS: 2 configurations, 32 replies, legacy/modern interleavings preserved

timeout 30s python3 scripts/stdio_adversarial_review.py /tmp/rg-final-fixes-server/bin/runtime-guard-mcp
PASS: legacy 95 hostile frames/recoveries; modern 109 hostile frames/recoveries
```

A bounded installed-server fixture also exercised the exact invocation-rate sequence (initialize reply, notification, first legacy `dry_run_command`) and the masker helper sequence (helper handshake, first legacy `secret_masker` call). Both returned normal successful results with no `1002` response and no synthetic secret reflection.

The full 60-second invocation-rate recovery and the 4,096-secret masker-state campaign were deliberately not repeated; their lifecycle prefixes were the concern under review. The supplied handoff reported the final 122-test suite and installed lifecycle/API83 probes passing.

### 2. Unterminated quoted assignments leaked at final flush — Resolved

`src/runtime_guard_mcp/policy.py:182-189` now recognizes a balanced closing quote or an unterminated end-of-line/end-of-input suffix, including one unfinished trailing backslash. The core body remains bounded to 8–256 completed match units, where a complete escape pair is one unit.

The previously leaking reproductions now redact:

```text
password="SyntheticPass123!     -> [REDACTED_PASSWORD_ASSIGNMENT_1]
token='SyntheticPass123!        -> [REDACTED_PASSWORD_ASSIGNMENT_1]
{"password":"SyntheticPass123! -> {"[REDACTED_PASSWORD_ASSIGNMENT_1]
password="SyntheticPass123!\   -> [REDACTED_PASSWORD_ASSIGNMENT_1]
```

Focused boundary checks established:

- 7 completed units remain unmasked; 8 units mask.
- 255 and 256 units mask; 257 units remain unmasked.
- 7 ordinary units plus one complete escape pair mask as 8 units.
- 255 ordinary units plus one complete escape pair mask as 256 units; 256 plus an escape pair remain outside the bound.
- An unfinished final backslash is treated as the incomplete suffix, not an additional completed unit. Thus at least 8 completed units must precede it.
- Double- and single-quoted forms behave consistently.
- The long-public-prefix/every-secret-split cases in `tests/test_review_fixes.py:40-55` keep the assignment in the streaming tail until final masking; no secret fragment is emitted early.

The focused unit run passed:

```text
PYTHONPATH=src python3 -m unittest -q tests.test_review_fixes tests.test_version_cache
Ran 6 tests in 0.717s — OK
```

### 3. Saturated admission responded to `notifications/initialized` — Resolved

`src/runtime_guard_mcp/server.py:471-495` now identifies notification envelopes before bounded admission. When capacity is full, requests still receive `1001`, but notifications return silently. A dropped initialization notification never reaches the worker and therefore cannot advance `legacy_phase`.

The committed capacity-one test at `tests/test_review_fixes.py:61-90` verifies silence, no phase transition from `new`, and subsequent dispatcher recovery.

I additionally exercised the lifecycle-specific state omitted from that unit fixture:

1. Complete initialize and reach `awaiting_notification`.
2. Occupy the only admission slot with a blocked modern ping.
3. Submit `notifications/initialized` while saturated.
4. Observe no reply and phase still `awaiting_notification`.
5. After capacity clears, verify a legacy tool request still returns `1002`.
6. Resend the notification, observe phase `ready`, then successfully list tools.

Result:

```json
{"silent_drop":true,"phase_after_drop":"awaiting_notification","pre_resend_code":1002,"phase_after_resend":"ready","post_resend_result":true}
```

The original notification no-response defect and the unintended-state-transition concern are both closed. The chosen overload behavior is intentionally lossy and is accurately documented: a saturated legacy client must resend the notification or reconnect.

## Artifact binding

The installed artifact used for focused client probes was `/tmp/rg-final-fixes-server`. The two relevant installed runtime modules were byte-identical to the exact reviewed head:

```text
policy.py  SHA-256 5235779ec609c036142e5f7230e48b0bad634f69eda17b3972f15cb7513deb29
server.py  SHA-256 a9cc1d50b445f4e4ecd3815b6895c687be1d4eb7fde97f123d5a536a6f4042bd
```

`cmp` returned equality for both source/installed pairs. The wheel predated only the final test-only commit; the relevant runtime bytes match `96cafe2`.

## Supplied evidence and independent focused evidence

Supplied but not broadly rerun:

- Full final suite: 122 tests PASS, 11.472 seconds test time
- Installed final lifecycle/API83: PASS
- Exact-head CI: rerunning/pending at handoff time

Independently run here:

- Exact revision/status/diff verification and `git diff --check`
- Relevant runtime installed/source byte comparison
- Six focused unit tests
- Installed version/cache review
- Installed legacy and modern stdio adversarial corpora
- Installed explicit invocation-rate handshake prefix
- Installed helper-based masker handshake and first call
- Capacity-one `awaiting_notification` silent-drop/locked-phase/resend recovery
- Quoted-assignment original repros, 8/256 boundaries, complete escapes, trailing unfinished escape, and streaming-tail behavior

## Residual limits and release gate

- Assignment masking remains a signature heuristic, not a JSON parser. Values shorter than 8 completed units, longer than 256 units, encoded/unknown formats, and other undisclosed signatures may remain unmasked. Replacement can make JSON invalid.
- The 16 KiB streaming tail is conservative for supported signatures, but this review did not attempt arbitrary Unicode/pathological-regex performance certification.
- Saturated initialization notifications are silently dropped by design. The server cannot acknowledge a notification; clients that receive `1002` after capacity clears must resend or reconnect.
- The committed saturation unit test checks silence and generic dispatcher recovery from phase `new`; the exact `awaiting_notification`/resend lifecycle was verified in this review but is not yet encoded in that test.
- The full invocation-rate minute reset, full masker capacity campaign, broad CI matrix, official SDK probes, filesystem-full behavior, and longer resource campaigns were outside this focused rerun.
- Exact-head CI completion was not available during this review. A green CI result and separate human approval remain mandatory before any release or stable label.

## Final disposition

- Prior Finding 1: **Resolved**
- Prior Finding 2: **Resolved**
- Prior Finding 3: **Resolved**
- New findings in focused scope: **None**
- Focused fix verdict: **Technically accepted, conditional on green exact-head CI and required human approval**
- Stable/release approval: **Not granted**

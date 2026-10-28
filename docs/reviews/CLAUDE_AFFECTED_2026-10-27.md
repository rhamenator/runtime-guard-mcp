# Affected-fix review: snapshot `995931e4a0a00b8df18dce668e49a5f09c04f005`

**Verdict: ready with limitations.** All four fixes work for the inputs the earlier review reported. One Low defect remains in F1 (streaming only), and F4 still lets a few lexical forms through. Neither blocks the accepted narrow Linux scope.

## How this review was done

- **Model:** my environment configuration says Opus 5.5 (`claude-opus-5-5`). That comes from configuration; I can't prove independently which model ran.
- **Read-only:** I only read and searched files. I ran no commands, tests, hashes or network calls, made no edits and started no other agents. `/tmp/rg-candidate-fixes-995931e` is not a git repository, so I could not confirm the snapshot hash myself. Every behavioural statement below comes from tracing the code by hand.
- **Files read:** `docs/reviews/CLAUDE_CANDIDATE_2026-10-27.md`, `src/runtime_guard_mcp/policy.py`, `tests/test_masking_overlap_review.py`, `README.md:194-200`, `docs/security.md:1-11`, `docs/CURRENT_REVIEW_BASELINE.md`, `docs/SUSTAINED_RESOURCE_EVIDENCE.md` (outline), `docs/MACOS_PACKAGE_QUALIFICATION.md` and `.github/workflows/macos-package-review.yml`.
- **Not seen by me:** the 131-test pass (you supplied it), final artifacts, the native macOS rerun, signing, and human review. I certify none of them. This report does not authorize publication.

## Fix confirmation

| Fix | Result | Basis |
|---|---|---|
| F1: end boundary on unquoted values | **Confirmed in final mode; a defect remains in streaming (R1)** | `policy.py:193` now ends the unquoted value with `(?=[\s'"]\|$)`. A run of 257 or more non-space, non-quote characters cannot satisfy that by backtracking, so it now fails as a whole. |
| F2: merge overlapping matches | **Confirmed** | `policy.py:211-224` merges overlapping matches transitively (adjacent ones stay separate). The placeholder type is the earliest-starting match's type, and the hash covers the whole merged text, so placeholders are stable. All detected types are reported. The streaming cutoff (`:288-290`) uses the merged spans. Both of the earlier review's examples are fully masked. |
| F4: lexical credential components | **Confirmed for all five listed commands; gaps remain (R2)** | `policy.py:86-91` strips quotes, turns backslashes into slashes and splits on `/`. Nothing is expanded or executed. |
| F3: baseline wording | **Confirmed** | `CURRENT_REVIEW_BASELINE.md:1` says the `2fe9232` packet and its ten-minute run stay historical and are not relabeled. Line 35 links the new record, and `SUSTAINED_RESOURCE_EVIDENCE.md:80` links `current-runtime-ten-minute-2026-10-27.json`. The old JSON at `review-baseline-…json:240` is left unchanged, which is correct. The new runtime needs new evidence. |

## Remaining defects

### R1: Over-long unquoted values are still partly masked at the streaming cutoff (Low, high confidence)

- **Cause:** `mask()` moves the cutoff using matches found in the full buffer (`raw`), but then looks for matches again in `prefix` alone (`policy.py:293`). In `prefix`, the `$` in the new lookahead matches at the cut point.
- **Example:** one non-final chunk of `'token=' + 'Z'*600 + ' ' + 'x'*15884`.
  - The buffer is 16,491 characters, so the cutoff lands at character 107, inside the run of Z's.
  - The full buffer has no assignment match, so the cutoff stays put.
  - The prefix is `token=` plus 101 Z's, which matches. The output is `[REDACTED_PASSWORD_ASSIGNMENT_1]`, reported as `PASSWORD_ASSIGNMENT`.
  - The remaining 499 Z's are emitted later in clear.
- **Impact:**
  - This is the original F1 symptom: a partial mask reported as a detection. It now happens only when an over-long value straddles the cutoff.
  - It contradicts `README.md:200`, which says over-long values "no longer produce a misleading partial assignment match".
  - Nothing leaks that final mode wouldn't also leave in clear, since 257+ is out of scope anyway.
  - The new test misses this case because its 21,000-character prefix always puts the cutoff inside the `public` padding.
- **Fix:** mask the prefix using the spans already computed on the full buffer (those ending at or before the cutoff) instead of matching again. Then add a test where the cutoff falls inside an over-long value.

### R2: Remaining lexical gaps in F4 (Low, high confidence)

- **Bypasses still rated SAFE:** components are only split on `/`, so a filename glued to an option with `=`, a short-option prefix, or a `:` is not caught:
  - `git show HEAD:.env`
  - `git show HEAD:id_rsa`
  - `grep -f.env x`
  - `grep --file=.env x`
- **Globs, also SAFE:** `cat /root/.ss?/id_rsa`. This falls under the expansion limit already disclosed in `security.md:7`.
- **Checks that run first:** commands with `sudo` or `$(…)`, and commands `shlex` can't parse, return NEEDS_CONFIRMATION before the component check runs. They are not SAFE, but they are not BLOCKED either.
- **Over-blocking:** `rg credentials src` and `grep -r shadow .` are BLOCKED. `README.md:200` discloses this.
- **Optional fix:** also split tokens on `=` and `:`, and handle short options with an attached value.

## Claim consistency for the experimental macOS work

- `MACOS_PACKAGE_QUALIFICATION.md` and `README.md:198` stay experimental. They make no claim about supported macOS, PKG/DMG, signing or notarization, and say there is no provenance attestation. That is consistent.
- **Minor wording mismatch (Low, documentation):**
  - The doc calls it "the manually dispatched" workflow, but the workflow also runs on `pull_request` (`macos-package-review.yml:4-10`).
  - On pull-request runs, `GITHUB_SHA` and `git archive HEAD` refer to the temporary merge commit, not the PR head. "Binds the candidate wheel to the Git revision" therefore needs qualifying, or the evidence should come only from `workflow_dispatch` runs on the exact commit.
- I have not seen the rerunning native macOS job or its output and make no claim about it.

## Scope and confidence

I reviewed only the masking and command-policy code that changed, plus the related documentation and workflow claims. Confidence is high for F1, F2 and F4 and for R1 and R2, based on hand-traced regexes and control flow. I did not certify regex performance, the full test suite, artifacts or the macOS run.

**Recommendation:** ready with limitations. Fixing R1, or narrowing the `README.md:200` claim, is advisable before final artifacts are built. R2 can be fixed or disclosed. Publication authorization stays with the owner, and independent human review has not taken place.

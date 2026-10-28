# Runtime Guard punctuation regression fix review — 2026-10-27

## Verdict

**Accepted for the narrow technical scope.** At exact head `2fe923267dd6648b999b94e3f58a1ed600625943`, the original unquoted assignment punctuation coverage is restored without regressing the previously accepted balanced-quoted, public-field, truncated-quoted, streaming-tail, or lifecycle behavior. I found no new Critical, High, Medium, or Low defect in the two-file delta.

This is not stable-release approval. A green exact-head CI run and separate human approval remain mandatory.

## Revision, dispatch, and scope

- Reviewed head: `2fe923267dd6648b999b94e3f58a1ed600625943` (`Preserve punctuation in unquoted assignment masking`)
- Comparison base: `96cafe2c303326183e08da786617e69133836ccf`
- Detached checkout: `/tmp/rg-daybreak-punctuation-20261027`
- Checkout state: clean before and after review
- Diff: exactly 2 files, 12 insertions and 1 deletion; `git diff --check` clean
- Dispatch model/effort: `gpt-daybreak-blue-latest`, `xhigh`
- Dispatch source: retained task dispatch plus explicit follow-up delegation from source thread `01a14ff8-0df7-7d43-8130-4b165f3ae7bb`; no independent in-band model self-attestation API was available
- No implementation changes, subagents, VMs, external targets/accounts, broad test run, heavy soak, or other-chat messages were used.
- Earlier reports were preserved unchanged:
  - `/tmp/rg-daybreak-fix-review-20261027.md` — SHA-256 `c880a868f11d5836a4ce10e8c7abcc44ade9434f6e8749f9e79d9c9c3ddb80c1`
  - `/tmp/rg-daybreak-final-fix-review-20261027.md` — SHA-256 `b60f6104041235a1e676e51431dc6d687bf9f83f79e5abf889c54885f0d40528`

## Delta review

### Implementation

The only runtime change is `src/runtime_guard_mcp/policy.py:187`:

```text
before: [^\s'",}\]]{8,256}
after:  [^\s'"]{8,256}
```

This restores the unquoted value branch to the same exclusion rule used before the quoted-assignment work: whitespace and quote characters terminate an unquoted value; comma, braces, brackets, and other punctuation remain part of the value. The two balanced/truncated quoted branches are byte-for-byte unchanged from accepted head `96cafe2` and precede the unquoted alternative, so a leading value quote cannot fall through to the restored branch.

Consequences verified in source and execution:

- `password=Demo,Pass123!` is masked as one assignment.
- `password=LongerPrefix]privateSuffix123!` is masked as one assignment.
- Opening and closing braces/brackets inside unquoted values are masked rather than splitting the signature.
- Whitespace still terminates the unquoted match, allowing a following `public=keep` field to remain visible.
- Quoted JSON-style values still stop at their proper unescaped closing quote, leaving a following quoted public field visible.
- Final unterminated quoted values still use the dedicated quoted branch and remain masked.
- Nonsensitive `public=Demo,Pass123!` text remains unchanged because the key is not recognized.

### Tests

`tests/test_review_fixes.py:40-55` retains the accepted truncated-quote/long-prefix coverage. The new `test_unquoted_assignment_punctuation_coverage_is_preserved` at `:57-66` checks comma, closing brace, and closing bracket values over every split boundary. The pre-existing balanced quoted/public-field test at `:20-38` remains unchanged.

The focused test file passed independently:

```text
PYTHONPATH=src python3 -m unittest -q tests.test_review_fixes
Ran 6 tests in 0.674s — OK
```

Additional safe synthetic checks covered every split for:

- `Demo,Pass123!`
- `Demo{Pass123!`
- `Demo}Pass123!`
- `Demo[Pass123!`
- `Demo]Pass123!`
- `LongerPrefix]privateSuffix123!`

All values were fully redacted, and a whitespace-separated `public=keep` suffix remained intact. An additional 21,000-character public prefix exercised 40 assignment-boundary splits across the 16 KiB streaming tail; the punctuation-bearing value was fully redacted and the public suffix remained visible.

Regression checks also confirmed:

- `{"password":"Demo,Pass123!","public":"keep"}` redacts the password assignment and retains the public field.
- `password="Demo,Pass123!` remains redacted at final flush.
- `public=Demo,Pass123!` remains unchanged.

The handoff reported the focused six tests and full 123-test suite passing in 11.552 seconds. The full suite was not independently rerun here.

## Residual limits

- Unquoted assignment parsing is deliberately lexical. Because comma/braces/brackets are restored as value characters, delimiter-adjacent text without whitespace or a quote may be included in the redacted assignment. That is the original conservative behavior, may overmask public punctuation-adjacent text, and does not expose the secret.
- The masker remains signature-based rather than a JSON or shell parser. Unknown/encoded formats, short values, and values beyond documented bounds can remain unmasked.
- The broad CI matrix and exact-head installed-artifact probes were outside this narrow rerun. Exact-head CI must be green before merge.
- Human approval remains separate; this review does not authorize release or a stable label.

## Final disposition

- Unquoted punctuation regression: **Resolved**
- Prior accepted quoted/public-field/truncation behavior: **Preserved**
- Prior lifecycle fixes: **Unchanged by this delta**
- New findings in narrow scope: **None**
- Narrow technical verdict: **Accepted, conditional on green exact-head CI and human approval**
- Stable/release approval: **Not granted**

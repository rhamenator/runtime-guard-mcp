**Verdict:** the phantom end-of-input fix is correct. I found no remaining way for a secret to leak in the scope you set. I found two low-severity issues: one causes extra masking, and one is a gap in the advisory lexical check.

**Basis:** I only read `policy.py` lines 20–21, 60–109 and 188–304, plus `tests/test_masking_overlap_review.py`. I ran nothing, so the tests' pass/fail status is unverified. Everything below comes from reading the source.

### Streaming: whole-buffer spans and the cutoff (`policy.py:287-302`)
- **Confirmed:** `_matches(raw)` runs once over the whole buffer. If a merged span straddles the cutoff, the cutoff moves back to that span's start. Merged spans are sorted and don't overlap, so only one can straddle, and the new cutoff can't land inside an earlier span. Only spans with `end <= cutoff` are passed to `_mask` (line 295), and the prefix is never rescanned. That removes the phantom `$` match.
- **Text arriving later can't change those spans:** each pattern reads at most about 8.3k characters past its start (the PRIVATE_KEY body is capped at 8192). The cutoff is always at least 16384 characters before the end of the buffer. So anything matched before the cutoff will match the same way once more text arrives.
- **600-unit value with the cutoff inside it:** for `token=` + 600×Z, the 8–256 value length plus the required lookahead means no match at offset 0. The cutoff stays at 107, the prefix comes out unchanged, and the final tail scan finds nothing. The 257 case behaves the same way. The `$`-anchored partial matches near the buffer end in the every-split test end after the cutoff, so they're excluded.
- **Overlap masking stays stable:** the digest uses the first kind and the full merged value. The final call masks the whole remaining buffer in one pass, so the every-split result should equal a single-shot run, which the test asserts.

### Defect 1: extra masking where the buffer is split (low severity, high confidence)
The buffer kept for the next call starts at `raw[cutoff:]`. When nothing straddles, that cutoff is the plain `len - 16384`, which can fall anywhere, even mid-word. When the next call scans that buffer, `\b` and the email lookbehind `(?<![\w.+-])` can't see the character before the cutoff. They then match where a single full-text scan would not.

Example: send `'a'*k + 'token=Secret12345 ' + ' '*16366` as a non-final chunk, which puts the cutoff exactly at `t`. Scanning the full text, `atoken` fails `\b`, so nothing is masked. In streaming, the next scan starts at `token=…` and masks it. The same applies to SSN (`1123-45-6789` split after `1`) and email.

This causes over-redaction only. I found no way for it to cause under-masking, because a lost lookbehind only adds matches here. Fix: keep a little context before the cutoff and scan the remaining buffer from an offset (`pattern.finditer(raw, pos)`) so the lookbehind and `\b` can see it. None of the supplied tests cover this.

### Lexical operand check (`policy.py:88-90`)
- **Confirmed caught:** `--file=.env`, `--file=".env"`, `--file='.env'`, `--file=.ssh/config` (splits to `.ssh`), `-f.env`, `HEAD:.env` and `HEAD:id_rsa`. In pwsh's non-POSIX mode a token can keep a stray quote, such as `--file=".env"` leaving `".env`. Stripping quotes from each part handles that.
- **Confirmed allowed:** `cat README.md`, `--file=patterns.txt` and `-fpatterns.txt` produce no sensitive parts and don't trigger the rg side-effect options, so they still reach `READ_ONLY_COMMAND`.

### Defect 2: clustered short options (low severity, high confidence; advisory gap)
The `-f` handling only strips a token that *starts with* `-f`. When `-f` comes after other short flags, as in `grep -if.env x` or `grep -vf.ssh/config x`, the token splits into `-if.env` and `-vf.ssh`. Neither matches the sensitive names, and the earlier regex at line 71 needs whitespace or `/` before `.env`. Both commands come back as **SAFE**. If you want to cover this, strip everything up to and including the first `f` in tokens that look like `-[A-Za-z]*f…`, for `grep`/`rg` only.

This is outside what you described as a lexical, non-shell-parsing check, so treat it as a known limitation, not a regression.

### Scope
I didn't review anything else in the snapshot: the rest of `policy.py`, other tests, or any artifact or publication status. You accepted the F2 overlap union earlier, and I didn't re-review it.

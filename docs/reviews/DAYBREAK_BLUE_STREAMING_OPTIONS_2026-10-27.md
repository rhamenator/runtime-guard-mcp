# Runtime Guard final affected-source review — 2026-10-27

## Review identity and actual scope

- Repository: `/home/rich/dev/runtime-guard-mcp`
- Reviewed delta only: `995931e4a0a00b8df18dce668e49a5f09c04f005..2e4aa2c66df72583e638c28e38043c9202fd1065`
- Exact reviewed source: `2e4aa2c66df72583e638c28e38043c9202fd1065`
- Read-only snapshot: `/tmp/rg-candidate-2e4aa2c-readonly`, created with `git archive` and made non-writable
- Runtime delta: `src/runtime_guard_mcp/policy.py` only
- Reviewed policy SHA-256: `7fce6a1ce981a4c934bea0e1c6f8bbaeefe52d823debb2f49432cb504530a9a5`
- Requested reviewer configuration: Daybreak Blue (`gpt-daybreak-blue-latest`), `xhigh`
- Observable configuration: exact served model/effort are not exposed inside the session; only a generic GPT-5-based Codex identity is observable. Requested dispatch is therefore recorded but not independently attested.
- Human review: none occurred and none is required by the current policy.

This review was limited to the AF-01 lexical credential-path fix, the full-buffer streaming-cutoff fix, their focused tests, and the two test/document-only changes in the supplied delta. Unchanged protocol, audit, cancellation, resource, packaging implementation, and earlier review findings were not reopened. The earlier AF-02 documentation finding was not changed by this delta and remains under its prior report rather than being re-adjudicated here.

## Verdict

**NOT READY at exact source `2e4aa2c66df72583e638c28e38043c9202fd1065`.**

The phantom-boundary streaming fix is accepted. The direct, quoted long-option, Git revision-path, and simple `-fFILE` AF-01 cases are fixed. One concrete AF-01 family remains: clustered short options and quoted PowerShell short-option tokens can still carry credential file operands while receiving `SAFE`. Resolve that narrow residual and repeat the affected tests before freezing the runtime source.

No exact `2e4aa2c` artifact bytes, build reports, hashes, or provenance were available to this source review. Reported exact local/GitHub builds were launching and are not certified here. Earlier artifacts must not be relabeled as `2e4aa2c` evidence. This review is not publication permission and does not expand macOS support.

## Finding

### FAF-01 — Medium — Clustered/quoted short `-f` operands still bypass credential-path blocking

**Files/lines**

- `src/runtime_guard_mcp/policy.py:80-109`, especially `88-91`
- `tests/test_masking_overlap_review.py:36-45`

**What was fixed**

The new normalization now:

- splits credential tokens on `/`, `=`, and `:`;
- strips a leading simple `-f` before component comparison;
- strips quotes from individual components;
- correctly blocks the supplied direct, `HEAD:.env`, `--file=.env`, `--file=.ssh/config`, and simple `-f.env` cases;
- preserves benign `--file=patterns.txt` and `-fpatterns.txt` classifications.

Those cases and the adjacent policy regressions passed in the exact snapshot.

**Residual evidence**

The implementation strips a short-file prefix only when the raw token itself begins exactly with `-f`:

```python
token[2:] if token.startswith("-f") else token
```

Standard grep-style short options can be clustered; when an `f` option consumes an argument, the rest of the token is the file operand. In addition, `shlex.split(..., posix=False)` retains outer quotes for PowerShell-like parsing, but the `startswith("-f")` decision happens before those quotes are stripped.

Direct calls to `dry_run_command` on exact `2e4aa2c` produced:

```text
bash:  grep -Hf.env target       => READ_ONLY_COMMAND/SAFE
bash:  grep -nf.env target       => READ_ONLY_COMMAND/SAFE
bash:  grep -vf.env target       => READ_ONLY_COMMAND/SAFE
pwsh:  grep "-f.env" target     => READ_ONLY_COMMAND/SAFE
pwsh:  grep "-Hf.env" target    => READ_ONLY_COMMAND/SAFE
pwsh:  grep "--file=.env" target => SENSITIVE_COMMAND_PATH/BLOCKED
```

For grep, `-Hf.env`, `-nf.env`, and `-vf.env` are clustered short options in which `f` reads `.env` as the pattern file. The server does not execute these commands, but its advisory result is its strongest `SAFE` classification despite the credential-file read.

**Impact**

AF-01's core claim remains incomplete: credential-looking lexical option operands are not consistently blocked for allow-listed read commands. This is not shell expansion or a speculative alias; it is ordinary option parsing. Runtime Guard remains advisory, but returning `SAFE` contradicts the sensitive-path policy and successor claim.

**Required disposition**

Normalize outer quotes before recognizing short options. For allow-listed commands with a file-reading `-f` option, parse/conservatively recognize clustered short-option forms and treat the suffix consumed by `f` as another lexical path operand. Add focused bash/sh and pwsh regressions for:

- `grep -Hf.env target`, `grep -nf.env target`, and `grep -vf.env target`;
- quoted `"-f.env"` and `"-Hf.env"` under `shell="pwsh"`;
- benign clustered equivalents with `patterns.txt`;
- existing simple/long/direct cases to prevent regression.

No expansion or execution is needed.

**Confidence:** High.

## Accepted affected change

### Full-buffer streaming spans prevent phantom boundary matches

**Accepted.** `SecretMasker.mask` now calculates merged spans once from the complete buffered `raw` value (`src/runtime_guard_mcp/policy.py:287-295`). It adjusts the cutoff using those full-buffer spans and supplies only spans ending within the emitted prefix to `_mask`. It no longer rescans `prefix` as an independent string whose artificial end could satisfy the unquoted assignment lookahead.

The regression at `tests/test_masking_overlap_review.py:47-55` uses 257- and 600-unit unsupported assignment values followed by a delimiter and 15,884 public characters. It verifies that the non-final prefix plus final tail equals the original input and that neither half reports a password-assignment signature. The exact repeated run passed.

The coordinate reuse is sound: included spans end at or before the cutoff; spans crossing the cutoff move it to their start and remain wholly buffered; spans starting at the cutoff are excluded from the prefix and remain in the tail. No new unbounded state or runtime dependency is introduced.

## Test/document-only affected changes

- `tests/test_package_lifecycle_environment.py` now compares exact PATH components rather than rejecting any interpreter path containing the substring `/host`. This correctly avoids false failure on hosted-toolcache paths without weakening the expected component list.
- `docs/MACOS_PACKAGE_QUALIFICATION.md` now distinguishes pull-request merge revision/ref identity from exact branch-candidate identity. This is claim-consistent.
- Supplied reports say native macOS lifecycle passed the `995` and `9fd` PR-merge builds. Those are useful experimental native-environment observations but are not exact `2e4aa2c` artifacts, provenance, or supported-macOS certification. The documented wheel/no-PKG/no-signing boundary remains unchanged.

## Repeated versus supplied evidence

### Repeated independently

- Resolved and archived exact `2e4aa2c66df72583e638c28e38043c9202fd1065` read-only.
- Reviewed every changed line in the four-file delta.
- Confirmed the exact snapshot contains 132 test methods.
- Ran the four focused modules/adjacent regressions:

```text
PYTHONPATH=src python3 -m unittest -q \
  tests.test_masking_overlap_review \
  tests.test_package_lifecycle_environment \
  tests.test_policy \
  tests.test_review_fixes
```

Result: 25 tests passed in 4.995 seconds.

- Called `dry_run_command` with bounded synthetic strings to verify FAF-01. No command, shell expansion, external target, account, network, container, or VM was used.

### Supplied but not repeated

- Full 132-test run at `50d283b`: reported passed. That revision predates the final lexical change at `2e4aa2c`, so it is supporting, not exact-final full-suite evidence.
- Exact `2e4aa2c` local/GitHub builds: reported launching; no completed bytes/results inspected.
- Native macOS PR-merge lifecycle passes at `995` and `9fd`: not repeated and not exact final-source artifacts.
- All earlier signed runtime/resource/lifecycle/client evidence: historical for earlier runtime bytes and not relabeled.

## Remaining gates

1. Resolve FAF-01's clustered/PowerShell short-option forms and add focused regressions.
2. Obtain another narrow affected review of that final lexical delta.
3. Run the full suite and wheel build at the actual final source, not only `50d283b`.
4. Build/inspect/checksum/attest and retain exact final local/GitHub artifacts; record source/ref/digests and retrieval. Repeat only behavior/evidence affected by the changed runtime/package bytes.
5. Keep macOS explicitly experimental wheel qualification only; no PKG/signing/support claim.
6. Record owner publication authorization separately. Do not publish stable v1/`latest` based on this review.

No repository file was modified, no artifact was published, no VM/container was started, and no other chat was messaged by this review.

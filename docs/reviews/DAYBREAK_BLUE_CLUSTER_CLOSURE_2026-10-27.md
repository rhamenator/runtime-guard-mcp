# Runtime Guard FAF-01 cluster closure review — 2026-10-27

## Identity and scope

- Repository: `/home/rich/dev/runtime-guard-mcp`
- Reviewed delta only: `2e4aa2c66df72583e638c28e38043c9202fd1065..5987605450d8c2bf9a28e9e05e3812299ff6cea5`
- Exact reviewed source: `5987605450d8c2bf9a28e9e05e3812299ff6cea5`
- Changed files: `src/runtime_guard_mcp/policy.py` and `tests/test_masking_overlap_review.py`
- Read-only snapshot: `/tmp/rg-candidate-5987605-readonly`, created with `git archive` and made non-writable
- Reviewed policy SHA-256: `a91e4f7d9fdb0d89a51f0f1ef11d3d79114d85792677dd7ffd13e4ef48cbd994`
- Requested reviewer configuration: Daybreak Blue (`gpt-daybreak-blue-latest`), `xhigh`
- Observable configuration: exact served model/effort are not exposed inside the session; only a generic GPT-5-based Codex identity is observable. Requested dispatch is recorded but not independently attested.
- Human review: none occurred and none is required under current policy.

This was a narrow classification/source review of FAF-01 only. It did not reopen unchanged runtime behavior, prior reports, the accepted streaming secrecy fix, packaging/platform implementation, or release policy. No inspected command string was executed.

## Verdict

**FAF-01 RESOLVED. READY WITH LIMITATIONS for this affected source delta.**

The exact `5987605` implementation blocks the direct, long-option, Git revision-path, simple short-file, clustered short-file, and quoted PowerShell credential operands in scope. It preserves `SAFE` for the tested benign pattern-file equivalents. I found no new security or classification bypass in the two-file delta.

This is source-level affected-fix acceptance, not artifact certification or publication permission. Exact current artifact builds must bind `5987605450d8c2bf9a28e9e05e3812299ff6cea5`; no newer artifact bytes were supplied or inspected here. Earlier reports and their unrelated findings/limitations remain preserved.

## FAF-01 closure evidence

### Implementation

At `src/runtime_guard_mcp/policy.py:88-97`, the command checker now:

1. strips outer quotes before option recognition;
2. normalizes backslashes to `/`;
3. limits clustered `-f` interpretation to the allow-listed `grep` and `rg` programs;
4. recognizes `f` within a letter-only short-option cluster using `^-[A-Za-z]*?f(.+)$` and treats the consumed suffix as the filename;
5. otherwise preserves the normalized operand;
6. splits operands on `/`, `=`, and `:` and strips component quotes before the existing case-insensitive sensitive-component test.

This directly closes the prior misses:

- `grep -Hf.env target`
- `grep -nf.env target`
- `grep -vf.env target`
- quoted `"-f.env"` / `"-Hf.env"` under PowerShell-like parsing
- equivalent clustered `rg` forms

The prior direct `.env`/`.ssh`, `--file=...`, `HEAD:.env`, and simple `-f.env` cases still block.

### Independently repeated classification matrix

Calls to `dry_run_command` on the exact read-only snapshot returned:

```text
SENSITIVE
bash: grep -Hf.env target         => SENSITIVE_COMMAND_PATH/BLOCKED
sh:   grep -nf.env target         => SENSITIVE_COMMAND_PATH/BLOCKED
pwsh: grep "-vf.env" target      => SENSITIVE_COMMAND_PATH/BLOCKED
bash: rg -Hf.env README.md        => SENSITIVE_COMMAND_PATH/BLOCKED
pwsh: rg "-if.env" README.md     => SENSITIVE_COMMAND_PATH/BLOCKED
bash: grep --file=.env target     => SENSITIVE_COMMAND_PATH/BLOCKED
bash: git show HEAD:.env          => SENSITIVE_COMMAND_PATH/BLOCKED

BENIGN
bash: grep -Hfpatterns.txt target        => READ_ONLY_COMMAND/SAFE
pwsh: grep "-nfpatterns.txt" target     => READ_ONLY_COMMAND/SAFE
sh:   rg -ifpatterns.txt README.md       => READ_ONLY_COMMAND/SAFE
bash: grep --file=patterns.txt target    => READ_ONLY_COMMAND/SAFE
```

These were policy-function calls with synthetic strings. No grep, ripgrep, Git, shell, external target, file operand, or account was invoked.

### Focused tests

The exact snapshot contains 133 test methods. Only the affected five-method module was run:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python3 -m unittest -q tests.test_masking_overlap_review
```

Result: **5 tests passed in 4.605 seconds**.

The test at `tests/test_masking_overlap_review.py:57-63` covers bash, sh, and pwsh; `-f`, `-Hf`, `-nf`, `-vf`, and `-if`; quoted and unquoted `.env`; and benign `patterns.txt` counterparts. The preceding methods preserve the direct/long/revision cases and accepted masking/streaming regressions.

The delegated result of five focused methods in 4.352 seconds is consistent with, but separate from, this repeated run.

## New findings

**None within the reviewed two-file delta.**

## Retained non-blocking limitations

- The option inspection is deliberately conservative, not a complete GNU/clap option parser. A short-option token in which an earlier option actually consumes the remaining characters can be interpreted as containing `-f`, producing a false-positive `BLOCKED` result. That fails safe and does not expose credential content; users can review/rewrite the command.
- The accepted streaming masker can conservatively recognize a signature at a retained-tail boundary after left context has already been emitted. This can over-redact public text or report an extra signature type, but it does not reveal a recognized secret. It is a false-positive limitation, not a secrecy leak.
- Command inspection remains lexical: it performs no variable expansion, alias/config resolution, shell execution, or file opening. `SAFE` remains advisory rather than an execution permission.

## Evidence not repeated

- No broad/full suite was run in this narrow closure review.
- No wheel/sdist was built or inspected.
- Exact `5987605` local/GitHub builds were reported as planned after review; no completed artifact bytes, hashes, reports, or provenance were available here.
- Earlier macOS PR-merge lifecycle runs remain experimental native-environment evidence only and do not establish exact `5987605` artifact identity, PKG/signing, or supported macOS status.
- No external targets, model accounts, network probes, heavy soak, container, or VM were used.

## Remaining gates

1. Run the complete suite and build/inspection workflow at exact `5987605` (or a later explicitly reviewed source if it changes).
2. Bind final local/GitHub wheel and sdist bytes, checksums, inspection reports, source/ref, provenance where applicable, and retrieval evidence to that exact commit.
3. Re-review only behavior affected by any subsequent runtime/package changes.
4. Preserve Linux-only supported scope; experimental macOS wheel results do not add PKG/signing/support claims.
5. Record owner publication authorization separately. Do not treat this affected-source acceptance as stable v1/`latest` permission.

No repository file was modified, no artifact was published, no VM/container was started, and no other chat was messaged by this review.

# Runtime Guard affected-fix review — 2026-10-27

## Identity and scope

- Repository: `/home/rich/dev/runtime-guard-mcp`
- Reviewed delta: `46b7d73e6bc7c62c7d4687e6d5997360e88bc3a6..995931e4a0a00b8df18dce668e49a5f09c04f005`
- Exact reviewed successor: `995931e4a0a00b8df18dce668e49a5f09c04f005`
- Snapshot: detached `git archive` extracted to `/tmp/rg-candidate-995931e-readonly` and made read-only
- Runtime delta: only `src/runtime_guard_mcp/policy.py`
- Reviewed policy SHA-256: `45bb92ced161e6a97eaf7fe87bf582950daf32798566e45bca0f279062240753`
- Requested reviewer configuration: Daybreak Blue (`gpt-daybreak-blue-latest`), `xhigh`
- Observable reviewer configuration: the exact serving-model identifier and effort are not exposed inside the session; only a generic GPT-5-based Codex identity is observable. The requested dispatch therefore cannot be independently attested by the reviewer.
- Human review: none occurred. It is recommended but not required under `docs/RELEASE-READINESS-REVIEW.md:5-17`.

This is an affected-delta review. The archived Daybreak and Claude reports for `46b7d73` remain unchanged. I re-reviewed the changed masking, lexical command-path, package-fixture isolation, experimental macOS workflow, and directly affected claims. I did not reopen unchanged protocol, audit, resource, cancellation, or accepted Linux/stdio scope decisions.

## Verdict

**NOT READY at `995931e4a0a00b8df18dce668e49a5f09c04f005` as the final technical candidate.**

The overlapping-redaction union and 8–256 unquoted-assignment boundary fixes are correct in the reviewed cases, including every tested split and long public prefixes. The isolated package environment and experimental macOS claims are appropriately bounded. However, the lexical credential-path fix is incomplete: real read-file option forms can still be classified `SAFE`. This is a concrete affected Medium finding in a control the successor claims to have fixed. Resolve and re-review it before designating the exact source/artifact candidate.

This verdict does not authorize publication, stable v1/`latest`, or macOS support. The old `2fe9232`, `7b...`, and `af...` artifacts are not evidence of this changed runtime. Exact final artifacts remain a gate after the source fix settles.

## Findings

### AF-01 — Medium — Option-attached credential paths bypass the lexical operand check

**Files/lines**

- `src/runtime_guard_mcp/policy.py:68-109`, especially `88-91` and `98-107`
- `tests/test_masking_overlap_review.py:36-40`
- Affected claim: `README.md:200` and `skills/runtime-guard/SKILL.md:102` (line may vary by renderer; final added paragraph)

**Evidence**

The new check tokenizes the command, strips outer quotes, normalizes backslashes, and splits each token only on `/`:

```python
parts = {part.lower() for token in tokens[1:]
         for part in token.strip("\"'").replace("\\", "/").split("/")}
```

That catches direct components such as `.env`, `./.ssh/id_rsa`, and `$HOME/.ssh/id_rsa`. It does not isolate a relative path attached to an option with `=` or a short option with its argument attached. The subsequent allow-list then classifies the command as read-only and `SAFE`.

Repeated directly on the exact read-only snapshot:

```text
rg --file=.env README.md          => READ_ONLY_COMMAND/SAFE
grep --file=.env target           => READ_ONLY_COMMAND/SAFE
rg --file=.ssh/config README.md   => READ_ONLY_COMMAND/SAFE
grep -f.env target                => READ_ONLY_COMMAND/SAFE
rg --file .env README.md          => SENSITIVE_PATH/BLOCKED
cat ./.ssh/id_rsa                 => SENSITIVE_COMMAND_PATH/BLOCKED
```

`rg`/`grep --file` and `-fFILE` read the named file as pattern input, so the first four are concrete credential-file reads, not speculative shell expansion. No command was executed by this review; only `dry_run_command` was called with synthetic strings.

The new regression covers only standalone path operands (`tests/test_masking_overlap_review.py:36-40`), so it does not expose these option-operand forms.

**Impact**

Runtime Guard remains advisory and never executes the command, but it returns its strongest `SAFE` classification for commands that can read `.env` or `.ssh` content. That contradicts the new “credential-looking command operand components are conservatively blocked” claim and the existing sensitive-path intent.

**Required fix/retest**

- Lexically normalize option operands after separators such as `=` before component comparison.
- Cover attached short read-file options used by allow-listed programs (at minimum `rg`/`grep -fFILE`) or conservatively downgrade such unparsed forms rather than returning `SAFE`.
- Add focused positive/negative regressions for quoted and unquoted `--file=.env`, `--file=.ssh/config`, `-f.env`, normal non-sensitive option values, and direct operands.
- Do not add shell expansion or command execution; the fix can remain purely lexical.

**Confidence:** High.

### AF-02 — Low — The prior human-review policy wording cleanup remains incomplete

**Files/lines**

- `README.md:190`
- `skills/runtime-guard/SKILL.md:83`
- Governing policy: `docs/RELEASE-READINESS-REVIEW.md:5-17`

**Evidence**

The delta correctly replaces most stale mandatory-human-review language with adversarial LLM review plus owner publication authorization. Two active statements remain:

- README says package identity checks do not replace “provenance and human review.”
- The shipped companion skill says the portability limitation has a “required human release disposition.”

The governing policy says independent human technical review is recommended, not required, and must not be implied as a hard gate. These are active instructions, not immutable historical reports.

**Impact**

This does not weaken runtime behavior, but leaves release-gate claims internally inconsistent and only partially resolves the earlier documentation finding.

**Required fix:** use the already adopted wording: adversarial LLM technical review, disclosure that no independent human review occurred, and separate owner publication authorization. Human review may remain described as recommended.

**Confidence:** High.

## Accepted affected fixes

### Overlapping redaction spans — accepted

`SecretMasker._matches` (`src/runtime_guard_mcp/policy.py:210-224`) sorts recognized spans and replaces the transitive union of overlapping matches. It preserves all detected signature types while using one stable placeholder for the union. The same union computation is used when selecting the streaming cutoff (`policy.py:286-300`), so a recognized extending overlap is not emitted from the prefix before the tail is retained.

The new test covers email/assignment and OpenAI-key/assignment overlaps, empty and 21,000-character public prefixes, every split point, absence of the synthetic assignment suffix, reported assignment type, and stable replacement across streams (`tests/test_masking_overlap_review.py:21-34`). The repeated focused run passed.

### Unquoted assignment boundary — accepted

The new terminal lookahead at `src/runtime_guard_mcp/policy.py:193` requires whitespace, quote, or end after an unquoted 8–256-unit value. Continuous 257+ unit values can no longer be mislabeled by masking only the first 256 units. The regression exercises lengths 255, 256, 257, and 600 at every split with a 21,000-character public prefix (`tests/test_masking_overlap_review.py:6-19`). The repeated run passed.

This remains signature-based masking. Values outside the documented bound remain visible unless another complete recognized signature applies; the README and skill disclose that limitation.

### Isolated lifecycle environment — accepted for its stated purpose

`scripts/package_lifecycle_review.py:29-40` now rebuilds a narrow subprocess environment, fixes `PATH` to the active interpreter directory plus system bins, redirects HOME/XDG paths, disables pip indexes/cache/config, and drops inherited shell hooks, Python/runtime overrides, package install targets, Rustup, and Cargo state. The loader/locale/temp/platform variables it retains are explicit. The environment regression confirms the intended removals (`tests/test_package_lifecycle_environment.py:14-33`).

This is fixture isolation on trusted disposable runners, not a hostile-environment sandbox. Retaining loader paths and temp variables is acceptable under that claim. The lifecycle script still performs no network access after wheels are staged.

### Experimental macOS workflow — claim-consistent, result pending

The workflow uses `pull_request`/manual dispatch, read-only repository permission, pinned GitHub actions, a hosted `macos-latest` runner, Python 3.13, committed-source wheel binding, the synthetic lower-version fixture, native venv install/launch/upgrade/uninstall/residue checks, checksums, and 90-day hosted artifact retention.

`docs/MACOS_PACKAGE_QUALIFICATION.md:3-9`, `README.md:198`, and the recorded environment scope consistently say:

- experimental hosted wheel qualification only;
- no PKG/DMG, Apple signing/notarization, desktop UI, every-version/architecture, or supported-platform certification;
- no provenance attestation equivalent to the signed Linux workflow;
- Linux remains the only accepted platform; Windows remains excluded.

No completed native rerun result was supplied to this review; it was reported as still running. I therefore accept the workflow/source claims but do not record macOS lifecycle as passed. Adding `scripts/inspect_wheel.py` (and optionally `LICENSE`/`NOTICE`) to the PR `paths` filter would improve automatic rerun coverage for direct workflow inputs; manual dispatch and the experimental status make this a non-blocking CI-hardening note.

## Tests and evidence

### Repeated independently

- Resolved exact `995931e4a0a00b8df18dce668e49a5f09c04f005` and reviewed from a detached read-only snapshot.
- Inspected every changed file and confirmed only `policy.py` changed under `src/runtime_guard_mcp/`.
- Counted 131 test methods in the exact candidate snapshot.
- Ran:

```text
PYTHONPATH=src python3 -m unittest -q \
  tests.test_masking_overlap_review \
  tests.test_package_lifecycle_environment \
  tests.test_policy
```

Result: 18 tests passed in 4.984 seconds.

- Ran `tests.test_review_fixes`: 6 tests passed in 0.658 seconds.
- Total focused repeated set: 24 tests, all passed.
- Called `dry_run_command` on six bounded synthetic strings to validate AF-01; no command execution, external target, account, network, container, or VM was involved.

### Supplied, not repeated

- Full 131-test result: reported passed in 16.64 seconds.
- Wheel build: reported passed in 2.04 seconds.
- Native macOS CI: reported rerunning; no success result treated as evidence.
- Earlier signed wheel/resource/lifecycle/native-client evidence: historical for prior runtime source only. Because `policy.py` changed, no prior artifact is relabeled as exact `995931e` evidence.

## Remaining gates

1. Fix AF-01 and add the focused option-operand regressions; obtain another affected re-review.
2. Correct AF-02's two remaining active policy statements.
3. Complete and record relevant Linux CI plus the experimental macOS run without expanding the supported-platform claim.
4. After the source settles, build local and GitHub artifacts from the exact final commit; bind source/ref, wheel/sdist hashes, inspections, tests, provenance where applicable, and retrieval records. Repeat only evidence affected by the runtime/package changes.
5. Record owner publication authorization separately. Do not publish stable v1/`latest` or claim macOS support from this experimental workflow.

No repository file was modified, no artifact was published, no VM/container was started, and no other chat was messaged by this review.

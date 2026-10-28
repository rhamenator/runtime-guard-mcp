# Review-artifact provenance

The tag/manual `Release artifacts` job produces review packages, not a stable GitHub/PyPI release. After source/wheel inspection, packaged tests, installed probes and checksum verification, the pinned GitHub `actions/attest` action signs build provenance for the five subjects listed in SHA256SUMS: wheel, source archive and three inspection/API reports. The signing job alone gets `id-token: write` and `attestations: write`; ordinary PR CI keeps read-only permissions. No registry push or artifact-storage record is requested.

The uploaded `provenance.jsonl` bundle contains the signatures; it is not included in its own subject list. GitHub's public-repository Sigstore infrastructure and GitHub Actions workflow identity are part of the trust model. Signing does not prove source correctness, a reproducible build, complete tests or independent review. A branch workflow can produce valid signed **review** artifacts; that does not authorize stable use. This change creates no stable tag or release.

## Verify downloaded artifacts

Obtain the expected source commit and Git ref from the reviewed candidate record through a trusted channel. Do not accept an arbitrary branch or derive the expected values solely from the downloaded bundle. With a GitHub CLI supporting these flags (verified on the hosted packaging runner; older 2.46.0 lacks the attestation command):

```sh
sha256sum --check SHA256SUMS
gh attestation verify runtime_guard_mcp-0.1.0-py3-none-any.whl \
  --bundle provenance.jsonl --repo rhamenator/runtime-guard-mcp \
  --signer-workflow rhamenator/runtime-guard-mcp/.github/workflows/release.yml \
  --source-digest EXPECTED_COMMIT --source-ref EXPECTED_GIT_REF \
  --deny-self-hosted-runners
```

Repeat signature verification for the source archive and three JSON subjects listed in SHA256SUMS. Checksums alone are consistency checks. The verifier must require the repository, signer workflow, source commit and ref; trusting just any signature from the owner is insufficient for a designated candidate. The default verifier predicate is SLSA provenance v1. Verification may need network access for trust material; no offline availability guarantee is made.

GitHub provenance is separate from the independent human release-readiness record, final native-client/platform scope and residual-risk acceptance. Normal installed-server users do not require signing tooling, write tokens or additional runtime packages.

The packaging job first verifies all five genuine subjects, then requires rejection of the wrong source commit, wrong ref, wrong signing workflow and a byte-modified wheel. A trust-root/network initialization failure must block verification; it is not an artifact-integrity verdict and must not be bypassed by disabling identity or signature checks.

## Resolver-related initialization failures

A local replay on 2026-10-24 isolated the earlier `no valid Sigstore verifiers could be initialized` result to DNS transport: the static Go CLI attempted direct DNS to `8.8.8.8:53` and timed out, while the host's native resolver successfully resolved both TUF repositories. This is an observed environment difference, not proof of a broken artifact or account quota. CLI diagnostics were enabled with `GH_DEBUG=1 GH_FORCE_TTY=80` under a bounded timeout; the relevant error was `lookup tuf-repo-cdn.sigstore.dev ... i/o timeout`.

Using a per-invocation `HTTPS_PROXY` pointing to a temporary loopback CONNECT relay with native DNS unblocked verification. The relay accepted only `tuf-repo-cdn.sigstore.dev:443` and `tuf-repo.github.com:443`; TLS remained end to end. No custom trust root, disabled certificate verification, relaxed identity flag, global DNS/cache modification or installed-server change was used. The temporary relay was shut down after the replay.

With CLI 2.103.2, all five downloaded subjects verified locally against the expected review commit/ref/workflow, and all four wrong-identity/modified-byte controls rejected. [Evidence](evidence/local-provenance-verification-2026-10-24.json) records the exact review artifact identities and scope. This resolves the earlier unexplained local verification result for that bundle; it is not a permanent host DNS repair, offline guarantee or stable-release approval. Other environments should diagnose their own resolver/trust failure and use an approved HTTPS proxy or a working verifier host while retaining all signature/identity checks. See the [CLI's TUF configuration](https://github.com/cli/cli/blob/v2.103.2/pkg/cmd/attestation/verification/tuf.go) for cache/transport behavior.

## Review retention and archival handoff

New review-artifact uploads request 90-day retention explicitly. This is a finite GitHub retention request, subject to repository/organization policy; it does not retroactively extend older runs or provide permanent availability. Do not designate a final candidate whose required package/report bundle has expired. Before release review, download the exact named run artifact, verify all SHA256SUMS subjects and provenance identities, and preserve the complete verified directory (packages, inspection/API reports, checksums and provenance.jsonl) in the owner's controlled backup/archive. Record the run, source/ref, wheel and bundle hashes, archive owner/location and an actual retrieval check in the human review record; keep credentials and private local archive paths out of the public repository. A source archive or checksum list alone cannot replace the signed package/report bundle. This policy does not publish a stable release or establish backup durability.

## Repeatable retrieval integrity check

After the original signing/identity verification is recorded, check a retrieved copy against the independently trusted, reviewed repository inventory:

```sh
python3 scripts/verify_review_bundle.py \
  docs/evidence/review-baseline-2026-10-27.json /path/to/retrieved-bundle
```

This Linux development helper requires exactly the seven recorded package/report/checksum/provenance members, checks all their recorded SHA-256 values and rejects missing/extra members, unsafe inventory names, duplicate JSON keys, symlinks, nonregular members and files over 32 MiB. It does not extract or execute bundle contents. Obtain the expected inventory from a trusted reviewed repository revision, not from the downloaded bundle itself. This is byte-retrieval verification, not new signature verification or publisher authentication; retain the signature/commit/ref/workflow checks above for initial acceptance.

On 2026-10-27 the full build `40595971974` bundle was downloaded again after a host restart removed temporary files. All seven digests matched the trusted `2fe9232` inventory, including the previously verified provenance bundle. A copy was preserved in the owner's local account archive and checked again; [retrieval evidence](evidence/review-bundle-retrieval-2026-10-27.json) omits the private path. This supplies a reproducible local retrieval check, not a second-device backup, permanent retention, owner custody acceptance or final release approval. The owner must still choose retention, backup/custody and recovery requirements. No live audit database was copied or rotated.

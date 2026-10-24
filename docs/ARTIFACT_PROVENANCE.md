# Review-artifact provenance

The tag/manual `Release artifacts` job produces review packages, not a stable GitHub/PyPI release. After source/wheel inspection, packaged tests, installed probes and checksum verification, the pinned GitHub `actions/attest` action signs build provenance for the five subjects listed in SHA256SUMS: wheel, source archive and three inspection/API reports. The signing job alone gets `id-token: write` and `attestations: write`; ordinary PR CI keeps read-only permissions. No registry push or artifact-storage record is requested.

The uploaded `provenance.jsonl` bundle contains the signatures; it is not included in its own subject list. GitHub's public-repository Sigstore infrastructure and GitHub Actions workflow identity are part of the trust model. Signing does not prove source correctness, a reproducible build, complete tests or independent review. A branch workflow can produce valid signed **review** artifacts; that does not authorize stable use. This change creates no stable tag or release.

## Verify downloaded artifacts

Obtain the expected source commit and Git ref from the reviewed candidate record through a trusted channel. Do not accept an arbitrary branch or derive the expected values solely from the downloaded bundle. With a GitHub CLI supporting these flags (tested with 2.103.2; 2.46.0 lacks the attestation command):

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

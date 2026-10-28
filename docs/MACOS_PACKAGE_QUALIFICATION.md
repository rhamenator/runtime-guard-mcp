# Experimental macOS package qualification

The owner authorized GitHub-hosted macOS installer/installation scenarios to the extent practicable. The pull-request and manually dispatched `Experimental macOS package review` workflow builds the same committed source on a disposable `macos-latest` runner with Python 3.13. It uses a recognized Python wheel package and records the actual OS/CPU/Python; it does not build or claim a native PKG/DMG installer.

The workflow binds the candidate wheel to the Git revision, builds a clearly synthetic lower-version fixture, and runs native clean install, MCP launch/call, pip upgrade, launch, uninstall and file-residue checks. A user-owned marker outside the install prefix must survive. The platform-independent lifecycle helper is shared with Linux CI; no Linux procfs or container approximation is used for this macOS job.

Artifacts, environment, inspection, lifecycle results and checksums are retained on GitHub for a requested 90 days, subject to policy. macOS Python is a prerequisite, not bundled in the wheel. Hosted artifacts have no commercial Apple signing/notarization; checksums are consistency records and the inspection binds payload to source, not Apple identity. This workflow currently supplies no provenance attestation; do not equate it with the signed Linux review workflow.

This is an experimental qualification path, not an expansion of the accepted Linux support matrix. A successful run covers its actual hosted environment only. It does not certify every macOS version/architecture, desktop UI, PKG installation, Gatekeeper/notarization, user database migration or system-service integration. Any future supported macOS claim needs scoped evidence, documentation and affected adversarial review first. Windows remains excluded. Do not publish stable v1/latest.

Pull-request builds identify GitHub's temporary merge revision/ref, not the PR head. Treat that recorded identity literally; an exact branch-candidate artifact requires a manual run once the workflow exists on the default branch. A successful PR job is native environment evidence, not an attestation for a differently identified branch commit.

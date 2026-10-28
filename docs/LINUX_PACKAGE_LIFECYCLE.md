# Disposable Linux wheel lifecycle

Runtime Guard's initial supported scope is Linux with Python 3.11–3.14 and a recognized Python wheel, installed into a dedicated virtual environment. It does not claim a desktop service, native Windows/macOS installer or every Linux distribution. Installer signing/notarization on commercial platforms remains deferred; those platforms are not claimed here.

## Recorded run

The [machine-readable result](evidence/linux-package-lifecycle-2026-10-27.json) records a disposable Debian/Python 3.13 container run against the signed review wheel from workflow [40595971974](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/40595971974), source `2fe923267dd6648b999b94e3f58a1ed600625943`. This remains review material, not an approved official candidate. Its wheel SHA-256 is `625472727e2bc950d3d7a6400f28e8aba10b3cc433ff330b4c0ffdab9ce808b5`.

The container had no network, a read-only root and input mounts, disposable executable tmpfs, two CPUs, 768 MiB memory and a 96-process limit. It was automatically removed after execution. No host environment, system package, user configuration or existing audit database was changed. An initial noexec tmpfs prevented virtual-environment Python from launching; rerunning with executable disposable tmpfs corrected the test setup, without weakening the application's permissions.

The probe checks:

1. Clean wheel installation without dependencies, metadata/version, `pip check`, installed entry point and real MCP initialization/discovery/advisory call.
2. Uninstall after clean install: environment file hashes return exactly to baseline.
3. Installation and launch of a synthetic `0.0.0` fixture, then pip `--upgrade` to the actual `0.1.0` candidate and launch again. Only one package metadata directory remains.
4. Final uninstall: console command, importable module, metadata and all added environment files are gone; baseline file bytes are unchanged.
5. A user-owned configuration marker outside the install prefix survives unchanged. User data is intentionally not part of package uninstall; delete the dedicated environment separately when retiring it.

The lower-version fixture uses the reviewed source with only the package version changed. It is not a prior published release. This tests distinct-version package replacement, not historical configuration/database migration. The marker check does not certify audit database migration. Empty directories, distribution-specific system integration, power loss, read-only home and arbitrary pip/Python combinations are outside this test.

## Reproduction and ongoing CI

`package_lifecycle_review.py LOWER_FIXTURE.whl CANDIDATE.whl` creates and removes its own temporary virtual environment and isolated home, disables pip indexes/cache, verifies the package's lack of runtime dependencies and runs subprocesses with bounded timeouts. Stage only trusted/inspected wheels. Run on Linux with Python and bundled venv/pip support.

The CI workflow copies its clean committed source archive, changes only the fixture version to `0.0.0`, builds that fixture wheel, and invokes the probe against the inspected candidate wheel. It runs on each advertised Python version. This is automated Linux package evidence, not a certification for excluded platforms. The container result records the exact image digest; a newer image is a new environment requiring a new recorded run.

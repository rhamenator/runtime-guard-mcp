# Installed scanner replay, 2026-10-23

The machine-readable [evidence](evidence/installed-scanner-replay-2026-10-23.json) records a bounded replay against source commit `bd56ecae8f26f6b9b4cc9ef32db11d1fbaf6681f`. Build a clean clone's source distribution with setuptools, inspect it against that commit, build its wheel with `python -m pip wheel --no-deps ARCHIVE -w OUTPUT`, inspect the wheel, and install it in a fresh venv without dependencies. Then run from the development checkout:

```sh
python scripts/wfuzz_loopback_review.py --server /path/to/venv/bin/runtime-guard-mcp
PYTHONPATH=src python scripts/live_adversarial_test.py --server /path/to/venv/bin/runtime-guard-mcp
```

Development requirements are Python 3.11+, Git, setuptools/wheel, Wfuzz and Nmap. Installed server runtime requirements remain empty. Both probes create their own temporary workspace, audit store and ephemeral loopback server; they do not accept an external target. Tokens and synthetic secret state are temporary, and saved reports omit the generated bearer value. No VM or model-account interaction is involved.

Wfuzz 3.1.0 completed 21 scanner requests plus its policy, saturation, redaction and audit-recovery fixtures. The separate API campaign completed 68 checks, including an actual Nmap 7.98 loopback port probe. Reports include observed resources and recovery, not throughput guarantees. The full 107-test suite also passed. The evidence JSON carries actual durations, artifact checksums and probe identities.

This is same-host Linux evidence for a finite corpus. It does not prove all injection detection, cross-user isolation, native coding-client cancellation, Internet/TLS deployment, hours-long load stability or independent review. It is tied to the stated artifact rather than any future stable tag. A final candidate still requires coordinated native-client/resource/package replay and human acceptance of the documented protocol/state/cancellation limits.

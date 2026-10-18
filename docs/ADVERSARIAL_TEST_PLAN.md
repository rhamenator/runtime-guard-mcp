# Bounded adversarial test plan

Purpose: exercise Runtime Guard's advisory boundary with synthetic data. The command strings below are inputs to `dry_run_command`; **do not execute them**. No real credential, private file, network target, or production service is required.

## Host baseline

Run from a fresh checkout on each test host:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

The suite creates temporary directories, a local SQLite file, and a short-lived loopback HTTP process. It makes no external network requests. Record Python version, operating system, commit SHA, pass/fail count, peak RSS, and any warnings. On Kali and the Ubuntu VM, run the same command separately; no shared mutable state is needed. Keep the Kali VM powered down outside the test window.

## Cases and expected results

| Area | Synthetic input | Expected |
| --- | --- | --- |
| Path | `../../etc/shadow`, `.env.production`, symlink to outside a temporary root | `BLOCKED` |
| Shell | `find . -delete`, `find . -exec ...`, `cat /proc/self/environ`, `cat ~/.config/gcloud/...` | never `SAFE`; sensitive reads `BLOCKED` |
| Shell | `rm -rf /tmp/example`, `git push --force`, `Remove-Item -Recurse` | `BLOCKED` |
| Budget | 64 concurrent one-token reservations against a ten-token limit | exactly ten `SAFE`, 54 `BLOCKED` within one process |
| Masker | synthetic `ghp_` token split one character per chunk | no raw token emitted; one stable placeholder |
| Protocol | malformed JSON-RPC shapes, invalid ID types, bad tool arguments | controlled JSON-RPC error; no crash |
| Audit | modify or delete an interior SQLite row | `verify_integrity()` reports invalid |

## Manual transport probes

Use an MCP SDK or Inspector on each host to initialize, list four tools, and call `dry_run_command` with `git status`. Repeat over stdio and loopback HTTP. Test hostile `Origin` and `Host` headers against the HTTP endpoint; expect HTTP 403. Do not bind the server outside loopback for this plan.

For cross-VM tests, keep Runtime Guard bound to `127.0.0.1:8765` on Ubuntu. Create an SSH local port forward from Kali to Ubuntu's loopback port, then run `python3 scripts/adversarial_probe.py` on Kali against `http://127.0.0.1:8765/mcp`. The probe uses only the standard library and prints pass/fail labels without response bodies or synthetic token values. For the optional concurrency check, launch a fresh Ubuntu server with `token_hour` set to 10 and run `python3 scripts/adversarial_probe.py --budget-limit 10`; stop that server after the run. Keep the tunnel and VM lifecycle under the test coordinator's control.

## Exit criteria and limits

All tests must pass on both hosts with no crashes, leaked synthetic tokens, unexpected disk growth, or thread accumulation. The suite is an advisory-policy test, not proof that another shell or filesystem tool is contained. The current server still needs MCP 2026-07-28 protocol work and client-specific Codex, Claude Code, and Cursor validation before a stable release.

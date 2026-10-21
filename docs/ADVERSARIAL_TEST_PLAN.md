# Bounded adversarial test plan

Purpose: exercise Runtime Guard's advisory boundary with synthetic data. The command strings below are inputs to `dry_run_command`; **do not execute them**. No real credential, private file, network target, or production service is required.

## Host baseline

Run from a fresh checkout on each test host:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

The suite creates temporary directories, a local SQLite file, and a short-lived loopback HTTP process. It makes no external network requests. Record Python version, operating system, commit SHA, pass/fail count, peak RSS, and any warnings. On Kali and the Ubuntu VM, run the same command separately; no shared mutable state is needed. Keep the Kali VM powered down outside the test window.

Run the actual HTTP MCP boundary probe from the repository root:

```bash
PYTHONPATH=src python3 scripts/live_adversarial_test.py
```

It launches its own authenticated server on a random `127.0.0.1` port, sends fewer than 250 synthetic requests, opens at most 32 temporary slow connections, and removes its temporary workspace and audit database. One additional authenticated connection drips a partial body for at most six seconds to verify the absolute connection deadline and recovery. It also starts one stdio child to send an oversized line followed by a valid MCP request and checks that framing recovers. If Nmap is installed, it scans only the ephemeral loopback port with `nmap -sT -Pn -p PORT 127.0.0.1`. The script reports pass/fail labels and never prints the generated bearer token or synthetic secret. The core checks run in CI on Python 3.11 and 3.13; the optional Nmap check is recorded separately when available.

The HTTP probe also sends duplicate JSON keys, non-finite values, numeric overflow, invalid UTF-8, a frame exceeding the 64-level nesting cap, and a wide array exceeding the 8192-marker structure cap under valid authentication. Each must return `-32700`, followed by a successful `ping`. The stdio subprocess tests cover the same malformed frames and recovery.

For a bounded installed-package scan with Wfuzz 3.1.0 available on the host, install a fresh wheel into a virtual environment and run `python3 scripts/wfuzz_loopback_review.py --server /path/to/venv/bin/runtime-guard-mcp`. The script creates its own authenticated loopback target and temporary files, sends eighteen serial POSTs across known paths, bearer values, Origin and Host authorities, and malformed JSON-RPC bodies, then checks recovery. Each body result is cross-checked with a direct structured response from the same installed server. After scanning, the script opens at most 32 partial-header loopback connections, expects one excess request to return 503, completes all 32 held requests and requires successful ping responses, closes the sockets, and expects a 200 recovery. It also submits three command strings against disposable files: an instruction-like recursive deletion and a sensitive-file read must be `BLOCKED`, while `find -delete` must require confirmation; the fixtures must remain unchanged. It then streams a synthetic GitHub-shaped token one character at a time to the installed `secret_masker`, checks the redacted output and temporary SQLite database and sidecar bytes, then changes one row in its temporary audit database and requires the installed tool to return `BLOCKED` / `AUDIT_UNAVAILABLE` without adding a decision, then checks that `ping` still works. It prints status summaries without the generated token. This optional toolset check is separate from CI and does not scan external hosts.

## Cases and expected results

| Area | Synthetic input | Expected |
| --- | --- | --- |
| Path | `../../etc/shadow`, `.env.production`, symlink to outside a temporary root | `BLOCKED` |
| Shell | `find . -delete`, `find . -exec ...`, `cat /proc/self/environ`, `cat ~/.config/gcloud/...` | never `SAFE`; sensitive reads `BLOCKED` |
| Shell | `rm -rf /tmp/example`, `git push --force`, `Remove-Item -Recurse` | `BLOCKED` |
| Budget | 64 concurrent one-token reservations against a ten-token limit | exactly ten `SAFE`, 54 `BLOCKED` within one process |
| Masker | synthetic `ghp_` token split one character per chunk | no raw token emitted; one stable placeholder |
| Protocol | malformed JSON-RPC shapes, invalid ID types, bad tool arguments | controlled JSON-RPC error; no crash |
| HTTP framing | duplicate security/body headers, transfer encoding, non-JSON POST | 400 or 415; next valid request still works |
| Audit | modify or delete a SQLite row; close or fail the audit store | startup or append refuses corruption; tool result is `BLOCKED` without computed content |

## Manual transport probes

Use an MCP SDK or Inspector on each host to initialize, list four tools, and call `dry_run_command` with `git status`. Repeat over stdio and loopback HTTP. Test hostile `Origin` and `Host` headers against the HTTP endpoint; expect HTTP 403. Do not bind the server outside loopback for this plan.

For cross-VM tests, keep Runtime Guard bound to `127.0.0.1:8765` on Ubuntu. Create an SSH local port forward from Kali to Ubuntu's loopback port, then run `python3 scripts/adversarial_probe.py` on Kali against `http://127.0.0.1:8765/mcp`. If the endpoint uses bearer authentication, set `RUNTIME_GUARD_PROBE_TOKEN` in the probe process environment to the same lab token; keep its value out of command logs. The probe uses only the standard library and prints pass/fail labels without response bodies or synthetic token values. For the optional concurrency check, launch a fresh Ubuntu server with `token_hour` set to 10 and run `python3 scripts/adversarial_probe.py --budget-limit 10`; stop that server after the run. Keep the tunnel and VM lifecycle under the test coordinator's control.

## Exit criteria and limits

All tests must pass on both hosts with no crashes, leaked synthetic tokens, unexpected disk growth, or thread accumulation. The live probe is a principal release gate, and its evidence must be reviewed with authorized pentesting-toolset results and residual risks. It is an advisory-policy test, not proof that another shell or filesystem tool is contained. The current server still needs MCP 2026-07-28 protocol work and client-specific Codex, Claude Code, and Cursor validation before a stable release.

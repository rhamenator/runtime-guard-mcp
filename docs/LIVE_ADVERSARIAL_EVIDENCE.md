# Live HTTP adversarial evidence

## Host run, 2026-10-18

Target: an ephemeral Runtime Guard child process bound to `127.0.0.1` with a generated bearer token, a temporary workspace, a ten-token hourly budget, and a temporary SQLite audit file. No third-party server, real secret, or external network target was used. The host run exercised the content committed as `17bf19ccf8aec23238fb33b0324ad3d9435b1aa7` in [PR #13](https://github.com/rhamenator/runtime-guard-mcp/pull/13), merged to main as `a1fcb28c4bb18ff462bcf7bad00e0ca735c009b4`. The base revision was `7a73ef8`.

Commands from the repository root:

```bash
PYTHONPATH=src python3 scripts/live_adversarial_test.py
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/runtime-guard-wheel-check
```

The script optionally ran Nmap 7.98 with `nmap -sT -Pn -p PORT 127.0.0.1`, where `PORT` was the child server's ephemeral loopback port. Host Python was 3.14.4 on Linux. It generated and discarded all authentication and secret fixtures.

The merged revision's [CI run](https://github.com/rhamenator/runtime-guard-mcp/actions/runs/39168504699) passed the unit suite, live HTTP probe, and package build on Python 3.11 and 3.13. Nmap is optional in CI, so the host's scanner result below is the recorded scanner evidence.

| Area | Live result |
| --- | --- |
| Authentication | Missing and wrong bearer returned 401; authenticated initialization and four-tool discovery returned 200. |
| Browser-origin boundaries | Spoofed `Host` and hostile `Origin` each returned 403. |
| Local scanner | Nmap reported the one selected loopback TCP port open while the server was healthy. |
| Malformed protocol | Invalid JSON returned `-32700`; boolean ID `-32600`; wrong argument type `-32602`; unknown method `-32601`; body over 1 MiB returned HTTP 413. |
| Injection-like inputs | Sensitive `/proc` read, destructive `find`, and instruction-like shell text with `rm -rf /` all returned `BLOCKED`. The server did not execute them. |
| Secret exposure | A synthetic GitHub-shaped token sent one character at a time never appeared raw in collected tool output; one stable placeholder appeared. The raw synthetic token was absent from the temporary audit database bytes. |
| Resource pressure and recovery | 32 partial-header connections occupied the configured handler cap; an extra request got 503; after closing them, a normal authenticated request returned 200. |

The final local run reported **19 PASS checks**. The first draft of the probe recorded one Nmap check failure when scanning immediately after releasing the saturated sockets. Moving the port scan ahead of the saturation case removed that measurement race; three consecutive repeated runs and the final run passed. This was a harness ordering issue, not evidence that the server remained unavailable; the HTTP recovery check had returned 200. The initial failure is retained here so the record does not overstate repeatability.

## Limits and release decision

This is a bounded host-side protocol/API test. It does not prove full MCP 2026-07-28 conformance, TLS deployment, per-client isolation, resistance to sustained flooding, or containment of agent actions through other tools. Nmap scanned one authorized loopback port; it was not a broad vulnerability scan. A separate authorized pentesting-toolset review, fresh client probes, resource measurements, and human review remain required before a stable release.

## Masker state follow-up, 2026-10-18

The live probe was extended to open 128 unfinished `secret_masker` streams through the authenticated HTTP API. A 129th stream returned `BLOCKED` / `STREAM_LIMIT`; finishing one stream allowed a new one to return `SAFE`. The final host run of `PYTHONPATH=src python3 scripts/live_adversarial_test.py` reported **21 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused policy tests also verified the 4096-secret mapping limit using a smaller configured test limit, blocked-stream reset, and controlled rejection of malformed Unicode. These bounds do not replace a sustained memory and CPU profile.

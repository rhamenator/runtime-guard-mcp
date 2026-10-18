# Live HTTP adversarial evidence

## Host run, 2026-10-18

Target: an ephemeral Runtime Guard child process bound to `127.0.0.1` with a generated bearer token, a temporary workspace, a ten-token hourly budget, and a temporary SQLite audit file. No third-party server, real secret, or external network target was used. Base revision before the probe change: `7a73ef8`; the probe and this record are reviewed together in the linked PR.

Commands from the repository root:

```bash
PYTHONPATH=src python3 scripts/live_adversarial_test.py
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/runtime-guard-wheel-check
```

The script optionally ran Nmap 7.98 with `nmap -sT -Pn -p PORT 127.0.0.1`, where `PORT` was the child server's ephemeral loopback port. Host Python was 3.14.4 on Linux. It generated and discarded all authentication and secret fixtures.

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

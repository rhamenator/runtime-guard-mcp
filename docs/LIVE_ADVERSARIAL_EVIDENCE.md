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

## Budget state follow-up, 2026-10-18

The live HTTP probe sent 12 one-token reservations against a fresh server configured with a ten-token hourly budget. It observed ten `SAFE` and two `BLOCKED` decisions, then completed the other adversarial cases for **22 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused tests used lower internal state caps to verify that reservation and fingerprint histories fail closed, concurrent reservations remain atomic, and expired records release capacity. The default 8192/4096 record caps were not saturated in the live run; sustained resource profiling remains open.

## Stdio framing follow-up, 2026-10-18

The live probe now starts an additional stdio server process and sends a synthetic line twice the 1 MiB request cap followed by a valid `ping`. It observes one controlled `-32600` error and one successful response with the expected request ID, for **23 PASS checks** overall on Python 3.14.4 with Nmap 7.98. A focused subprocess test sends a line three times the cap and verifies the same recovery. This bounds memory used to frame a line; it does not measure peak RSS under sustained input.

## HTTP framing follow-up, 2026-10-18

The authenticated loopback probe sent duplicate Content-Length, Host, Authorization, and Content-Type headers, a Transfer-Encoding/Content-Length combination, a non-JSON media type, malformed Host port, and invalid Origin scheme. The server returned controlled 400 or 415 responses, then accepted a valid `ping`. The full probe reported **32 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused HTTP-process tests also cover duplicate Origin and very long Content-Length fields. This hardens the legacy JSON-RPC-over-HTTP endpoint; it does not establish MCP 2026-07-28 Streamable HTTP conformance.

## Audit failure follow-up, 2026-10-18

After the normal authenticated HTTP probes, the harness changed the final row of its temporary SQLite audit database and called `dry_run_command`. The server returned `BLOCKED` / `AUDIT_UNAVAILABLE` and did not append another decision, for **33 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused tests also confirm that a tampered database refuses restart and a closed audit connection returns a blocked tool result without the computed content. This detects direct row mutation; deletion of the final row still needs an external anchor, and deliberate recomputation of unkeyed hashes remains outside this guarantee.

## HTTP slow-drip follow-up, 2026-10-19

The authenticated loopback probe held one partial JSON request open and sent body bytes every 150 milliseconds, faster than the five-second inactivity timeout. The server closed that connection at its five-second absolute deadline and accepted a fresh authenticated `ping` afterward. The full run reported **35 PASS checks** on Python 3.14.4 with Nmap 7.98. A focused one-slot test also verified that a handler becomes available after the deadline while bytes continue arriving. This is a bounded single-connection result, not a sustained flooding or proxy test; slow legitimate uploads can hit the same deadline.

## Strict JSON wire follow-up, 2026-10-19

The authenticated loopback probe sent `NaN`, duplicate top-level and nested keys, an overflowing `1e999` number, and invalid UTF-8. Each returned JSON-RPC `-32700`; a subsequent valid `ping` succeeded. The full run reported **41 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused stdio and HTTP process tests also rejected those frames and verified recovery. This closes parser ambiguity for these cases; it is not a complete JSON-RPC or MCP conformance certification.

## JSON nesting follow-up, 2026-10-19

The authenticated loopback probe sent a 65-level nested array within the request-size cap. It returned JSON-RPC `-32700` and the next valid `ping` succeeded, for **42 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused tests checked the 64-level boundary and brackets inside quoted strings, plus stdio and HTTP recovery. This bounds nesting before object construction but does not by itself cap all memory growth from wide JSON objects.

## JSON width follow-up, 2026-10-19

The authenticated loopback probe sent an array of 8193 zero values, occupying roughly 16 KiB on the wire but exceeding the 8192 structural-marker cap. It returned JSON-RPC `-32700`; the next valid request succeeded. The full run reported **43 PASS checks** on Python 3.14.4 with Nmap 7.98. Focused tests verified the limit boundary, quoted commas, and stdio/HTTP recovery. Large strings remain possible under the one-megabyte frame cap; the cap bounds container count rather than total memory in all cases.

## Installed HTTP boundary Wfuzz review, 2026-10-19

A bounded host-side Wfuzz 3.1.0 run tested an installed `runtime-guard-mcp` entry point rather than a source-tree import. The review script started a child server on an ephemeral `127.0.0.1` port with a generated bearer token, temporary workspace, and temporary audit database. It sent six serial POST requests (`-t 1`, two-second per-request timeout) across four paths and two bearer values, then checked recovery with a valid `ping`. No external target, real credential, or VM was involved.

Reproduce after installing a wheel into a clean virtual environment:

```bash
python3 scripts/wfuzz_loopback_review.py --server /path/to/venv/bin/runtime-guard-mcp
```

Observed statuses: `/mcp` 200; `/admin`, `/metrics`, and `/.env` 404; invalid bearer 401; generated valid bearer 200; post-scan `ping` 200. Wfuzz reported a local Pycurl/OpenSSL mismatch warning; these requests used plain loopback HTTP, and all expected responses were observed. The script prints only sanitized status summaries and deletes its fixtures. This is evidence for those path and authentication cases only. It does not establish TLS behavior, broad route coverage, sustained flood resistance, or a completed independent pentest.


## Installed JSON-RPC Wfuzz follow-up, 2026-10-19

The Wfuzz loopback review now sends five additional authenticated POST bodies to the installed entry point: truncated JSON, duplicate `method` keys, a `NaN` number, a boolean request ID, and a valid `ping`. The harness compares Wfuzz's HTTP status and response byte count with a direct request for each identical body. It checks JSON-RPC `-32700` for the first three, `-32600` for the invalid ID, an empty result for the valid call, and a further successful `ping` after the sweep. The scanner sends **11 serial requests** total, all to a generated local target. The direct comparison adds five requests; neither run uses an external service or credential.

This checks these five wire bodies and recovery, not general fuzz coverage or full protocol conformance. Wfuzz does not expose response bodies in this JSON report, so the direct requests establish the structured error codes; equal response lengths and statuses link those outcomes to the scanner observations.


## Installed Host and Origin Wfuzz follow-up, 2026-10-19

The installed-endpoint Wfuzz review added seven authenticated header cases. For `Origin`, `http://localhost` returned 200, `https://evil.example` returned 403, and `ftp://localhost` plus `http://localhost:bad` returned 400. For `Host`, `localhost` returned 200, `evil.example` returned 403, and `localhost:bad` returned 400. A valid post-scan `ping` returned 200. The scanner sent **18 serial loopback requests** total across all current sweeps, with one worker and a two-second per-request timeout. The fixed list does not cover every authority parser ambiguity, reverse proxy behavior, or non-loopback deployment.


## Installed audit fail-closed follow-up, 2026-10-19

The installed-endpoint review added a post-scan audit integrity check. It calls `dry_run_command` with `git status` through authenticated HTTP, alters the most recent row in its own temporary SQLite audit database, and repeats the call. The Wfuzz 3.1.0 host run observed `isError: true` with `BLOCKED` / `AUDIT_UNAVAILABLE`, no new decision row, no computed `SAFE` verdict, and a successful subsequent `ping`. This test uses only a disposable audit store. Testing was delayed until host full I/O PSI avg10 fell below 1%. This checks direct row mutation in a disposable store; it does not prove protection against deletion of the final row or an attacker recomputing unkeyed hashes.


## Installed secret-stream follow-up, 2026-10-19

The installed-endpoint review sent a synthetic `ghp_`-shaped token one character per authenticated HTTP tool call, then finalized the stream. The collected output contained `[REDACTED_GITHUB_TOKEN_1]` and did not contain the raw token. No complete token appeared in any response body or the temporary SQLite database and WAL/other sidecar bytes. The host Wfuzz 3.1.0 review and its other installed checks passed after this addition. This tests one supported token shape and one stream; unknown formats, partial-fragment leakage to a caller, and process-memory exposure remain outside the claim.


## Installed handler saturation follow-up, 2026-10-19

After the Wfuzz sweeps, the fresh-installed server review held exactly 32 loopback connections at partial HTTP headers, matching the configured handler cap. One authenticated `ping` received 503. The strengthened probe then completed every held request and required all 32 to return a successful `ping`, proving those connections acquired slots rather than receiving unnoticed 503 responses. After closing those sockets, a new authenticated `ping` returned 200. A regression check confirms the probe rejects a one-slot server and accepts a 32-slot server. The held connections lasted under five seconds and the review closed them in a `finally` block. This is one bounded saturation/recovery observation, not a sustained flood, CPU/RSS profile, or proof that an upstream proxy cannot exhaust its own resources.


## HTTP diagnostic reflection follow-up, 2026-10-20

A synthetic private marker used as an unsupported HTTP method returned 501 with generic JSON, without the request marker. Focused process tests also checked malformed HTTP versions and an overlong header (400/431), followed by valid MCP recovery, plus bodyless HEAD errors. The live probe reports 44 checks when Nmap is available. This prevents reflection through the standard handler diagnostic; it does not sanitize content intentionally returned by tools.


## Malformed-envelope ID follow-up, 2026-10-20

Authenticated HTTP probes sent malformed envelopes with boolean, array, and object IDs. Each returned `-32600` with a null response ID rather than reflecting the invalid value. Focused stdio and HTTP process tests cover the same cases and subsequent valid traffic. The live probe now reports 47 checks with Nmap available. This closes one envelope-validation gap; it is not full MCP conformance evidence.


## Installed command-input follow-up, 2026-10-20

The fresh-installed HTTP review submitted three command strings targeting only temporary fixtures. An instruction-like prefix followed by recursive deletion and a `.env` read returned `BLOCKED`; `find -delete` returned the documented `NEEDS_CONFIRMATION`. Structured and text results agreed, fixture contents remained unchanged after each call, and no synthetic private file content appeared in responses. This checks a fixed corpus and observable fixture preservation, not semantic shell safety or containment of other agent tools.


## Installed budget exhaustion follow-up, 2026-10-20

The installed review configured a ten-token hourly budget and sent twelve one-token reservations through authenticated HTTP. Exactly ten returned `SAFE` / `WITHIN_BUDGET`, with remaining counts descending to zero. The final two returned `BLOCKED` / `TOKENS_BUDGET` with zero remaining; structured and text results matched. This is a serial single-process budget check, not independent metering of an agent, sustained load, or restart-persistence evidence.


## Cleared audit hash restart follow-up, 2026-10-21

After changing the final audit row, the loopback harness cleared its stored hash and attempted a stdio restart with that disposable database. Startup failed before emitting any RPC response. Focused tests also clear either hash column and confirm the altered row remains unmodified; partial hash schemas fail while genuine legacy-table migration still passes. The live probe reports 48 checks with Nmap. Replacing a whole store with a legacy database or recomputing unkeyed hashes remains outside this guarantee.


## Live audit tip follow-up, 2026-10-21

The authenticated HTTP probe deleted the final row of its disposable audit store while the server stayed alive. The next tool call returned `AUDIT_UNAVAILABLE` without appending a replacement decision. Focused tests also delete every row and require the same fail-closed result. The process keeps its last committed tip hash and compares it inside the same immediate transaction as insertion. The live probe reports 49 checks with Nmap. This requires one writer process per store and does not preserve the anchor across restart.

The audit-tip PR's first push CI exposed an existing saturation-harness race on Python 3.11: immediate 503 closure could interrupt the second write of an HTTP client POST. The overload probe now sends one bodyless GET in a single write and reads its 503; all 32 held authenticated calls and the authenticated recovery check remain required. Five consecutive focused runs, then the full local suite and installed review, passed after the fix. This was a probe transport failure, not an audit-tip failure.


## CI probe alignment follow-up, 2026-10-21

The source-tree live probe now shares the installed review's saturation helper and audit-byte scanner. Its 49-check run proves all 32 held requests were accepted, reads overload rejection without a multi-write POST race, and checks audit sidecars as well as the main SQLite file. A focused regression fixture puts the private marker only in a WAL-named sidecar and requires detection. The original simpler source-tree checks did not establish those stronger properties.

## Installed resource snapshots, 2026-10-21

The bounded installed Wfuzz review now records procfs observations for the child server at baseline, while its 32 handlers are held, and after all probes. Against the wheel built from runtime revision `4c3b26f`, the host measured:

| Snapshot | RSS (KiB) | Threads | File descriptors |
| --- | ---: | ---: | ---: |
| Baseline | 27744 | 1 | 7 |
| Saturated | 29508 | 65 | 39 |
| Final | 28584 | 1 | 7 |

The temporary audit database plus sidecars occupied 255256 bytes after the fixed workload. The report also includes the kernel-reported `VmHWM` at each snapshot. These are sampled observations, not a memory ceiling, a continuous peak profile, or proof of long-term leak freedom; CPU and sustained disk growth remain unmeasured. The 65 threads include the main thread, 32 request handlers, and 32 connection-deadline timers. Procfs absence is explicitly reported as unavailable. Reproduce with the installed-review command in the test plan; output contains no command lines or credentials.


## Scalar parameter validation, 2026-10-21

Authenticated HTTP calls supplied null, boolean, numeric, and string `params`. Each returned `-32602` with the request ID preserved. Focused direct and stdio tests cover the same invalid types, subsequent valid requests, accepted structured values, and notification silence. The live probe reports 53 checks with Nmap. This follows the [JSON-RPC parameter structure requirement](https://www.jsonrpc.org/specification#parameter_structures); method-specific validation still applies.


## Bearer comparison hardening, 2026-10-21

The authenticated HTTP probe rejected a same-length token differing in its final character and a non-ASCII incorrect bearer with 401, then continued normal authenticated traffic. Focused process tests also cover first-character mismatch, truncation, scheme case, and missing credentials, requiring generic unauthorized JSON and a successful exact match. The live probe reports 55 checks with Nmap. The server uses constant-time byte comparison; no timing attack or statistical timing guarantee is claimed.


## Installed live-probe CI gate, 2026-10-21

The full live adversarial probe now accepts an installed executable and uses it for every child launch. A host run passed all 55 checks against a fresh wheel, including authenticated HTTP boundaries, secret streaming, handler saturation, stdio oversized-frame recovery, and refusal to restart with a damaged audit. Children ran from a temporary directory with source-path environment overrides cleared. CI runs the same installed mode on Python 3.11 through 3.14 under a 40-second deadline. Nmap remains optional, and this does not replace the separate Wfuzz review or human release gate.


## Official SDK adversarial workflow, 2026-10-21

Official Python SDK 2.3.0 drove a fresh installed stdio server through discovery and safe calls, then path escape and instruction-like recursive deletion against temporary fixtures. Both returned error-marked blocked tool results with matching structured/text content. Three one-token reservations with different session IDs exhausted a two-token caller budget: two safe, then `TOKENS_BUDGET`. A synthetic GitHub-shaped token was replaced by its placeholder, absent from returned text and audit database/sidecar bytes. The sentinel remained unchanged. This fixed-corpus SDK check runs in Python 3.12 CI; it does not prove whole-agent interception or complete prompt-injection resistance.


## Initialization required fields, 2026-10-21

HTTP probes rejected missing required initialization fields, a non-object capabilities value, and invalid client implementation fields with `-32602`, followed by successful valid initialization. Focused direct and stdio tests cover additional invalid types, optional title validation, extension fields, and fallback to the supported version. The source and installed live probes now report 58 checks with Nmap. This validates required fields from the [advertised 2025-06-18 schema](https://modelcontextprotocol.io/specification/2025-06-18/schema#initializerequest), not every nested capability or modern lifecycle requirement.

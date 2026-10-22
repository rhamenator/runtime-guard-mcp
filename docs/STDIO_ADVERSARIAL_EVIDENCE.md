# Finite stdio hostile-frame review

Reviewed on 2026-10-21 (America/Detroit), base revision `5fc0a60`. This is a bounded black-box regression campaign against an actual installed server. It uses only Python's standard library, no inference or external target. It complements the HTTP/Nmap/Wfuzz evidence and does not replace an independent pentest or full MCP conformance review.

## Reproduce

Build a wheel, install it with `--no-deps` in a clean virtual environment, then run:

```bash
python3 scripts/stdio_adversarial_review.py /path/to/runtime-guard-mcp
```

The driver removes source import overrides and server config from the child environment, uses a temporary working directory, starts a fresh server for each era, and uses sequential request/response exchanges. CI runs this against the freshly installed wheel on Python 3.11–3.14 with a 30-second command timeout. The driver also has bounded response reads, queue size, per-response waits, a 20-second child watchdog per era, and child shutdown. It is not an overload/soak test.

## Corpus and observations

Seed `20261021` selects reproducible truncated JSON prefixes. Other cases cover invalid UTF-8, duplicate keys, non-finite/overflow numbers, depth/structure limits, malformed envelopes, params, metadata, IDs, methods and tool arguments. Modern cases add missing protocol fields, unsupported versions and invalid client implementation fields. A valid ping with a unique ID follows every hostile frame, requiring the expected legacy/modern result envelope. A synthetic private marker must not appear in collected stdout replies. Stderr is discarded; this is not stderr leak evidence.

The host installed-wheel run passed **95 legacy** and **109 modern** hostile frames, plus **204 recovery checks**. Its result record is [the pinned corpus summary](evidence/stdio-corpus-2026-10-21.json). This is a finite fixture set, not coverage-guided fuzzing. It does not cover all schema fields, notifications/cancellation races, transport overload, semantic policy bypasses, stderr or sustained resource behavior.

The baseline installed revision failed at a modern null ID paired with an unsupported version: it returned the version error before validating the ID. The fix checks modern IDs first. Review also aligned optional modern `clientInfo.title` validation with legacy behavior; non-string titles now return `-32602`. Focused unit tests cover both fixes. Complete modern schema/error-envelope review remains open.

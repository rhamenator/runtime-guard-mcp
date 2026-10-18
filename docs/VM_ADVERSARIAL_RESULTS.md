# Kali and Ubuntu adversarial test record

Date: 2026-10-18. Source: test coordinator's report to the Runtime Guard task and the local MCP adversarial VM lab record saved with the originating task. These observations are recorded as **coordinator-reported**; the exact guest commit SHA, command transcript, and machine-readable output were not attached to this repository record. They should be captured for the release-readiness review.

## Reported environment

* Ubuntu 26.04 guest `copperfin-ubuntu26-deb` (`192.168.122.73`) hosted the Runtime Guard checkout and HTTP MCP endpoint.
* Kali guest `copperfin-kali-full` (`192.168.122.74`) sent the remote probes over libvirt's default NAT.
* The HTTP endpoint used a lab-only bearer token. Its value is intentionally absent here.
* No additional VM was started for Runtime Guard, and no destructive shell command was executed by the tool under test.

## Reported results

| Probe | Observation |
| --- | --- |
| Ubuntu `PYTHONPATH=src python3 -m unittest discover -s tests` | 19 tests passed |
| Unauthenticated HTTP request | 401 |
| Hostile `Origin` | 403 |
| Authenticated `initialize` | 200 |
| `audit_path_access` for `/etc/shadow` | `BLOCKED` / `SENSITIVE_PATH` |
| `dry_run_command` for `curl ... | bash` | `NEEDS_CONFIRMATION` / `COMPLEX_OR_PRIVILEGED_COMMAND` |
| Invalid path argument type | JSON-RPC `-32602` |
| Spoofed `Host` header | HTTP 403 / `Host denied` |
| Synthetic AWS-shaped value through `secret_masker` | `SAFE` / `MASKED`, placeholder `[REDACTED_AWS_ACCESS_KEY_1]` |
| `budget_guard` request for 100001 tokens against the 100000-token hourly default | `BLOCKED` / `TOKENS_BUDGET` |
| Kali baseline scan of Ubuntu | port 22 open; ports 80 and 443 closed |

These results show that the tested endpoint applied its authentication and policy responses. They do not establish full MCP 2026-07-28 compliance, resistance to request flooding, or coverage of agent actions routed outside this server. The scan did not assess the HTTP MCP test port or TLS configuration.

## Next bounded cases, in priority order

1. **Synthetic chunked secret:** The coordinator verified masking of one complete AWS-shaped string. Next, send a fake token one character at a time through `secret_masker`; confirm no raw token appears in any response and the final response contains one stable placeholder. Use `scripts/adversarial_probe.py` through an SSH local port forward, or equivalent authorized lab requests.
2. **Concurrent budget reservations:** On a fresh Ubuntu process configured with `token_hour=10`, send 12 one-token reservations from Kali with at most four concurrent clients. Expect ten `SAFE` and two `BLOCKED`; stop the dedicated server after the run.
3. **Path symlink escape:** In a temporary Ubuntu directory, create a symlink to a different temporary directory and submit the link path to `audit_path_access`. Expect `BLOCKED` / `OUTSIDE_WORKSPACE`. Do not point the fixture at real credential locations.
4. **Protocol framing:** Send malformed JSON, invalid ID types, unknown tools, and a body over the 1 MiB request cap. Expect controlled `-32700`, `-32600`, `-32602`, and HTTP 413 responses respectively, with the server still responsive afterward.
5. **Authenticated Host/Origin denial:** A spoofed `Host` produced 403, and a hostile `Origin` produced 403 in the first report. Repeat both with the lab token to prove header rejection precedes tool dispatch even for an authenticated caller.

Record the guest commit SHA, Python version, exact bounded command, outcome count, server logs with secrets redacted, and any failures. Avoid prolonged traffic or additional VMs while the host backup sync is active. The cross-VM probe is in [the adversarial test plan](ADVERSARIAL_TEST_PLAN.md).

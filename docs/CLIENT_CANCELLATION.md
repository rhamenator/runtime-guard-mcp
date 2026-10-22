# Real-client cancellation and recovery

Status: bounded client-control observations, not production approval or a universal UI guarantee. The [redacted record](evidence/runtime-client-cancellation-2026-10-22.json) pins server revision `9bfe3b6` and the fresh wheel digest. No production server code was changed for these probes.

## Fixture and reused work

The optional development harness adapts Outbound Guard's control orchestration and transparent wire bridge (GPL-3.0-or-later; control-harness source `f5aaf302ec756c02bddb8c7246ba3c9aef4eeed5`). It removes the network namespace/DNS/HTTP fixture: Runtime Guard has advisory policy functions, not outbound HTTP sockets.

A test-only wrapper imports the installed package using its virtual-environment Python. Only `dry_run_command` is exposed. The first call is paused for up to four seconds; after sending the real client interrupt, the harness deliberately waits about 0.3 seconds and releases that pause. The installed stdio dispatcher, tool policy and audit then run normally. This instrumentation creates a reliable cancellation window; it is **not** a production delay feature, OS-I/O cancellation or proof of forced preemption.

A transparent bridge retains only method/ID/rule/version metadata. A second model prompt in the same live client session requests another advisory check. Passing recovery requires that call's actual `READ_ONLY_COMMAND` tool response and two intact audit decisions. Final assistant prose is not used as evidence. Claude/Cursor records and the successful Codex retry additionally prove that only one fixture process ran. Initial Codex evidence predates that marker; an intervening replay was inconclusive.

## Observations, 2026-10-22

| Client/control path | Protocol observed | Matching MCP cancellation | Cancelled call replied | Recovery |
| --- | --- | --- | --- | --- |
| Claude Code 2.1.301, stream-JSON interrupt | 2026-07-28 | Yes | No | Second call SAFE, one live server process, two audit rows |
| Codex CLI 0.151.0, app-server turn/interrupt (successful retry) | 2025-06-18 | No | Yes | Second call SAFE, one live server process, two audit rows |
| Cursor CLI 2026.10.19-6bbf2c4, ACP session/cancel | 2025-06-18 | No | Yes | Second call SAFE, one live server process, two audit rows |

All three completed observations acknowledged the client turn interrupt and kept the client live. A later Codex replay with process/protocol markers did not complete the acceptance checks; its historical broad rate-limit classifier cannot establish the cause and is retained as **INCONCLUSIVE**. It is not a passing replay and was not automatically retried. The completed initial Codex observation is distinct from that failure.

A cancelled agent turn did not produce an MCP cancellation notification in the tested Codex/Cursor paths. Runtime Guard cannot infer an omitted notification: it completed/replied to the original advisory call. Those clients' prompt MCP-cancellation acceptance remains unmet. Claude's notification suppressed the response while the underlying delayed policy function still finished and wrote its audit decision. No policy/audit rollback is promised.

Reported policy-finish samples (~0.31 seconds after interrupt) include the deliberate 0.3-second release wait; they are not cancellation-latency guarantees. No desktop Stop button, terminal Escape key, saturated client queue, actual slow filesystem or every client/version was tested. Modern authenticated evidence here covers Claude only; other clients' modern behavior remains open.

## Optional reproduction

These development probes require installed/authenticated Claude Code, Codex CLI or Cursor and normal model account usage, which may incur cost. Run them sequentially; classify explicit rate-limit versus account-quota indicators before a bounded retry; an incomplete client probe is not itself a server failure. No sudo, VM, container or network target is required. Normal server users do not need these probes or helper scripts.

Build/install the server in a disposable virtual environment, then supply that environment's **Python executable**, keeping its virtual-environment path (do not replace it with its resolved system-Python symlink target):

```bash
python3 scripts/client_cancellation_probe.py claude /path/to/venv/bin/python
python3 scripts/client_cancellation_probe.py codex /path/to/venv/bin/python
python3 scripts/client_cancellation_probe.py cursor /path/to/venv/bin/python
```

The harness uses an empty owner-only workspace, existing client authentication, one enabled MCP tool, a read-only Codex sandbox, and Cursor permission approval limited to this advisory tool. Claude disables other tools. The agent is instructed not to run commands: `git status` is inspection text for the guard. The Codex temporary home links to existing auth without copying/printing credentials. Private client/wire logs and temporary settings are removed on cleanup; cleanup signals only the probe's process group. Clients may retain their normal account-side history/settings. The helper uses a 150-second watchdog and bounded control waits. A `PASS_OBSERVATION` with `matching_wire_cancellation: false` is a completed negative observation, not a passing prompt-cancellation gate.

A manually authorized bounded Codex retry completed in 11.95 seconds: legacy MCP 2025-06-18, one fixture process, acknowledged interrupt, no MCP cancellation notification, successful second call and two audit records. No current limit was observed; the historical failure cause remains unknown. Future failure hints distinguish explicit account-quota and rate-limit indicators from unknown failures; these hints alone do not establish causality.

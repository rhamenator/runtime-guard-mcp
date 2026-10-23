# Audit scan Python memory regression

Host review on 2026-10-21, based on `1b070f9`; branch `codex/stream-audit-verification`. This addresses the full-table Python allocation part of release issue #54, not audit retention or the complete resource gate.

## Change

Startup/migration and integrity verification iterate SQLite cursors, closing them on completion or early failure. Integrity hashing stays under the process writer lock for a coherent scan relative to this writer. Append hash/tip rules and tamper detection are unchanged. Large scans can delay writes; no deadline or disk retention/cap is introduced.

## Reproduction and regression

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p test_audit_memory.py -q
PYTHONPATH=src python3 -m unittest discover -s tests -p test_policy.py -q
```

`test_audit_memory.py` creates a valid 12,000-record chain in a temporary SQLite database, then measures startup and a complete integrity scan with `tracemalloc`. Both phases must stay below 1 MiB of traced Python allocation. It also corrupts the last row, requires failure at row 12,000 after 11,999 valid records, and requires restart refusal. Existing policy tests cover legacy migration and other mutation/deletion behavior.

Python 3.14.4 host observations:

| Implementation | Startup peak Python bytes | Verification peak Python bytes |
| --- | ---: | ---: |
| Baseline `1b070f9` | 7,443,118 (expected regression failure) | Not reached after the startup assertion |
| Streaming scan | 6,354 | 4,507 |

The regression was also run against the baseline audit module and failed specifically at the 1 MiB startup ceiling. The modified module passed. These figures are observations, not portable exact limits; CI applies the wider 1 MiB regression ceiling across supported Python versions.

## Limits

This measures traced Python allocations only. It does not establish bounded SQLite native memory/cache, process RSS, CPU time, disk/WAL growth, sustained traffic behavior or adversarially rewritten oversized database rows. Disk-full and storage-lock recovery, tamper-evident retention semantics, and sustained resource profiling remain required. No external target, real secret, VM or authenticated model invocation was used.

## Forced process termination during write traffic

The development-only `audit_kill_review.py` starts an installed HTTP server with a temporary audit file, records at least eight acknowledged read-only advisory decisions, then sends SIGKILL while a bounded sequential request producer continues. Eight independent iterations vary the delay before killing. Partial HTTP responses/disconnections after the planned kill are expected transport outcomes, not successful acknowledgements. Unexpected policy/parser failures always fail the probe.

After each kill it requires SQLite integrity and a record count between acknowledged calls and acknowledged calls plus one (at most one request was outstanding). Restarting the actual installed stdio server must verify the persisted audit chain and successfully append another SAFE decision; its row count must increase by exactly one. Restart diagnostics or hash/integrity failures fail the run. CI runs this installed campaign on Python 3.11–3.14.

This establishes bounded same-host process-crash recovery under real traffic, without a test-only runtime patch. It does not guarantee the kill lands inside SQLite commit, simulate host power loss/storage-controller failure, establish physical durability on other filesystems, or recover volatile budgets/masking handles. Those limitations and independent human release disposition remain open. [Machine-readable evidence](evidence/audit-kill-recovery-2026-10-23.json) records actual acknowledgements, surviving row counts, artifact/probe hashes and elapsed time. All eight cycles passed locally in 1.92 seconds, with no unhandled worker exceptions.

# Audit database and WAL admission controls

These controls apply when `audit_db` is enabled. They add no runtime dependency or network permission. Use one writer process per database; retain OS/filesystem quotas for an exact total-disk guarantee.

## Configuration

```json
{
  "workspace_root": "/path/to/workspace",
  "audit_db": "/path/to/audit.sqlite",
  "audit_max_records": 100000,
  "audit_max_db_bytes": 67108864,
  "audit_wal_checkpoint_bytes": 4194304
}
```

`audit_max_db_bytes` defaults to 64 MiB and must be an integer >=8192. Startup sets SQLite `max_page_count`, rounding the byte allowance down to whole database pages. At least two pages must fit for the database's page size. An existing database exceeding the page ceiling causes controlled startup refusal; it is not truncated or deleted. Growth beyond the ceiling causes SQLite write failure and a fail-closed `AUDIT_UNAVAILABLE` result, without the computed tool decision. Earlier rows and the chain remain intact. Raise the reviewed allowance or use the documented verified backup/fresh-file recovery procedure. The default record limit is independent and may be reached first.

`audit_wal_checkpoint_bytes` defaults to 4 MiB and must be an integer >=4096. Before startup migration and each new audit write, a WAL at/above this high-water threshold must complete a `TRUNCATE` checkpoint. A pinned reader that prevents reclamation causes `BLOCKED` / `AUDIT_WAL_CAPACITY`, with no new decision row. Release long-lived readers, then retry only after considering the policy state already changed before audit. Pings remain available in the existing process. Startup can refuse while reclamation is blocked; releasing readers permits a later startup. Checkpoints use the existing 250 ms SQLite busy timeout per attempt; concurrent requests can queue behind the writer lock, so this is not a total request latency bound. `journal_size_limit` also requests reduced retained journal size after SQLite resets it.

## Boundary

The database-page ceiling excludes WAL, shared-memory files, filesystem metadata, backups and temporary storage. The WAL threshold is an **admission high-water mark**, not a hard byte quota: the transaction or startup migration crossing it can overshoot, and writes by external processes are outside this policy. The next admitted write requires successful reclamation. Neither control bounds process RSS or guarantees power-loss durability. No automatic record deletion, rotation, cross-file signing or policy rollback is added. Archive with SQLite's backup API, not a live main-file-only copy; never delete active audit rows to make room.

SQLite reference: [max_page_count, wal_checkpoint and journal_size_limit](https://www.sqlite.org/pragma.html). The implementation verifies the returned page ceiling instead of assuming the PRAGMA was applied.

## Verification

`tests/test_audit_storage_limits.py` uses a real 8 KiB page ceiling, intact-chain verification, reviewed-limit recovery, over-ceiling startup refusal, pinned-reader concurrent denials, concurrent writes after release and controlled WAL-inspection failure. No simulated disk-full exception substitutes for the database ceiling.

Run `python3 scripts/audit_storage_review.py /path/to/venv/bin/runtime-guard-mcp` against an installed build. It fills an 8 KiB audit, preserves its prefix after reviewed-limit restart, pins a real read transaction and sends four concurrent loopback HTTP calls. Each must deny without growing the WAL or returning a computed safe decision; startup while pinned must fail without raw paths/tracebacks. After reader release, four workers complete 128 successful writes and pings succeed. Its temporary audit/config, subprocess watchdog and loopback listener require no VM, model account or external target. CI repeats it on Python 3.11–3.14. This finite four-worker test is not a long concurrent-load soak.

[Machine-readable installed result](evidence/audit-storage-limits-2026-10-22.json) records the server source revision, wheel checksum and probe checksum. The tested wheel contains the production source changes; developer probes are repository artifacts, not runtime dependencies.

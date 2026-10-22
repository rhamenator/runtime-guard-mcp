# Bounded installed-server resource regression

This is one finite sequential saturation test, not closure of the full sustained-resource release gate. It runs an installed wheel with stdlib only on Linux. No model account, VM, container, network target or elevated permission is needed.

## Reproduce

Build a wheel, install it without dependencies into a fresh virtual environment, then run:

```bash
python3 scripts/sustained_resource_review.py /path/to/venv/bin/runtime-guard-mcp
```

The probe removes inherited Runtime Guard/source configuration, creates private temporary config/audit files and drives legacy and modern stdio separately. It fills an audit capped at 128 records, warms up with 128 denials, then sends 65,536 sequential tool calls per era. Every call must fail closed with `AUDIT_CAPACITY`, without returning the computed safe decision. Pings every 64 calls and a final ping must succeed. SQLite structure and retained record count are checked. The server has a 40-second per-era watchdog and bounded shutdown; CI additionally limits the entire command to 90 seconds. Cleanup only affects its own subprocess and temporary directory.

After warmup and every 2,048 calls, Linux `/proc` provides RSS, CPU time, descriptor count and thread count. File sizes include the database, WAL and shared-memory files. Regression thresholds: sampled peak RSS <=128 MiB, RSS increase <=8 MiB, descriptor increase <=2, <=2 threads, no audit-file growth after capacity, and <=30 CPU seconds per measured phase. CPU is process CPU time, not a wall-time latency promise. These are explicit test thresholds, not configurable production quotas. Samples can miss transient peaks.

## Measured 2026-10-22

[Machine-readable evidence](evidence/sustained-resource-2026-10-22.json) identifies the source revision and fresh wheel hash. Local Python 3.14 results:

| Era | Denied calls | Wall seconds | CPU seconds | Peak sampled RSS | RSS / FD / disk increase | Threads |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Legacy | 65,536 | 7.796 | 6.93 | 28,106,752 bytes | 0 / 0 / 0 | 2 |
| Modern | 65,536 | 9.722 | 8.69 | 28,180,480 bytes | 0 / 0 / 0 | 2 |

Each process retained 128 records, six descriptors and 626,056 combined audit-file bytes. Each era has 33 resource samples. Pings remained responsive in this sequential workload; no per-ping latency guarantee is claimed. CI repeats the assertions on Python 3.11–3.14 against a freshly installed artifact.

## Remaining gate

This does not test indefinite soak, mixed successful tool workloads, many callers, concurrent HTTP load, slow output readers, scheduler starvation, power-loss or inode exhaustion. A record cap is not a physical database/WAL byte quota. The full release gate still requires longer mixed/concurrent resource tests, storage/provenance work and exact release-candidate adversarial review. These measurements do not establish whole-agent enforcement.

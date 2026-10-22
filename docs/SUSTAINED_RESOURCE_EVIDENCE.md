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


## Paced concurrent mixed-tool review, 2026-10-22

`python3 scripts/concurrent_resource_review.py /path/to/venv/bin/runtime-guard-mcp` drives an authenticated, installed HTTP server with four workers. Each runs 128 budget/masker/command cycles, paced across eight seconds: 1,536 total tool calls, bounded independently of host speed. The temporary config caps audit records at 1,024 and the shared token allowance at 64. A barrier after each worker's first 16 cycles completes all 64 initial reservations before the record cap can obscure a completed reservation. Exactly 64 reservations must succeed across all worker session IDs; later reservations deny. All tools eventually fail closed at audit capacity, with computed values omitted. The synthetic secret must not appear in replies or audit/sidecars. Post-load ping must return an actual empty result, and an installed stdio restart/ping must pass startup chain verification.

Local Python 3.14 run: 8.025 seconds, 1,536 calls, 64 accepted token reservations, 512 audit-capacity denials and 1,024 retained audit rows. Across 159 samples, peak RSS was 29,601,792 bytes, peak descriptors 11 and peak threads 10. Final descriptors/threads returned to their baseline seven/one; final RSS grew by 692,224 bytes. Process CPU increased 3.52 seconds; combined audit file peak was 287,088 bytes. Post-load and restart-integrity pings passed. These are observations from one finite paced run, not latency or throughput promises.

Regression thresholds: peak sampled RSS <=128 MiB, final RSS growth <=16 MiB, peak threads <=65 and descriptors <=baseline+32, final threads/descriptors <=baseline+2, combined sampled audit files <=8 MiB, process CPU increase <=20 seconds. Snapshots reuse the existing Linux procfs sampler. The helper has a 35-second server watchdog, bounded socket/shutdown waits and private temporary workspace/audit files; CI adds a 45-second outer timeout and runs this extra load only on Python 3.12. Other installed resource/concurrency checks remain in the full matrix. No VM, inference, external network target or runtime dependency is required.

This extends sequential failure-path evidence with concurrent successful/stateful and denial paths. It does not cover long-duration soak, many callers, unique-secret churn, unfinished streams, path checks, output backpressure or exact disk quotas. HTTP remains legacy JSON-RPC over HTTP, and the shared caller budget is not multi-user authorization isolation. Earlier "remaining gate" limitations still apply.

[Machine-readable concurrent results](evidence/concurrent-resource-2026-10-22.json) identify the server/harness revisions and wheel/probe hashes.

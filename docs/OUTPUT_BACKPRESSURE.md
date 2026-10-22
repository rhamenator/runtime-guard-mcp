# Stdio output backpressure

## Failure and implementation

Previously stdout writes and flushes ran under the dispatcher lock. An unread output pipe could block request admission/cancellation and EOF shutdown indefinitely. Output now has one daemon writer using raw descriptor writes, a 32-frame queue and a 16 MiB encoded queued/active byte ceiling. Enqueue never waits for the pipe. One bounded reader queue plus a bounded frame assembly/drain replaces blocking input reads on the transport supervisor, so idle stdin cannot hide output failure. Oversized lines still drain through LF and return a generic error.

The supervisor checks every 50 ms for output failure or a frame taking five seconds to write. Queue/byte overflow and write errors also fail the session. The CLI exits 2; it does not print a traceback or payload diagnostic. Raw blocked descriptor threads are daemons and hold no Python buffered-stream locks, allowing process shutdown. The transport owns process stdio; this is not a reusable embedded-session API or a guarantee of thread interruption. Fixed buffering/deadlines are internal safety limits, not client-configurable throughput promises.

Normal EOF retains the existing up-to-five-second policy drain, then up to five seconds to drain output. A stalled-output failure cancels tracked pending requests, but Python work already running is not preempted. Admitted policy state/audit effects are not rolled back. Queue accounting covers encoded queued/active bytes; response serialization, input frames, policy state and Python allocator overhead are additional bounded-by-input/state allocations, not part of a process-wide RSS quota.

## Recovery

A client must read responses while sending requests. Brief pauses can recover before the limits. After exit 2 or a partial JSON frame, discard that connection and reconnect to a fresh process. Treat stateful outcomes as unknown and do not blindly replay consuming budgets or masking chunks. A fresh process resets volatile state and preserves configured persistent audit history. Restart is not rollback. No stalled pipe is reused after truncation.

## Reproducible installed evidence

Build/install a fresh wheel without dependencies, then run:

```bash
timeout 40s python3 scripts/output_backpressure_review.py /path/to/venv/bin/runtime-guard-mcp
```

For both legacy and modern requests, a 512 KiB masker result fills an actual anonymous output pipe. Leaving stdout unread must exit 2 within eight seconds, with stdin either held open or closed at EOF; disconnecting the reader must also exit 2. Resuming after 250 ms returns the entire valid structured/text result and a subsequent ping, exiting 0. No error diagnostic is returned. All eight scenarios run with persistent audit enabled: one decision remains after each, SQLite integrity passes, and a fresh installed server verifies the hash chain and answers ping. The complete local command took 24.01 seconds including restart verification. The controller has bounded subprocess waits and cleanup. Unit tests also cover frame-limit draining/CRLF/EOF recovery and pre-enqueue byte-ceiling rejection.

These cases demonstrate unknown-outcome semantics: the decision can be committed even if the response never reaches the client. They do not simulate power loss or assert transaction rollback.

[Machine-readable evidence](evidence/output-backpressure-2026-10-22.json) records probe/wheel identity and observations. CI repeats the installed campaign on Python 3.11–3.14. The local full suite has 81 passing tests; installed adversarial transport checks pass. These measurements are Linux pipe evidence, not native Windows/macOS pipe certification, real-client slow-reader tests, hours-long soak, exact memory quotas or whole-agent enforcement. The final exact-candidate client/adversarial/package and human-review gates remain open.

The two fixed I/O threads increase the stdio resource baseline from two to four threads. Installed sequential saturation still passes 65,536 denials per era (11.800/11.565 seconds), no FD/disk growth, RSS growth under 300 KiB, and recovery ping. The production-limit masker campaign also passes with four threads. Only the fixed thread-count assertion changes; RSS/FD/disk/CPU budgets remain unchanged. Updated measurements and probe hashes are included in the same evidence file. Cancellation cannot retract a reply already committed to the output queue.

# Dependency decisions

The server has **no third-party runtime dependencies**. MCP message handling, stdio and HTTP transports, policy checks, sliding windows, redaction, and SQLite audit storage use the Python standard library. This keeps the local attack surface and installation footprint small.

`setuptools>=68` is a build-only dependency for wheel and editable-install metadata. It is not imported by the running server. The official Python MCP SDK 2.3.0 is installed only in a separate temporary client environment for local and Python 3.12 CI interoperability probes; it is not a project dependency.

The deliberate tradeoff is that we maintain a small MCP protocol implementation ourselves. Its current surface is limited to `initialize`, `ping`, `tools/list`, `tools/call`, stdio, and legacy JSON-RPC-over-HTTP JSON responses. Protocol changes, richer streaming, and additional client versions require explicit compatibility tests before release. Security-sensitive behavior is kept in focused local modules with deterministic tests; any future dependency should be justified by a concrete reliability or security gap and reviewed for maintenance cost.

CI enforces the current zero-runtime-dependency policy against the installed wheel's `Requires-Dist` metadata and runs `pip check` in the fresh client environment. Installing with `--no-deps` alone would hide newly declared requirements when the smoke workflow does not import them. A justified future runtime dependency requires updating this gate together with the documented tradeoff.

The optional Linux filesystem-full development probe uses system `unshare`, `mount` and `umount` with rootless user/mount namespaces, or sudo on disposable CI runners. These are test-environment requirements, not server runtime dependencies or ordinary installation permissions.

`jsonschema==4.26.0` is a test-client-only dependency in the isolated SDK probe environment. Its Draft 2020-12 validator checks advertised tool schemas and actual structured results without adding a schema implementation to the server. It is not listed in project requirements or imported by runtime code; the installed-server zero-dependency gate remains unchanged.

The schema test client uses jsonschema's existing transitive `referencing` API to supply an explicit registry that refuses retrieval. No new package or runtime requirement is added. A bounded inline-only preflight and authorized loopback canary campaign verify that hostile schema references cannot cause implicit client retrieval. General schema-reference support remains unsupported.

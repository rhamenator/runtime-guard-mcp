# Dependency decisions

The server has **no third-party runtime dependencies**. MCP message handling, stdio and HTTP transports, policy checks, sliding windows, redaction, and SQLite audit storage use the Python standard library. This keeps the local attack surface and installation footprint small.

`setuptools>=68` is a build-only dependency for wheel and editable-install metadata. It is not imported by the running server. The official Python MCP SDK 2.3.0 was installed only in a temporary test environment for interoperability probes; it is not a project dependency.

The deliberate tradeoff is that we maintain a small MCP protocol implementation ourselves. Its current surface is limited to `initialize`, `ping`, `tools/list`, `tools/call`, stdio, and JSON responses over Streamable HTTP. Protocol changes, richer streaming, and additional client versions require explicit compatibility tests before release. Security-sensitive behavior is kept in focused local modules with deterministic tests; any future dependency should be justified by a concrete reliability or security gap and reviewed for maintenance cost.

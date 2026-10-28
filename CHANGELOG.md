# Changelog

## Unreleased

- Keep official candidates below 1.0; production-quality gates and owner self-review apply, with absence of independent human review disclosed.
- Bound stdio output and input admission, version-aware modern/legacy protocol handling and cancellation recovery; Codex/Cursor tested control paths omit MCP cancellation.
- Enforce completed legacy stdio initialization before tool dispatch and preserve quoted/unquoted credential masking across streaming boundaries.
- Bind inspected source/wheel artifacts to signed provenance and archive scoped separate-model fix reviews.
- Verify Linux wheel clean install, launch, distinct-version fixture upgrade, uninstall and file residue in disposable environments; user data outside the environment is retained.

- Initial stdio and local HTTP MCP server with advisory path, command, budget, and output tools.
- Redacted, tamper-evident optional SQLite audit log.
- Repository security, contribution, and CI baseline.

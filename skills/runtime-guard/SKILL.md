---
name: runtime-guard
description: Use a configured runtime-guard-mcp server to assess coding-agent file paths, shell commands, budgets, and output redaction before actions. Applies only when this local server is connected.
---

# Runtime Guard

Connect the server via stdio as documented in the [README](../../README.md), with `RUNTIME_GUARD_WORKSPACE_ROOT` set to the project workspace. Verify `tools/list` before relying on it. This skill does not install software, set host policy, or grant execution permission.

Before a risky file action, call `audit_path_access` with the exact intended path and operation. Before a shell command with uncertain effects, call `dry_run_command` with its actual shell. Treat `BLOCKED` as a stop and `NEEDS_CONFIRMATION` as a request for human review. `SAFE` is an advisory classification; use ordinary user instructions and host controls for the final decision.

Use `budget_guard` to reserve reported token, payload, and command usage with `consume=true`, supplying a stable action fingerprint to detect loops. Use `secret_masker` for untrusted command output or text that may contain credentials; send chunks under one stream ID and end with `final=true`. Never send raw secrets back to the model for convenience.

The server cannot see actions routed through other tools. Do not describe its presence as whole-agent enforcement.

"""Bounded policy checks; no tool in this module executes a command or reads a target file."""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def verdict(status: str, rule: str, remediation: str, **details: Any) -> dict[str, Any]:
    return {"status": status, "rule": rule, "remediation": remediation, **details}


SENSITIVE_PARTS = {".ssh", ".aws", ".gnupg", ".kube", "gcloud"}
SENSITIVE_FILES = {".env", ".env.local", "id_rsa", "id_ed25519", "credentials", "shadow", "secrets.json"}


def _resolve_policy_path(path: Path) -> Path:
    # Strict resolution consistently reports loops/access failures across Python
    # versions. Missing targets remain valid advisory candidates for new files.
    try:
        return path.resolve(strict=True)
    except FileNotFoundError:
        return path.resolve(strict=False)


def audit_path_access(path: str, workspace_root: str, operation: str = "read", allowed_roots: list[str] | None = None) -> dict[str, Any]:
    if not path or not workspace_root:
        return verdict("BLOCKED", "INVALID_PATH", "Supply a path and workspace root.")
    if "\x00" in path or "\x00" in workspace_root:
        return verdict("BLOCKED", "INVALID_PATH", "Remove NUL bytes.")
    if operation not in {"read", "write", "delete"}:
        return verdict("BLOCKED", "INVALID_OPERATION", "Use read, write, or delete.")
    try:
        root = _resolve_policy_path(Path(workspace_root).expanduser())
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = _resolve_policy_path(candidate)
        roots = [root] + [_resolve_policy_path(Path(p).expanduser()) for p in (allowed_roots or [])]
    except (OSError, RuntimeError):
        return verdict("BLOCKED", "PATH_RESOLUTION_FAILED", "Restore path accessibility or remove symlink loops before retrying.")
    parts = {p.lower() for p in resolved.parts}
    if any(p.lower() in SENSITIVE_FILES or p.lower().startswith(".env.") for p in resolved.parts) or parts & SENSITIVE_PARTS:
        return verdict("BLOCKED", "SENSITIVE_PATH", "Use a project-safe file instead.", resolved_path=str(resolved))
    if not any(resolved == item or item in resolved.parents for item in roots):
        return verdict("BLOCKED", "OUTSIDE_WORKSPACE", "Choose a path inside the configured workspace.", resolved_path=str(resolved))
    if operation == "delete":
        return verdict("NEEDS_CONFIRMATION", "DESTRUCTIVE_FILE_OPERATION", "Confirm the exact deletion with the user.", resolved_path=str(resolved))
    return verdict("SAFE", "WORKSPACE_PATH", "No remediation needed.", resolved_path=str(resolved))


READ_ONLY = {"pwd", "ls", "cat", "head", "tail", "rg", "grep", "find", "wc", "stat", "git status", "git diff", "git log", "git show"}
BLOCKED_RE = [
    (re.compile(r"\brm\s+(?:-[A-Za-z]*[rf][A-Za-z]*\s+)+(/|~|\*|\.)\b|\brm\s+-[A-Za-z]*[rf][A-Za-z]*\b|\brm\s+--recursive\b|\bRemove-Item\b[^\n]*-Recurse\b", re.I), "RECURSIVE_DELETE"),
    (re.compile(r"\b(?:mkfs(?:\.[\w]+)?|dd\s+if=|wipefs|shred|Clear-Disk|Format-Volume)\b", re.I), "RAW_DISK_OPERATION"),
    (re.compile(r"\bgit\b[^\n]*\bpush\b[^\n]*(?:--force(?:-with-lease)?|\s-f\b)", re.I), "FORCE_PUSH"),
    (re.compile(r"\b(?:DROP\s+(?:DATABASE|TABLE)|TRUNCATE\s+TABLE)\b", re.I), "DATABASE_DESTRUCTION"),
]


def dry_run_command(command: str, shell: str = "bash") -> dict[str, Any]:
    if shell not in {"bash", "sh", "pwsh"} or len(command) > 8192 or "\x00" in command:
        return verdict("BLOCKED", "INVALID_COMMAND", "Use a supported shell and a command under 8192 characters.")
    if re.search(r"(?:~|/home/[^/\s]+)/(?:\.ssh|\.aws|\.gnupg|\.kube|\.config/gcloud)(?:/|\b)|/etc/(?:shadow|gshadow)\b|/proc/(?:self|\d+)/(?:environ|mem)\b|(?:^|[/\s])\.env(?:\.[\w-]+)?(?:\s|$)", command, re.I):
        return verdict("BLOCKED", "SENSITIVE_PATH", "Do not read or modify credential files through shell commands.")
    for pattern, rule in BLOCKED_RE:
        if pattern.search(command):
            return verdict("BLOCKED", rule, "Use a narrowly scoped alternative or obtain an explicit reviewed exception.")
    if re.search(r"\bfind\b[^\n]*(?:-delete\b|-exec\b|-execdir\b|-ok\b|-okdir\b)", command, re.I):
        return verdict("NEEDS_CONFIRMATION", "FIND_SIDE_EFFECT", "Review find actions and each target before execution.")
    if re.search(r"\b(?:curl|wget)\b.*\|\s*(?:bash|sh|pwsh)\b|\b(?:sudo|su)\b|\$\(|`", command, re.I):
        return verdict("NEEDS_CONFIRMATION", "COMPLEX_OR_PRIVILEGED_COMMAND", "Review expansion, remote code, and privileges before execution.")
    try:
        tokens = shlex.split(command, posix=shell != "pwsh")
    except ValueError:
        return verdict("NEEDS_CONFIRMATION", "UNPARSEABLE_COMMAND", "Review shell syntax manually.")
    if not tokens:
        return verdict("BLOCKED", "EMPTY_COMMAND", "Supply a command.")
    # Lexical credential components only: do not expand variables, execute the
    # shell or open paths. Quoted operands are conservative matches too.
    parts = {part.strip("\"'").lower() for token in tokens[1:]
             for part in re.split(r"[/=:]", (token[2:] if token.startswith("-f") else token).strip("\"'").replace("\\", "/"))}
    if parts & (SENSITIVE_PARTS | SENSITIVE_FILES) or any(part.startswith('.env.') for part in parts):
        return verdict("BLOCKED", "SENSITIVE_COMMAND_PATH", "Use project-safe operands instead of credential paths.")
    if tokens[0] in {"bash", "sh", "pwsh"} and any(x in tokens for x in {"-c", "-Command"}):
        return verdict("NEEDS_CONFIRMATION", "NESTED_SHELL", "Review the nested script separately.")
    if any(x in command for x in ("|", ">", "<", ";", "&", "(", ")", "\n", "\r")):
        return verdict("NEEDS_CONFIRMATION", "COMPOUND_COMMAND", "Review each command and redirection separately.")
    # Read-oriented programs can still write files or invoke subprocesses.
    # Conservative option matching also flags quoted operands with these names.
    option_names = {token.split("=", 1)[0] for token in tokens[1:]}
    side_effect_options = {
        "git": {"--output"},
        "find": {"-fprint", "-fprint0", "-fprintf", "-fls"},
        "rg": {"--pre", "--hostname-bin"},
    }
    if option_names & side_effect_options.get(tokens[0], set()):
        return verdict("NEEDS_CONFIRMATION", "COMMAND_SIDE_EFFECT_OPTION", "Review file-output and subprocess options and their targets before execution.")
    key = " ".join(tokens[:2]) if tokens[0] == "git" else tokens[0]
    if key in READ_ONLY:
        return verdict("SAFE", "READ_ONLY_COMMAND", "No remediation needed.")
    return verdict("NEEDS_CONFIRMATION", "UNRECOGNIZED_COMMAND", "Review effects and target paths before execution.")


class InvocationLimiter:
    """One process-wide fixed minute window; constant memory and atomic admission."""

    def __init__(self, limit: int = 600, clock=time.monotonic):
        if type(limit) is not int or limit <= 0:
            raise ValueError("invocations_minute must be a positive integer")
        self.limit = limit
        self._clock = clock
        self._start = clock()
        self._count = 0
        self._lock = threading.Lock()

    def admit(self) -> bool:
        with self._lock:
            now = self._clock()
            if now - self._start >= 60:
                self._start, self._count = now, 0
            if self._count >= self.limit:
                return False
            self._count += 1
            return True


class BudgetState:
    """Per-caller limits; session IDs cannot reset caller-wide windows."""

    def __init__(self, token_hour: int = 100_000, payload_hour: int = 50_000_000, commands_minute: int = 120, max_events_per_metric: int = 8192, max_fingerprint_events: int = 4096):
        self.token_hour = token_hour
        self.payload_hour = payload_hour
        self.commands_minute = commands_minute
        self.max_events_per_metric = max_events_per_metric
        self.max_fingerprint_events = max_fingerprint_events
        self._lock = threading.Lock()
        self._events: dict[tuple[str, str], deque[tuple[float, int]]] = defaultdict(deque)
        self._fingerprints: dict[tuple[str, str], deque[tuple[float, str]]] = defaultdict(deque)
        self._fingerprint_order: deque[tuple[float, tuple[str, str]]] = deque()

    def check(self, caller: str, session: str, tokens: int, payload_bytes: int, commands: int, fingerprint: str, consume: bool) -> dict[str, Any]:
        if min(tokens, payload_bytes, commands) < 0 or max(tokens, payload_bytes, commands) > 10_000_000:
            return verdict("BLOCKED", "INVALID_BUDGET_INPUT", "Use nonnegative bounded counts.")
        now = time.monotonic()
        limits = {"tokens": (3600, self.token_hour, tokens), "payload": (3600, self.payload_hour, payload_bytes), "commands": (60, self.commands_minute, commands)}
        with self._lock:
            totals = {}
            for metric, (window, limit, amount) in limits.items():
                q = self._events[(caller, metric)]
                while q and q[0][0] <= now - window:
                    q.popleft()
                totals[metric] = sum(n for _, n in q)
                if totals[metric] + amount > limit:
                    return verdict("BLOCKED", f"{metric.upper()}_BUDGET", "Reduce work or wait for the budget window to reset.", remaining=max(0, limit - totals[metric]))
            if fingerprint:
                while self._fingerprint_order and self._fingerprint_order[0][0] <= now - 300:
                    _, old_key = self._fingerprint_order.popleft()
                    old_queue = self._fingerprints[old_key]
                    old_queue.popleft()
                    if not old_queue:
                        del self._fingerprints[old_key]
                q = self._fingerprints.get((caller, session), ())
                if sum(value == fingerprint for _, value in q) >= 5:
                    return verdict("BLOCKED", "REPEATED_LOOP", "Stop the repeated action and inspect its prior results.")
            if consume:
                if any(amount and len(self._events[(caller, metric)]) >= self.max_events_per_metric for metric, (_, _, amount) in limits.items()):
                    return verdict("BLOCKED", "BUDGET_STATE_LIMIT", "Wait for an older reservation to expire before consuming more budget.")
                if fingerprint and len(self._fingerprint_order) >= self.max_fingerprint_events:
                    return verdict("BLOCKED", "FINGERPRINT_STATE_LIMIT", "Wait for an older fingerprint to expire before recording more actions.")
                for metric, (_, _, amount) in limits.items():
                    if amount:
                        self._events[(caller, metric)].append((now, amount))
                if fingerprint:
                    key = (caller, session)
                    self._fingerprints[key].append((now, fingerprint))
                    self._fingerprint_order.append((now, key))
            return verdict("SAFE", "WITHIN_BUDGET", "No remediation needed.", remaining={m: limits[m][1] - totals[m] - limits[m][2] for m in limits})


SECRET_PATTERNS = [
    ("AWS_ACCESS_KEY", re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}")),
    ("GITHUB_TOKEN", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,255}")),
    ("OPENAI_KEY", re.compile(r"sk-[A-Za-z0-9_-]{20,255}")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]{0,8192}?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("PASSWORD_ASSIGNMENT", re.compile(r"""\b(?:password|api[_-]?key|secret|token)["']?\s*[:=]\s*(?:"(?:\\.|[^"\\\r\n]){8,256}(?:"|\\?(?=\r|\n|$))|'(?:\\.|[^'\\\r\n]){8,256}(?:'|\\?(?=\r|\n|$))|[^\s'"]{8,256}(?=[\s'"]|$))""", re.I)),
    ("EMAIL_ADDRESS", re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}\b")),
    ("US_SSN", re.compile(r"\b(?!000|666|9\d\d)\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b")),
]
MAX_MASKER_STREAMS = 128
MAX_MASKER_SECRETS_PER_CALLER = 4096


class SecretMasker:
    def __init__(self, max_streams: int = MAX_MASKER_STREAMS, max_secrets_per_caller: int = MAX_MASKER_SECRETS_PER_CALLER):
        self._lock = threading.Lock()
        self._secrets: dict[str, dict[str, str]] = defaultdict(dict)
        self._indices: dict[str, dict[str, int]] = defaultdict(dict)
        self._buffers: dict[tuple[str, str], str | None] = {}
        self.max_streams = max_streams
        self.max_secrets_per_caller = max_secrets_per_caller

    @staticmethod
    def _matches(text: str) -> list[tuple[int, int, str, str, list[str]]]:
        spans = sorted((m.start(), m.end(), kind) for kind, pattern in SECRET_PATTERNS
                       for m in pattern.finditer(text))
        merged = []
        for start, end, kind in spans:
            if merged and start < merged[-1][1]:
                prior = merged[-1]
                prior[1] = max(prior[1], end)
                if kind not in prior[3]:
                    prior[3].append(kind)
            else:
                merged.append([start, end, kind, [kind]])
        return [(start, end, kind, text[start:end], kinds)
                for start, end, kind, kinds in merged]

    def _mask(self, caller: str, text: str, matches=None) -> tuple[str, list[str]] | None:
        if matches is None:
            matches = self._matches(text)
        mapping = self._secrets[caller]
        new_digests = set()
        cursor = 0
        for start, end, kind, value, detected in matches:
            if start < cursor:
                continue
            digest = hashlib.sha256((kind + "\0" + value).encode()).hexdigest()
            if digest not in mapping:
                new_digests.add(digest)
            cursor = end
        if len(mapping) + len(new_digests) > self.max_secrets_per_caller:
            return None
        output = []
        kinds = []
        cursor = 0
        for start, end, kind, value, detected in matches:
            if start < cursor:
                continue
            output.append(text[cursor:start])
            digest = hashlib.sha256((kind + "\0" + value).encode()).hexdigest()
            if digest not in mapping:
                indices = self._indices[caller]
                indices[kind] = indices.get(kind, 0) + 1
                mapping[digest] = f"[REDACTED_{kind}_{indices[kind]}]"
            output.append(mapping[digest])
            kinds.extend(detected)
            cursor = end
        output.append(text[cursor:])
        return "".join(output), sorted(set(kinds))

    def mask(self, caller: str, session: str, stream: str, chunk: str, final: bool) -> dict[str, Any]:
        if len(chunk) > 1_048_576:
            return verdict("BLOCKED", "CHUNK_TOO_LARGE", "Send smaller chunks.")
        key = (caller + ":" + session, stream)
        with self._lock:
            if key in self._buffers and self._buffers[key] is None:
                if final:
                    self._buffers.pop(key)
                return verdict("BLOCKED", "STREAM_RESET_REQUIRED", "Discard this stream and start a new one.")
            if key not in self._buffers and not final and len(self._buffers) >= self.max_streams:
                return verdict("BLOCKED", "STREAM_LIMIT", "Finish an existing stream before starting another.")
            raw = (self._buffers.get(key) or "") + chunk
            if len(raw) > 1_064_960:
                if final:
                    self._buffers.pop(key, None)
                else:
                    self._buffers[key] = None
                return verdict("BLOCKED", "STREAM_BUFFER_TOO_LARGE", "Finish or reset the stream.")
            if final:
                self._buffers.pop(key, None)
                try:
                    result = self._mask(caller, raw)
                except UnicodeEncodeError:
                    return verdict("BLOCKED", "INVALID_UNICODE", "Remove invalid Unicode from the stream.")
                if result is None:
                    return verdict("BLOCKED", "SECRET_STATE_LIMIT", "Start a fresh process before masking more distinct secrets.")
                masked, kinds = result
                return verdict("SAFE", "MASKED", "No remediation needed.", text=masked, secret_types=kinds)
            # Hold a conservative tail so a token split across chunks is not emitted early.
            cutoff = max(0, len(raw) - 16384)
            matches = self._matches(raw)
            for start, end, _, _, _ in matches:
                if start < cutoff < end:
                    cutoff = start
            prefix, tail = raw[:cutoff], raw[cutoff:]
            try:
                result = self._mask(caller, prefix, [match for match in matches if match[1] <= cutoff])
            except UnicodeEncodeError:
                self._buffers[key] = None
                return verdict("BLOCKED", "INVALID_UNICODE", "Remove invalid Unicode from the stream.")
            if result is None:
                self._buffers[key] = None
                return verdict("BLOCKED", "SECRET_STATE_LIMIT", "Start a fresh process before masking more distinct secrets.")
            self._buffers[key] = tail
            masked, kinds = result
            return verdict("SAFE", "MASKED", "No remediation needed.", text=masked, secret_types=kinds)

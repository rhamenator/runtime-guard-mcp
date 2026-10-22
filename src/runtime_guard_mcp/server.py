"""Advisory MCP server with stdio and legacy JSON-RPC-over-HTTP transports."""

from __future__ import annotations

import argparse
import hmac
import json
import math
import os
import queue
import socket
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore, Event, Lock, Thread, Timer
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .audit import AuditCapacityError, AuditIntegrityError, AuditLog, DEFAULT_AUDIT_MAX_RECORDS
from .policy import BudgetState, SecretMasker, audit_path_access, dry_run_command, verdict

PROTOCOL_VERSION = "2025-06-18"
MODERN_VERSION = "2026-07-28"
META_PREFIX = "io.modelcontextprotocol/"
MAX_STDIO_REQUESTS = 32
MAX_MESSAGE = 1_048_576
MAX_JSON_DEPTH = 64
MAX_JSON_STRUCTURE_TOKENS = 8192
MAX_HTTP_HANDLERS = 32
HTTP_SOCKET_TIMEOUT = 5.0
HTTP_CONNECTION_DEADLINE = 5.0


class BoundedHTTPServer(ThreadingHTTPServer):
    """Reject excess connections before creating handler threads."""

    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], handler: type[BaseHTTPRequestHandler], max_handlers: int = MAX_HTTP_HANDLERS, socket_timeout: float = HTTP_SOCKET_TIMEOUT, connection_deadline: float = HTTP_CONNECTION_DEADLINE):
        self._slots = BoundedSemaphore(max_handlers)
        self.socket_timeout = socket_timeout
        self.connection_deadline = connection_deadline
        super().__init__(server_address, handler)

    def process_request(self, request: Any, client_address: Any) -> None:
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        def expire() -> None:
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        deadline = Timer(self.connection_deadline, expire)
        deadline.daemon = True
        try:
            deadline.start()
            request.settimeout(self.socket_timeout)
            super().process_request_thread(request, client_address)
        finally:
            deadline.cancel()
            self._slots.release()


def obj(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


STR = {"type": "string"}
NONNEG = {"type": "integer", "minimum": 0}
TOOLS = [
    {"name": "audit_path_access", "description": "Advisory path containment check; follows existing symlinks but does not authorize a later filesystem operation.", "inputSchema": obj({"path": {"type": "string", "maxLength": 4096}, "operation": {"type": "string", "enum": ["read", "write", "delete"]}}, ["path"])},
    {"name": "dry_run_command", "description": "Classify shell text without executing it. SAFE is heuristic, not permission to execute.", "inputSchema": obj({"command": {"type": "string", "maxLength": 8192}, "shell": {"type": "string", "enum": ["bash", "sh", "pwsh"]}}, ["command"])},
    {"name": "budget_guard", "description": "Check or atomically consume caller-wide token, payload, and command budgets; detects repeated session actions.", "inputSchema": obj({"session_id": {"type": "string", "maxLength": 128}, "tokens": NONNEG, "payload_bytes": NONNEG, "commands": NONNEG, "fingerprint": {"type": "string", "maxLength": 256}, "consume": {"type": "boolean"}}, ["session_id"])},
    {"name": "secret_masker", "description": "Mask common credentials in output chunks using stable placeholders within a caller; final=true flushes buffered text.", "inputSchema": obj({"session_id": {"type": "string", "maxLength": 128}, "stream_id": {"type": "string", "maxLength": 128}, "chunk": {"type": "string", "maxLength": 1048576}, "final": {"type": "boolean"}}, ["session_id", "stream_id", "chunk", "final"])},
]

OUTPUT_BASE = {"status": {"type": "string", "enum": ["SAFE", "NEEDS_CONFIRMATION", "BLOCKED"]}, "rule": STR, "remediation": STR}
OUTPUT_EXTRA = {
    "audit_path_access": {"resolved_path": STR},
    "dry_run_command": {},
    "budget_guard": {"remaining": {"oneOf": [{"type": "integer", "minimum": 0}, {"type": "object", "properties": {"tokens": NONNEG, "payload": NONNEG, "commands": NONNEG}, "required": ["tokens", "payload", "commands"], "additionalProperties": False}]}},
    "secret_masker": {"text": STR, "secret_types": {"type": "array", "items": STR}},
}
for definition in TOOLS:
    definition["outputSchema"] = obj({**OUTPUT_BASE, **OUTPUT_EXTRA[definition["name"]]}, ["status", "rule", "remediation"])


def rpc_error(identifier: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": identifier, "error": {"code": code, "message": message}}


def parse_json_request(raw: bytes) -> Any:
    """Decode one UTF-8 JSON message without ambiguous or non-finite values."""
    source = raw.decode("utf-8")
    depth = 0
    structure_tokens = 0
    in_string = False
    escaped = False
    for character in source:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{:,":
            structure_tokens += 1
            if structure_tokens > MAX_JSON_STRUCTURE_TOKENS:
                raise ValueError("JSON structure limit exceeded")
            if character in "[{":
                depth += 1
                if depth > MAX_JSON_DEPTH:
                    raise ValueError("JSON nesting limit exceeded")
        elif character in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced JSON nesting")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    def reject_constant(_value: str) -> None:
        raise ValueError("Non-finite JSON constant")

    return json.loads(source, object_pairs_hook=unique_object, parse_float=finite_float, parse_constant=reject_constant)


def valid_meta_key(key: str) -> bool:
    """Validate metadata names in linear time without backtracking regexes."""
    if not key.isascii():
        return False
    prefix, separator, name = key.rpartition("/")
    if separator:
        for label in prefix.split("."):
            if not label or not label[0].isalpha() or not label[-1].isalnum() or any(not (char.isalnum() or char == "-") for char in label):
                return False
    else:
        name = key
    return not name or (name[0].isalnum() and name[-1].isalnum() and all(char.isalnum() or char in "-_." for char in name))


class RuntimeGuard:
    def __init__(self, workspace_root: str, token_hour: int = 100_000, payload_hour: int = 50_000_000, commands_minute: int = 120, audit_db: str | None = None, allowed_roots: list[str] | None = None, enabled_tools: list[str] | None = None, audit_max_records: int = DEFAULT_AUDIT_MAX_RECORDS):
        self.workspace_root = str(Path(workspace_root).expanduser().resolve(strict=False))
        self.allowed_roots = allowed_roots or []
        self.enabled_tools = set(enabled_tools) if enabled_tools is not None else {tool["name"] for tool in TOOLS}
        self.budgets = BudgetState(token_hour, payload_hour, commands_minute)
        self.masker = SecretMasker()
        self.audit = AuditLog(audit_db, audit_max_records) if audit_db else None

    def call(self, name: str, arguments: dict[str, Any], caller: str) -> dict[str, Any]:
        if name == "audit_path_access":
            result = audit_path_access(arguments["path"], self.workspace_root, arguments.get("operation", "read"), self.allowed_roots)
        elif name == "dry_run_command":
            result = dry_run_command(arguments["command"], arguments.get("shell", "bash"))
        elif name == "budget_guard":
            result = self.budgets.check(caller, arguments["session_id"], arguments.get("tokens", 0), arguments.get("payload_bytes", 0), arguments.get("commands", 0), arguments.get("fingerprint", ""), arguments.get("consume", False))
        elif name == "secret_masker":
            result = self.masker.mask(caller, arguments["session_id"], arguments["stream_id"], arguments["chunk"], arguments["final"])
        else:
            raise KeyError(name)
        if self.audit:
            try:
                self.audit.record(caller, name, result["status"], result["rule"])
            except AuditCapacityError:
                result = verdict("BLOCKED", "AUDIT_CAPACITY", "Archive the verified audit database and configure a fresh audit_db before retrying; do not delete active audit rows.")
            except (sqlite3.Error, AuditIntegrityError):
                result = verdict("BLOCKED", "AUDIT_UNAVAILABLE", "Restore audit integrity and storage before using this server.")
        return {"content": [{"type": "text", "text": json.dumps(result, separators=(",", ":"))}], "structuredContent": result, "isError": result["status"] == "BLOCKED"}

    def handle(self, message: Any, caller: str = "local", modern_stdio: bool = False) -> dict[str, Any] | None:
        identifier = message.get("id") if isinstance(message, dict) else None
        if type(identifier) not in {str, int, float, type(None)} or (type(identifier) is float and not math.isfinite(identifier)):
            return rpc_error(None, -32600, "Invalid Request")
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return rpc_error(identifier, -32600, "Invalid Request")
        if "id" not in message:
            return None
        if "params" in message and not isinstance(message["params"], dict):
            return rpc_error(identifier, -32602, "Invalid params")
        params = message.get("params", {})
        if "_meta" in params and not isinstance(params["_meta"], dict):
            return rpc_error(identifier, -32602, "Invalid request metadata")
        method = message["method"]
        meta = params.get("_meta", {})
        modern = any(key.startswith(META_PREFIX) for key in meta) or method == "server/discover"
        if modern:
            if type(identifier) not in {str, int}:
                return rpc_error(None, -32600, "Invalid Request")
            if not isinstance(meta.get(META_PREFIX + "protocolVersion"), str) or not isinstance(meta.get(META_PREFIX + "clientCapabilities"), dict):
                return rpc_error(identifier, -32602, "Missing or invalid per-request protocol metadata")
            version = meta[META_PREFIX + "protocolVersion"]
            if version != MODERN_VERSION or not modern_stdio:
                response = rpc_error(identifier, -32022, "Unsupported protocol version")
                response["error"]["data"] = {"supported": [MODERN_VERSION, PROTOCOL_VERSION] if modern_stdio else [PROTOCOL_VERSION], "requested": version}
                return response
            client = meta.get(META_PREFIX + "clientInfo")
            if META_PREFIX + "clientInfo" in meta and (not isinstance(client, dict) or not all(isinstance(client.get(key), str) for key in ("name", "version")) or ("title" in client and not isinstance(client["title"], str))):
                return rpc_error(identifier, -32602, "Invalid client implementation")
            capabilities = meta[META_PREFIX + "clientCapabilities"]
            if any(not isinstance(value, dict) for value in capabilities.values()):
                return rpc_error(identifier, -32602, "Invalid client capabilities")
            if META_PREFIX + "logLevel" in meta and meta[META_PREFIX + "logLevel"] not in ("debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"):
                return rpc_error(identifier, -32602, "Invalid log level")
            if "progressToken" in meta and type(meta["progressToken"]) not in {str, int, float}:
                return rpc_error(identifier, -32602, "Invalid progress token")
            if any(not valid_meta_key(key) for key in meta):
                return rpc_error(identifier, -32602, "Invalid metadata key")
        if method == "server/discover":
            result = {"supportedVersions": [MODERN_VERSION, PROTOCOL_VERSION], "capabilities": {"tools": {}}, "ttlMs": 0, "cacheScope": "private"}
        elif method == "initialize":
            if modern:
                return rpc_error(identifier, -32601, "Modern requests use server/discover")
            params = message.get("params")
            if not isinstance(params, dict) or not isinstance(params.get("protocolVersion"), str) or not isinstance(params.get("capabilities"), dict):
                return rpc_error(identifier, -32602, "Invalid initialize parameters")
            client = params.get("clientInfo")
            if not isinstance(client, dict) or not all(isinstance(client.get(field), str) for field in ("name", "version")) or ("title" in client and not isinstance(client["title"], str)):
                return rpc_error(identifier, -32602, "Invalid client implementation")
            result = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "runtime-guard-mcp", "version": __version__}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [tool for tool in TOOLS if tool["name"] in self.enabled_tools]}
            if modern:
                result["tools"].sort(key=lambda tool: tool["name"])
                result.update(ttlMs=0, cacheScope="private")
        elif method == "tools/call":
            params = message.get("params")
            if not isinstance(params, dict) or not isinstance(params.get("name"), str) or not isinstance(params.get("arguments", {}), dict):
                return rpc_error(identifier, -32602, "Invalid tool arguments")
            name, args = params["name"], params.get("arguments", {})
            tool = next((tool for tool in TOOLS if tool["name"] == name), None)
            if tool is None or name not in self.enabled_tools:
                return rpc_error(identifier, -32602, "Unknown tool")
            required = tool["inputSchema"]["required"]
            allowed = tool["inputSchema"]["properties"]
            if any(field not in args for field in required) or any(field not in allowed for field in args):
                return rpc_error(identifier, -32602, "Invalid tool arguments")
            for field, value in args.items():
                spec = allowed[field]
                kind = spec["type"]
                if (kind == "string" and (not isinstance(value, str) or len(value) > spec.get("maxLength", MAX_MESSAGE))) or (kind == "integer" and (type(value) is not int or value < spec.get("minimum", 0))) or (kind == "boolean" and type(value) is not bool) or ("enum" in spec and value not in spec["enum"]):
                    return rpc_error(identifier, -32602, "Invalid tool arguments")
            try:
                result = self.call(name, args, caller)
            except (KeyError, TypeError, ValueError):
                return rpc_error(identifier, -32602, "Invalid tool arguments")
        else:
            return rpc_error(identifier, -32601, "Method not found")
        if modern:
            result = {**result, "resultType": "complete", "_meta": {META_PREFIX + "serverInfo": {"name": "runtime-guard-mcp", "version": __version__}}}
        return {"jsonrpc": "2.0", "id": identifier, "result": result}


class StdioDispatcher:
    """One policy worker, bounded admission, and cancellation on the reader thread."""

    def __init__(self, guard: RuntimeGuard, emit: Any, capacity: int = MAX_STDIO_REQUESTS):
        self.guard, self.emit = guard, emit
        self.pending: dict[Any, Event] = {}
        self.initializations: set[Any] = set()
        self.lock = Lock()
        self.slots = BoundedSemaphore(capacity)
        self.queue: queue.Queue = queue.Queue(maxsize=capacity)
        self.closed = Event()
        self.worker = Thread(target=self._run, daemon=True)
        self.worker.start()

    def submit(self, message: Any) -> None:
        if isinstance(message, dict) and "id" not in message and message.get("jsonrpc") == "2.0" and isinstance(message.get("method"), str):
            params = message.get("params")
            if message.get("jsonrpc") == "2.0" and message.get("method") == "notifications/cancelled" and isinstance(params, dict) and isinstance(params.get("_meta", {}), dict):
                identifier = params.get("requestId")
                if type(identifier) in {str, int} and ("reason" not in params or isinstance(params["reason"], str)):
                    with self.lock:
                        event = self.pending.get(identifier)
                        if event and identifier not in self.initializations:
                            event.set()
            return
        identifier = message.get("id") if isinstance(message, dict) else None
        tracked = type(identifier) in {str, int}
        with self.lock:
            if tracked and identifier in self.pending:
                self.emit(rpc_error(identifier, -32600, "Request ID already in flight"))
                return
            if not self.slots.acquire(blocking=False):
                self.emit(rpc_error(identifier if tracked else None, 1001, "Request capacity exceeded; retry after pending work completes"))
                return
            cancelled = Event()
            if tracked:
                self.pending[identifier] = cancelled
                if message.get("method") == "initialize":
                    self.initializations.add(identifier)
            self.queue.put_nowait((message, identifier, tracked, cancelled))

    def _run(self) -> None:
        while not self.closed.is_set() or not self.queue.empty():
            try:
                message, identifier, tracked, cancelled = self.queue.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                if not cancelled.is_set():
                    try:
                        response = self.guard.handle(message, "stdio", modern_stdio=True)
                    except Exception:
                        response = rpc_error(identifier if tracked else None, -32603, "Internal error")
                    with self.lock:
                        if response is not None and not cancelled.is_set():
                            self.emit(response)
            finally:
                with self.lock:
                    if tracked:
                        self.pending.pop(identifier, None)
                        self.initializations.discard(identifier)
                self.slots.release()
                self.queue.task_done()

    def close(self) -> None:
        self.closed.set()
        self.worker.join(timeout=5)
        if self.worker.is_alive():
            with self.lock:
                for event in self.pending.values():
                    event.set()


def serve_stdio(guard: RuntimeGuard) -> None:
    output_lock = Lock()

    def emit(response: dict[str, Any]) -> None:
        with output_lock:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()

    dispatcher = StdioDispatcher(guard, emit)
    try:
        while True:
            line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
            if not line:
                break
            if len(line) > MAX_MESSAGE:
                while line and not line.endswith(b"\n"):
                    line = sys.stdin.buffer.readline(65536)
                emit(rpc_error(None, -32600, "Request too large"))
            else:
                try:
                    dispatcher.submit(parse_json_request(line))
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    emit(rpc_error(None, -32700, "Parse error"))
    finally:
        dispatcher.close()


def serve_http(guard: RuntimeGuard, host: str, port: int, auth_token: str | None) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"} and not auth_token:
        raise ValueError("Non-loopback HTTP bind requires RUNTIME_GUARD_AUTH_TOKEN")

    class Handler(BaseHTTPRequestHandler):
        server_version = "runtime-guard-mcp/0.1"

        def log_message(self, _format: str, *_args: Any) -> None:
            pass

        def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
            # BaseHTTPRequestHandler's diagnostic can contain untrusted request data.
            self.close_connection = True
            if self.request_version == "HTTP/0.9":
                self.request_version = "HTTP/1.0"
            self._json(code, {"error": self.responses.get(code, ("HTTP error",))[0]})

        def _json(self, status: int, payload: dict[str, Any] | None) -> None:
            raw = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else b""
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                if raw and self.command != "HEAD":
                    self.wfile.write(raw)
            except OSError:
                # A peer may disconnect, including when the absolute deadline closes it.
                pass

        def do_GET(self) -> None:
            self._json(405, {"error": "GET streaming is not supported"})

        def do_POST(self) -> None:
            if self.path != "/mcp":
                self._json(404, {"error": "Not found"})
                return
            hosts = self.headers.get_all("Host", [])
            if len(hosts) != 1:
                self._json(400, {"error": "Invalid Host header"})
                return
            try:
                parsed_host = urlparse("http://" + hosts[0])
                request_host = parsed_host.hostname
                _ = parsed_host.port
            except ValueError:
                self._json(400, {"error": "Invalid Host header"})
                return
            if parsed_host.username or parsed_host.password or parsed_host.path or parsed_host.query or parsed_host.fragment:
                self._json(400, {"error": "Invalid Host header"})
                return
            if request_host not in {"localhost", "127.0.0.1", "::1", host}:
                self._json(403, {"error": "Host denied"})
                return
            origins = self.headers.get_all("Origin", [])
            if len(origins) > 1:
                self._json(400, {"error": "Invalid Origin header"})
                return
            origin = origins[0] if origins else None
            if origin:
                try:
                    parsed_origin = urlparse(origin)
                    origin_host = parsed_origin.hostname
                    _ = parsed_origin.port
                except ValueError:
                    self._json(400, {"error": "Invalid Origin header"})
                    return
                if parsed_origin.scheme not in {"http", "https"} or parsed_origin.username or parsed_origin.password or parsed_origin.path or parsed_origin.query or parsed_origin.fragment:
                    self._json(400, {"error": "Invalid Origin header"})
                    return
                if origin_host not in {"localhost", "127.0.0.1", "::1", host}:
                    self._json(403, {"error": "Origin denied"})
                    return
            auth_headers = self.headers.get_all("Authorization", [])
            if len(auth_headers) > 1:
                self._json(400, {"error": "Invalid Authorization header"})
                return
            if auth_token and (not auth_headers or not hmac.compare_digest(auth_headers[0].encode("utf-8"), ("Bearer " + auth_token).encode("utf-8"))):
                self._json(401, {"error": "Unauthorized"})
                return
            if self.headers.get_all("Transfer-Encoding"):
                self._json(400, {"error": "Transfer encoding is not supported"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not lengths[0].strip().isascii() or not lengths[0].strip().isdecimal():
                self._json(400, {"error": "Invalid length"})
                return
            media_types = self.headers.get_all("Content-Type", [])
            if len(media_types) != 1 or media_types[0].split(";", 1)[0].strip().lower() != "application/json":
                self._json(415, {"error": "Content type must be application/json"})
                return
            if len(lengths[0].strip()) > 10:
                self._json(413, {"error": "Request too large"})
                return
            length = int(lengths[0].strip())
            if not 0 < length <= MAX_MESSAGE:
                self._json(413, {"error": "Request too large"})
                return
            try:
                raw = self.rfile.read(length)
            except OSError:
                self._json(400, {"error": "Incomplete request body"})
                return
            if len(raw) != length:
                self._json(400, {"error": "Incomplete request body"})
                return
            try:
                message = parse_json_request(raw)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._json(200, rpc_error(None, -32700, "Parse error"))
                return
            response = guard.handle(message, "http")
            self._json(202 if response is None else 200, response)

    BoundedHTTPServer((host, port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Runtime Guard MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--workspace-root", default=os.environ.get("RUNTIME_GUARD_WORKSPACE_ROOT", os.getcwd()))
    parser.add_argument("--host", default=os.environ.get("RUNTIME_GUARD_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("RUNTIME_GUARD_PORT", "8765")))
    parser.add_argument("--config", default=os.environ.get("RUNTIME_GUARD_CONFIG"))
    args = parser.parse_args()
    config = {}
    if args.config:
        try:
            with open(args.config, "rb") as source:
                raw_config = source.read(MAX_MESSAGE + 1)
            if len(raw_config) > MAX_MESSAGE:
                raise ValueError("Configuration too large")
            config = parse_json_request(raw_config)
        except (OSError, ValueError, UnicodeDecodeError):
            parser.error("Cannot read config: use valid UTF-8 JSON without duplicate keys or non-finite numbers, within the request size and structure limits")
        if not isinstance(config, dict) or set(config) - {"workspace_root", "allowed_roots", "enabled_tools", "token_hour", "payload_hour", "commands_minute", "audit_db", "audit_max_records"}:
            parser.error("Invalid config keys")
        for key in ("token_hour", "payload_hour", "commands_minute", "audit_max_records"):
            if key in config and (type(config[key]) is not int or config[key] <= 0):
                parser.error(f"{key} must be a positive integer")
        if "workspace_root" in config and (not isinstance(config["workspace_root"], str) or not config["workspace_root"]):
            parser.error("workspace_root must be a path")
        if "audit_db" in config and config["audit_db"] is not None and (not isinstance(config["audit_db"], str) or not config["audit_db"]):
            parser.error("audit_db must be a path or null")
        if "allowed_roots" in config and (not isinstance(config["allowed_roots"], list) or not all(isinstance(p, str) and p for p in config["allowed_roots"])):
            parser.error("allowed_roots must be a list of paths")
        if "enabled_tools" in config and (not isinstance(config["enabled_tools"], list) or not all(isinstance(name, str) for name in config["enabled_tools"]) or not set(config["enabled_tools"]) <= {tool["name"] for tool in TOOLS}):
            parser.error("enabled_tools contains an unknown tool")
    try:
        guard = RuntimeGuard(config.get("workspace_root", args.workspace_root), config.get("token_hour", 100_000), config.get("payload_hour", 50_000_000), config.get("commands_minute", 120), config.get("audit_db"), config.get("allowed_roots"), config.get("enabled_tools"), config.get("audit_max_records", DEFAULT_AUDIT_MAX_RECORDS))
    except (OSError, ValueError, sqlite3.Error, AuditIntegrityError):
        parser.error("Cannot initialize Runtime Guard: verify workspace, audit storage access, capacity and integrity")
    if args.transport == "stdio":
        serve_stdio(guard)
    else:
        serve_http(guard, args.host, args.port, os.environ.get("RUNTIME_GUARD_AUTH_TOKEN"))


if __name__ == "__main__":
    main()

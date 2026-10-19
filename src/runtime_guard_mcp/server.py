"""Small MCP server with stdio and local Streamable HTTP transports."""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore, Timer
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .audit import AuditIntegrityError, AuditLog
from .policy import BudgetState, SecretMasker, audit_path_access, dry_run_command, verdict

PROTOCOL_VERSION = "2025-06-18"
MAX_MESSAGE = 1_048_576
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


class RuntimeGuard:
    def __init__(self, workspace_root: str, token_hour: int = 100_000, payload_hour: int = 50_000_000, commands_minute: int = 120, audit_db: str | None = None, allowed_roots: list[str] | None = None, enabled_tools: list[str] | None = None):
        self.workspace_root = str(Path(workspace_root).expanduser().resolve(strict=False))
        self.allowed_roots = allowed_roots or []
        self.enabled_tools = set(enabled_tools) if enabled_tools is not None else {tool["name"] for tool in TOOLS}
        self.budgets = BudgetState(token_hour, payload_hour, commands_minute)
        self.masker = SecretMasker()
        self.audit = AuditLog(audit_db) if audit_db else None

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
            except (sqlite3.Error, AuditIntegrityError):
                result = verdict("BLOCKED", "AUDIT_UNAVAILABLE", "Restore audit integrity and storage before using this server.")
        return {"content": [{"type": "text", "text": json.dumps(result, separators=(",", ":"))}], "structuredContent": result, "isError": result["status"] == "BLOCKED"}

    def handle(self, message: Any, caller: str = "local") -> dict[str, Any] | None:
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return rpc_error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid Request")
        if "id" not in message:
            return None
        identifier = message["id"]
        if type(identifier) not in {str, int, float, type(None)} or (type(identifier) is float and not math.isfinite(identifier)):
            return rpc_error(None, -32600, "Invalid Request")
        method = message["method"]
        if method == "initialize":
            result = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "runtime-guard-mcp", "version": __version__}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [tool for tool in TOOLS if tool["name"] in self.enabled_tools]}
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
        return {"jsonrpc": "2.0", "id": identifier, "result": result}


def serve_stdio(guard: RuntimeGuard) -> None:
    while True:
        line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
        if not line:
            break
        if len(line) > MAX_MESSAGE:
            # Discard the rest of this frame in bounded pieces before parsing the next one.
            while line and not line.endswith(b"\n"):
                line = sys.stdin.buffer.readline(65536)
            response = rpc_error(None, -32600, "Request too large")
        else:
            try:
                response = guard.handle(json.loads(line), "stdio")
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = rpc_error(None, -32700, "Parse error")
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


def serve_http(guard: RuntimeGuard, host: str, port: int, auth_token: str | None) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"} and not auth_token:
        raise ValueError("Non-loopback HTTP bind requires RUNTIME_GUARD_AUTH_TOKEN")

    class Handler(BaseHTTPRequestHandler):
        server_version = "runtime-guard-mcp/0.1"

        def log_message(self, _format: str, *_args: Any) -> None:
            pass

        def _json(self, status: int, payload: dict[str, Any] | None) -> None:
            raw = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else b""
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                if raw:
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
            if auth_token and (not auth_headers or auth_headers[0] != "Bearer " + auth_token):
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
                message = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
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
        with open(args.config, encoding="utf-8") as source:
            config = json.load(source)
        if not isinstance(config, dict) or set(config) - {"workspace_root", "allowed_roots", "enabled_tools", "token_hour", "payload_hour", "commands_minute", "audit_db"}:
            parser.error("Invalid config keys")
        for key in ("token_hour", "payload_hour", "commands_minute"):
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
    guard = RuntimeGuard(config.get("workspace_root", args.workspace_root), config.get("token_hour", 100_000), config.get("payload_hour", 50_000_000), config.get("commands_minute", 120), config.get("audit_db"), config.get("allowed_roots"), config.get("enabled_tools"))
    if args.transport == "stdio":
        serve_stdio(guard)
    else:
        serve_http(guard, args.host, args.port, os.environ.get("RUNTIME_GUARD_AUTH_TOKEN"))


if __name__ == "__main__":
    main()

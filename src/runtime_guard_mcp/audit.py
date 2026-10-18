"""Optional redacted decision audit; no payloads, paths, commands, or secrets are stored."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time


class AuditLog:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS decisions (time_utc INTEGER NOT NULL, caller_hash TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, rule TEXT NOT NULL)")
        self._db.commit()

    def record(self, caller: str, tool: str, status: str, rule: str) -> None:
        digest = hashlib.sha256(caller.encode()).hexdigest()[:16]
        with self._lock:
            self._db.execute("INSERT INTO decisions VALUES (?, ?, ?, ?, ?)", (int(time.time()), digest, tool, status, rule))
            self._db.commit()

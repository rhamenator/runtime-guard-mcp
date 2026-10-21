"""Optional redacted decision audit; no payloads, paths, commands, or secrets are stored."""

from __future__ import annotations

from contextlib import closing
import hashlib
import json
import sqlite3
import threading
import time


class AuditIntegrityError(RuntimeError):
    """A previously recorded audit decision has been changed or removed."""


class AuditLog:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS decisions (time_utc INTEGER NOT NULL, caller_hash TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, rule TEXT NOT NULL, prev_hash TEXT, content_hash TEXT)")
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(decisions)")}
        hash_columns = columns & {"prev_hash", "content_hash"}
        if len(hash_columns) == 1:
            self._db.close()
            raise AuditIntegrityError("Incomplete audit hash schema")
        legacy = not hash_columns
        for column in ("prev_hash", "content_hash"):
            if column not in columns:
                self._db.execute(f"ALTER TABLE decisions ADD COLUMN {column} TEXT")
        # Backfill older local audits so subsequent appends have a chain anchor.
        previous = "0" * 64
        with closing(self._db.execute("SELECT rowid, time_utc, caller_hash, tool, status, rule, content_hash FROM decisions ORDER BY rowid")) as rows:
            for rowid, timestamp, caller, tool, status, rule, current_hash in rows:
                if legacy:
                    current_hash = self._hash(previous, timestamp, caller, tool, status, rule)
                    self._db.execute("UPDATE decisions SET prev_hash = ?, content_hash = ? WHERE rowid = ?", (previous, current_hash, rowid))
                previous = current_hash
        self._db.commit()
        if not self.verify_integrity()["valid"]:
            self._db.close()
            raise AuditIntegrityError("Audit integrity check failed at startup")
        self._tip = previous

    @staticmethod
    def _hash(previous: str, timestamp: int, caller: str, tool: str, status: str, rule: str) -> str:
        payload = json.dumps([previous, timestamp, caller, tool, status, rule], separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def record(self, caller: str, tool: str, status: str, rule: str) -> None:
        digest = hashlib.sha256(caller.encode()).hexdigest()[:16]
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                previous = self._db.execute("SELECT time_utc, caller_hash, tool, status, rule, prev_hash, content_hash FROM decisions ORDER BY rowid DESC LIMIT 1").fetchone()
                if previous and previous[6] != self._hash(previous[5], *previous[:5]):
                    raise AuditIntegrityError("Latest audit record failed integrity check")
                previous_hash = previous[6] if previous else "0" * 64
                if previous_hash != self._tip:
                    raise AuditIntegrityError("Audit tip changed outside this process")
                timestamp = int(time.time())
                content_hash = self._hash(previous_hash, timestamp, digest, tool, status, rule)
                self._db.execute("INSERT INTO decisions (time_utc, caller_hash, tool, status, rule, prev_hash, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?)", (timestamp, digest, tool, status, rule, previous_hash, content_hash))
                self._db.commit()
                self._tip = content_hash
            except (sqlite3.Error, AuditIntegrityError):
                try:
                    self._db.rollback()
                except sqlite3.Error:
                    pass
                raise

    def verify_integrity(self) -> dict[str, int | bool | None]:
        # Keep the scan and hash checks within the writer lock, without retaining
        # the table in Python memory. Closing the cursor also releases early exits.
        with self._lock:
            with closing(self._db.execute("SELECT rowid, time_utc, caller_hash, tool, status, rule, prev_hash, content_hash FROM decisions ORDER BY rowid")) as rows:
                previous = "0" * 64
                checked = 0
                for rowid, timestamp, caller, tool, status, rule, prev_hash, content_hash in rows:
                    if prev_hash != previous or content_hash != self._hash(previous, timestamp, caller, tool, status, rule):
                        return {"valid": False, "records_checked": checked, "failed_rowid": rowid}
                    previous = content_hash
                    checked += 1
                return {"valid": True, "records_checked": checked, "failed_rowid": None}

"""Optional redacted decision audit; no payloads, paths, commands, or secrets are stored."""

from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time


AUDIT_BUSY_TIMEOUT_SECONDS = 0.25
DEFAULT_AUDIT_MAX_RECORDS = 100_000
DEFAULT_AUDIT_MAX_DB_BYTES = 64 * 1024 * 1024
DEFAULT_AUDIT_WAL_CHECKPOINT_BYTES = 4 * 1024 * 1024


class AuditIntegrityError(RuntimeError):
    """A previously recorded audit decision has been changed or removed."""


class AuditCapacityError(RuntimeError):
    """The configured audit record limit has been reached; no rows are removed."""


class AuditWalCapacityError(AuditCapacityError):
    """WAL reclamation is required before admitting another audit write."""


class AuditLog:
    def __init__(self, path: str, max_records: int = DEFAULT_AUDIT_MAX_RECORDS, max_db_bytes: int = DEFAULT_AUDIT_MAX_DB_BYTES, wal_checkpoint_bytes: int = DEFAULT_AUDIT_WAL_CHECKPOINT_BYTES):
        if type(max_records) is not int or max_records <= 0:
            raise ValueError("audit_max_records must be a positive integer")
        if type(max_db_bytes) is not int or max_db_bytes < 8192:
            raise ValueError("audit_max_db_bytes must be at least 8192")
        if type(wal_checkpoint_bytes) is not int or wal_checkpoint_bytes < 4096:
            raise ValueError("audit_wal_checkpoint_bytes must be at least 4096")
        self.wal_checkpoint_bytes = wal_checkpoint_bytes
        self.max_records = max_records
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, timeout=AUDIT_BUSY_TIMEOUT_SECONDS, check_same_thread=False)
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            page_size = self._db.execute("PRAGMA page_size").fetchone()[0]
            max_pages = max_db_bytes // page_size
            if max_pages < 2 or self._db.execute(f"PRAGMA max_page_count={max_pages}").fetchone()[0] != max_pages:
                raise ValueError("Existing audit exceeds configured database page ceiling")
            filename = self._db.execute("PRAGMA database_list").fetchone()[2]
            self._wal_path = Path(filename + "-wal") if filename else None
            self._db.execute(f"PRAGMA journal_size_limit={wal_checkpoint_bytes}")
            self._check_wal_capacity()
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("CREATE TABLE IF NOT EXISTS decisions (time_utc INTEGER NOT NULL, caller_hash TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, rule TEXT NOT NULL, prev_hash TEXT, content_hash TEXT)")
            columns = {row[1] for row in self._db.execute("PRAGMA table_info(decisions)")}
            hash_columns = columns & {"prev_hash", "content_hash"}
            if len(hash_columns) == 1:
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
            integrity = self.verify_integrity()
            if not integrity["valid"]:
                raise AuditIntegrityError("Audit integrity check failed at startup")
            self._db.commit()
            self._tip = previous
            self._records = integrity["records_checked"]
        except BaseException:
            # Closing rolls back schema/backfill writes, even on interrupted startup.
            self._db.close()
            raise

    def _check_wal_capacity(self) -> None:
        # A high-water admission check, not an exact filesystem byte quota.
        if self._wal_path is None:
            return
        try:
            size = self._wal_path.stat().st_size
        except FileNotFoundError:
            return
        except OSError:
            raise sqlite3.OperationalError("Cannot inspect audit WAL") from None
        if size >= self.wal_checkpoint_bytes:
            busy, _, _ = self._db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if busy:
                raise AuditWalCapacityError("Release audit readers before admitting more writes")

    @staticmethod
    def _hash(previous: str, timestamp: int, caller: str, tool: str, status: str, rule: str) -> str:
        payload = json.dumps([previous, timestamp, caller, tool, status, rule], separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def record(self, caller: str, tool: str, status: str, rule: str) -> None:
        digest = hashlib.sha256(caller.encode()).hexdigest()[:16]
        with self._lock:
            if self._records >= self.max_records:
                raise AuditCapacityError("Audit record capacity exhausted")
            self._check_wal_capacity()
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
                self._records += 1
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

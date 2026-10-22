"""Bounded stdio transport I/O; blocked raw descriptor threads are daemonized."""
import os
import queue
import time
from threading import Event, Lock, Thread

OUTPUT_BYTES = 16 * 1024 * 1024
OUTPUT_DEADLINE = 5.0


class StdioOutput:
    def __init__(self, fd, max_bytes=OUTPUT_BYTES, deadline=OUTPUT_DEADLINE):
        self.fd, self.max_bytes, self.deadline = fd, max_bytes, deadline
        self.queue = queue.Queue(maxsize=32)
        self.lock = Lock()
        self.failed, self.closed = Event(), Event()
        self.bytes = 0
        self.started = None
        self.worker = Thread(target=self._run, daemon=True)
        self.worker.start()

    def emit(self, raw, cancelled=None, complete=None):
        with self.lock:
            if self.failed.is_set() or self.closed.is_set():
                return False
            if self.bytes + len(raw) > self.max_bytes:
                self.failed.set()
                return False
            self.bytes += len(raw)
            try:
                self.queue.put_nowait((raw, cancelled, complete))
            except queue.Full:
                self.bytes -= len(raw)
                self.failed.set()
                return False
            return True

    def healthy(self):
        with self.lock:
            if self.started is not None and time.monotonic() - self.started >= self.deadline:
                self.failed.set()
        return not self.failed.is_set()

    def _run(self):
        while not self.failed.is_set() and (not self.closed.is_set() or not self.queue.empty()):
            try:
                raw, cancelled, complete = self.queue.get(timeout=.05)
            except queue.Empty:
                continue
            with self.lock:
                self.started = time.monotonic()
            try:
                if cancelled is not None and cancelled.is_set():
                    continue
                remaining = memoryview(raw)
                while remaining:
                    size = os.write(self.fd, remaining)
                    if size <= 0:
                        raise OSError('Output disconnected')
                    remaining = remaining[size:]
            except OSError:
                self.failed.set()
                return
            finally:
                with self.lock:
                    self.bytes -= len(raw)
                    self.started = None
                self.queue.task_done()
                if complete is not None:
                    complete()
                raw = remaining = cancelled = complete = None

    def close(self):
        self.closed.set()
        if not self.failed.is_set():
            # Poll the same per-frame deadline during final draining.
            end = time.monotonic() + self.deadline
            while self.worker.is_alive() and self.healthy() and time.monotonic() < end:
                self.worker.join(timeout=.05)
            if self.worker.is_alive():
                self.failed.set()
        return not self.failed.is_set()


def read_frames(fd, frames, stopped, max_message):
    """One bounded queued frame plus one bounded assembly buffer, including drains."""
    buffer = bytearray()
    oversized = False

    def put(value):
        while not stopped.is_set():
            try:
                frames.put(value, timeout=.05)
                return True
            except queue.Full:
                pass
        return False

    try:
        while not stopped.is_set():
            chunk = os.read(fd, 65536)
            if not chunk:
                if buffer or oversized:
                    put(False if oversized else bytes(buffer))
                put(None)
                return
            for part in chunk.splitlines(keepends=True):
                # Only LF terminates the wire frame (splitlines also splits CR).
                if not oversized:
                    buffer.extend(part)
                    if len(buffer) > max_message:
                        oversized = True
                        buffer.clear()
                if part.endswith(b'\n'):
                    if not put(False if oversized else bytes(buffer)):
                        return
                    buffer.clear()
                    oversized = False
    except OSError:
        put(None)

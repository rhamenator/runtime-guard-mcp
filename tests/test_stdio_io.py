import os
import queue
import threading
import unittest
from runtime_guard_mcp.stdio import StdioOutput, read_frames


class StdioIOTests(unittest.TestCase):
    def test_frame_limit_drains_and_recovers_without_losing_eof_tail(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b'123456789\n{}\r\nlast')
            os.close(write_fd)
            write_fd = None
            frames = queue.Queue(maxsize=8)
            read_frames(read_fd, frames, threading.Event(), 8)
            self.assertEqual([frames.get_nowait() for _ in range(4)], [False, b'{}\r\n', b'last', None])
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)

    def test_output_byte_ceiling_rejects_before_enqueue(self):
        read_fd, write_fd = os.pipe()
        output = StdioOutput(write_fd, max_bytes=4)
        try:
            output.emit(b'12345')
            self.assertFalse(output.healthy())
            self.assertEqual(output.bytes, 0)
            self.assertTrue(output.queue.empty())
            self.assertFalse(output.close())
        finally:
            output.worker.join(timeout=1)
            os.close(write_fd)
            os.close(read_fd)

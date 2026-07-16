import json
import tempfile
import threading
import unittest
from pathlib import Path

import server


class TestSessionPersistence(unittest.TestCase):
    def test_write_json_is_atomic_under_concurrent_writers(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "session.json"
            errors = []

            def writer(index):
                try:
                    server.write_json(target, {"id": "session", "writer": index, "messages": [index] * 20})
                except Exception as exc:  # pragma: no cover - assertion reports details
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(index,)) for index in range(12)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["id"], "session")
            self.assertEqual(len(data["messages"]), 20)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    # ── JSONL-specific tests ──────────────────────────────────────

    def test_write_jsonl_atomic(self):
        """write_jsonl is atomic (temp+replace) — no corruption under concurrent writers."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "session.jsonl"
            errors = []

            def writer(index):
                try:
                    msgs = [{"role": "user", "content": f"msg-{index}-{i}"} for i in range(20)]
                    server.write_jsonl(target, msgs)
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(index,)) for index in range(12)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            msgs = server.read_jsonl(target)
            self.assertEqual(len(msgs), 20, "Should have exactly 20 messages (one writer wins)")
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_append_jsonl_concurrent(self):
        """append_jsonl: concurrent appends should preserve all messages."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "session.jsonl"
            errors = []

            def appender(prefix, count):
                try:
                    msgs = [{"role": "user", "content": f"{prefix}-{i}"} for i in range(count)]
                    server.append_jsonl(target, msgs)
                except Exception as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=appender, args=(f"t{t}", 10))
                for t in range(5)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            msgs = server.read_jsonl(target)
            self.assertEqual(len(msgs), 50, "5 threads x 10 messages = 50")

    def test_read_jsonl_corrupted_last_line(self):
        """read_jsonl skips a corrupted/partial last line (simulated crash)."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "crash.jsonl"
            target.write_text(
                '{"role":"user","content":"msg1"}\n'
                '{"role":"assistant","content":"msg2"}\n'
                '{"role":"assistant","conte',  # incomplete — power loss mid-write
                encoding="utf-8",
            )
            msgs = server.read_jsonl(target)
            self.assertEqual(len(msgs), 2, "Should recover first 2 intact lines, skip partial")

    def test_read_jsonl_empty_and_missing(self):
        """read_jsonl returns [] for missing or empty file."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(server.read_jsonl(Path(tmp) / "nope.jsonl"), [])
            empty = Path(tmp) / "empty.jsonl"
            empty.write_text("", encoding="utf-8")
            self.assertEqual(server.read_jsonl(empty), [])

    def test_read_jsonl_skips_blank_lines(self):
        """read_jsonl skips blank lines between messages."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "blanks.jsonl"
            target.write_text(
                '{"role":"user","content":"a"}\n'
                '\n'
                '{"role":"assistant","content":"b"}\n'
                '\n\n',
                encoding="utf-8",
            )
            msgs = server.read_jsonl(target)
            self.assertEqual(len(msgs), 2)

    def test_count_jsonl_lines(self):
        """count_jsonl_lines returns correct count without parsing JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "count.jsonl"
            self.assertEqual(server.count_jsonl_lines(target), 0)
            for i in range(100):
                server.append_jsonl(target, [{"role": "user", "content": str(i)}])
            self.assertEqual(server.count_jsonl_lines(target), 100)

    def test_read_last_jsonl_line(self):
        """read_last_jsonl_line returns the last message's parsed JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "last.jsonl"
            self.assertIsNone(server.read_last_jsonl_line(target))
            server.write_jsonl(target, [
                {"role": "user", "content": "first", "_time": "2026-01-01T00:00:00"},
                {"role": "assistant", "content": "last", "_time": "2026-07-15T12:00:00"},
            ])
            last = server.read_last_jsonl_line(target)
            self.assertEqual(last["content"], "last")
            self.assertEqual(last["_time"], "2026-07-15T12:00:00")

    def test_messages_path(self):
        """messages_path returns the correct .jsonl path."""
        p = server.messages_path("abc123def456")
        self.assertTrue(p.name.endswith(".jsonl"))
        self.assertIn("abc123def456", str(p))


if __name__ == "__main__":
    unittest.main()

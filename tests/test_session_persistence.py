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


if __name__ == "__main__":
    unittest.main()

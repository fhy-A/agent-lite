"""Integration checks for Code's rich file preview pipeline."""

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server as server_mod


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestRichPreviews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_root = tempfile.TemporaryDirectory(prefix="code_preview_root_")
        cls.temp_data = tempfile.TemporaryDirectory(prefix="code_preview_data_")
        cls.root = Path(cls.temp_root.name)
        cls.data = Path(cls.temp_data.name)

        cls.png_bytes = b"\x89PNG\r\n\x1a\n" + (b"preview" * 8)
        cls.pdf_bytes = b"%PDF-1.4\n% Code preview fixture\n%%EOF\n"
        (cls.root / "sample.png").write_bytes(cls.png_bytes)
        (cls.root / "sample.pdf").write_bytes(cls.pdf_bytes)
        (cls.root / "sample.md").write_text("# Preview\n\n**Rendered** content.\n", encoding="utf-8")
        (cls.root / "sample.csv").write_text(
            'name,note\nAlice,"hello, world"\nBob,"two\nlines"\n', encoding="utf-8"
        )

        for name in ("sessions", "memory", "skills", "attachments", "file-backups"):
            (cls.data / name).mkdir(parents=True, exist_ok=True)
        config_path = cls.data / "config.json"
        config_path.write_text(
            json.dumps({"projectRoot": str(cls.root), "userHome": str(Path.home())}),
            encoding="utf-8",
        )

        cls.patchers = [
            mock.patch.object(server_mod, "DATA_DIR", cls.data),
            mock.patch.object(server_mod, "CONFIG_PATH", config_path),
            mock.patch.object(server_mod, "SESSIONS_DIR", cls.data / "sessions"),
            mock.patch.object(server_mod, "MEMORY_DIR", cls.data / "memory"),
            mock.patch.object(server_mod, "SKILLS_DIR", cls.data / "skills"),
            mock.patch.object(server_mod, "ATTACHMENTS_DIR", cls.data / "attachments"),
            mock.patch.object(server_mod, "FILE_BACKUP_DIR", cls.data / "file-backups"),
            mock.patch.object(server_mod, "APP_DIR", cls.root),
        ]
        for patcher in cls.patchers:
            patcher.start()

        cls.port = free_port()
        cls.httpd = server_mod.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), server_mod.CodeHandler
        )
        cls.httpd.daemon_threads = True
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        for patcher in reversed(cls.patchers):
            patcher.stop()
        cls.temp_root.cleanup()
        cls.temp_data.cleanup()

    @classmethod
    def request_file(cls, path, raw=False):
        query = urllib.parse.urlencode({"path": path, **({"raw": "1"} if raw else {})})
        return urllib.request.urlopen(
            f"http://127.0.0.1:{cls.port}/api/file?{query}", timeout=5
        )

    def test_image_and_pdf_raw_responses_are_inline_byte_streams(self):
        for name, expected_type, expected_body in (
            ("sample.png", "image/png", self.png_bytes),
            ("sample.pdf", "application/pdf", self.pdf_bytes),
        ):
            with self.subTest(name=name), self.request_file(name, raw=True) as response:
                self.assertEqual(response.headers.get_content_type(), expected_type)
                self.assertTrue(response.headers["Content-Disposition"].startswith("inline;"))
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.read(), expected_body)

    def test_binary_metadata_and_text_preview_contracts(self):
        with self.request_file("sample.png") as response:
            image = json.loads(response.read())
        self.assertTrue(image["binary"])
        self.assertEqual(image["mime"], "image/png")

        with self.request_file("sample.md") as response:
            markdown = json.loads(response.read())
        self.assertFalse(markdown["binary"])
        self.assertIn("# Preview", markdown["content"])

        with self.request_file("sample.csv") as response:
            csv_data = json.loads(response.read())
        self.assertFalse(csv_data["binary"])
        self.assertIn('Alice,"hello, world"', csv_data["content"])

    def test_frontend_contains_all_four_rich_preview_renderers(self):
        app_dir = Path(__file__).resolve().parent.parent
        script = (app_dir / "app.js").read_text(encoding="utf-8")
        markup = (app_dir / "index.html").read_text(encoding="utf-8")
        styles = (app_dir / "styles.css").read_text(encoding="utf-8")

        for marker in (
            "renderImagePreview(",
            "renderMarkdownPreview(",
            "renderPdfPreview(",
            "renderDelimitedPreview(",
            "parseDelimitedText(",
        ):
            self.assertIn(marker, script)
        self.assertIn('id="previewModeActions"', markup)
        self.assertIn(".markdown-preview", styles)
        self.assertIn(".preview-table-scroll", styles)
        self.assertIn(".preview-pdf-frame", styles)


if __name__ == "__main__":
    unittest.main()

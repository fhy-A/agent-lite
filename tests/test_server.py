"""
Tests for server.py pure functions.
Run: python -m unittest tests.test_server -v
   or: python tests/test_server.py
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


class TestSanitizeFilename(unittest.TestCase):
    def test_normal_name(self):
        self.assertEqual(server.sanitize_filename("hello.txt"), "hello.txt")

    def test_strips_path_separators(self):
        # Path().name extracts only the last component
        result = server.sanitize_filename(r"foo\bar/baz.txt")
        self.assertEqual(result, "baz.txt")

    def test_replaces_angle_brackets(self):
        self.assertEqual(server.sanitize_filename("<evil>.txt"), "_evil_.txt")

    def test_replaces_colon(self):
        # Path().name strips the drive letter prefix (C:)
        self.assertEqual(server.sanitize_filename("C:file.txt"), "file.txt")

    def test_replaces_quote_and_pipe(self):
        self.assertEqual(server.sanitize_filename('a"b|c.txt'), "a_b_c.txt")

    def test_replaces_question_mark(self):
        self.assertEqual(server.sanitize_filename("what?.txt"), "what_.txt")

    def test_replaces_asterisk(self):
        self.assertEqual(server.sanitize_filename("*.txt"), "_.txt")

    def test_truncates_long_name(self):
        long_name = "x" * 200 + ".txt"
        result = server.sanitize_filename(long_name)
        self.assertEqual(len(result), 120)
        # Truncation at 120 chars cuts the extension; only verify length

    def test_empty_returns_attachment(self):
        self.assertEqual(server.sanitize_filename(""), "attachment")

    def test_none_returns_attachment(self):
        self.assertEqual(server.sanitize_filename(None), "attachment")

    def test_whitespace_only(self):
        self.assertEqual(server.sanitize_filename("   "), "attachment")


class TestSafeMemoryName(unittest.TestCase):
    def test_valid_simple(self):
        self.assertEqual(server.safe_memory_name("my-config_v2"), "my-config_v2")

    def test_valid_only_letters(self):
        self.assertEqual(server.safe_memory_name("abcdef"), "abcdef")

    def test_valid_max_length(self):
        self.assertEqual(server.safe_memory_name("a" * 64), "a" * 64)

    def test_invalid_empty(self):
        with self.assertRaisesRegex(ValueError, "invalid memory name"):
            server.safe_memory_name("")

    def test_invalid_none(self):
        with self.assertRaisesRegex(ValueError, "invalid memory name"):
            server.safe_memory_name(None)

    def test_invalid_too_long(self):
        with self.assertRaisesRegex(ValueError, "invalid memory name"):
            server.safe_memory_name("a" * 65)

    def test_invalid_special_chars(self):
        with self.assertRaisesRegex(ValueError, "invalid memory name"):
            server.safe_memory_name("hello world")

    def test_invalid_dot(self):
        with self.assertRaisesRegex(ValueError, "invalid memory name"):
            server.safe_memory_name("file.md")


class TestSafeSessionId(unittest.TestCase):
    def test_valid_min_length(self):
        self.assertEqual(server.safe_session_id("abcd1234"), "abcd1234")

    def test_valid_long(self):
        self.assertEqual(server.safe_session_id("a" * 64), "a" * 64)

    def test_invalid_too_short(self):
        with self.assertRaisesRegex(ValueError, "invalid session id"):
            server.safe_session_id("abc")

    def test_invalid_empty(self):
        with self.assertRaisesRegex(ValueError, "invalid session id"):
            server.safe_session_id("")

    def test_invalid_none(self):
        with self.assertRaisesRegex(ValueError, "invalid session id"):
            server.safe_session_id(None)

    def test_invalid_special_chars(self):
        with self.assertRaisesRegex(ValueError, "invalid session id"):
            server.safe_session_id("session@id!")

    def test_invalid_too_long(self):
        with self.assertRaisesRegex(ValueError, "invalid session id"):
            server.safe_session_id("a" * 65)


class TestIsProbablyText(unittest.TestCase):
    def test_plain_text(self):
        self.assertTrue(server.is_probably_text(b"hello world"))

    def test_json_bytes(self):
        self.assertTrue(server.is_probably_text(b'{"key": "value"}'))

    def test_utf8_encoded(self):
        self.assertTrue(server.is_probably_text("你好世界".encode("utf-8")))

    def test_binary_null_early(self):
        self.assertFalse(server.is_probably_text(b"foo\x00bar"))

    def test_binary_null_at_4095(self):
        data = b"A" * 4095 + b"\x00"
        self.assertFalse(server.is_probably_text(data))

    def test_binary_null_at_4097(self):
        data = b"A" * 4097 + b"\x00"
        self.assertTrue(server.is_probably_text(data))

    def test_empty_bytes(self):
        self.assertTrue(server.is_probably_text(b""))


class TestIsSafeCommand(unittest.TestCase):
    def test_dir_is_safe(self):
        ok, _ = server.is_safe_command("dir")
        self.assertTrue(ok)

    def test_dir_with_path(self):
        ok, _ = server.is_safe_command("dir C:\\Users")
        self.assertTrue(ok)

    def test_git_status(self):
        ok, _ = server.is_safe_command("git status")
        self.assertTrue(ok)

    def test_git_log(self):
        ok, _ = server.is_safe_command("git log --oneline")
        self.assertTrue(ok)

    def test_docker_compose_ps(self):
        ok, _ = server.is_safe_command("docker compose ps")
        self.assertTrue(ok)

    def test_python_m_pytest(self):
        ok, _ = server.is_safe_command("python -m pytest tests/ -v")
        self.assertTrue(ok)

    def test_npm_test(self):
        ok, _ = server.is_safe_command("npm test")
        self.assertTrue(ok)

    def test_empty_is_unsafe(self):
        ok, msg = server.is_safe_command("")
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)

    def test_del_is_blocked(self):
        ok, _ = server.is_safe_command("del file.txt")
        self.assertFalse(ok)

    def test_rm_is_blocked(self):
        ok, _ = server.is_safe_command("rm file.txt")
        self.assertFalse(ok)

    def test_pipe_is_blocked(self):
        ok, _ = server.is_safe_command("dir | findstr test")
        self.assertFalse(ok)

    def test_redirect_is_blocked(self):
        ok, _ = server.is_safe_command("dir > output.txt")
        self.assertFalse(ok)

    def test_semicolon_is_blocked(self):
        ok, _ = server.is_safe_command("dir; del file.txt")
        self.assertFalse(ok)

    def test_python_c_is_blocked(self):
        ok, _ = server.is_safe_command("python -c 'print(1)'")
        self.assertFalse(ok)

    def test_node_e_is_blocked(self):
        ok, _ = server.is_safe_command("node -e 'console.log(1)'")
        self.assertFalse(ok)

    def test_unknown_prefix_is_unsafe(self):
        ok, _ = server.is_safe_command("format C:")
        self.assertFalse(ok)

    def test_findstr_is_safe(self):
        ok, _ = server.is_safe_command("findstr /n test server.py")
        self.assertTrue(ok)

    def test_get_childitem_is_safe(self):
        ok, _ = server.is_safe_command("Get-ChildItem . -Recurse")
        self.assertTrue(ok)

    def test_npx_is_safe(self):
        ok, _ = server.is_safe_command("npx jest")
        self.assertTrue(ok)


class TestParseMemoryFrontmatter(unittest.TestCase):
    def test_with_frontmatter(self):
        text = "---\nname: test-memory\ndescription: A test\n---\n\nThis is the body."
        meta, body = server.parse_memory_frontmatter(text)
        self.assertEqual(meta, {"name": "test-memory", "description": "A test"})
        self.assertEqual(body, "This is the body.")

    def test_no_frontmatter(self):
        text = "Just a plain body without frontmatter."
        meta, body = server.parse_memory_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_empty_frontmatter(self):
        # Adjacent --- with nothing between doesn't match the regex
        text = "---\n---\n\nBody here."
        meta, body = server.parse_memory_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_frontmatter_no_trailing_newline(self):
        text = "---\nkey: value\n---\nBody"
        meta, body = server.parse_memory_frontmatter(text)
        self.assertEqual(meta, {"key": "value"})
        self.assertEqual(body, "Body")

    def test_frontmatter_multiline_body(self):
        text = "---\ntitle: Multi\n---\n\nLine 1\nLine 2\n\nLine 3"
        meta, body = server.parse_memory_frontmatter(text)
        self.assertEqual(meta, {"title": "Multi"})
        self.assertIn("Line 1", body)
        self.assertIn("Line 3", body)

    def test_looks_like_frontmatter_but_not_at_start(self):
        text = "Some text\n---\nkey: value\n---\nBody"
        meta, body = server.parse_memory_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)


class TestBuildMemoryFile(unittest.TestCase):
    def test_basic(self):
        result = server.build_memory_file(
            {"name": "test", "description": "A test memory"},
            "This is the body content."
        )
        expected = (
            "---\n"
            "name: test\n"
            "description: A test memory\n"
            "---\n"
            "\n"
            "This is the body content."
        )
        self.assertEqual(result, expected)

    def test_empty_meta(self):
        result = server.build_memory_file({}, "body")
        self.assertEqual(result, "---\n---\n\nbody")

    def test_empty_body(self):
        result = server.build_memory_file({"key": "val"}, "")
        self.assertEqual(result, "---\nkey: val\n---\n\n")

    def test_roundtrip(self):
        meta = {"name": "rt", "description": "roundtrip test", "type": "note"}
        body = "Line 1\nLine 2"
        built = server.build_memory_file(meta, body)
        parsed_meta, parsed_body = server.parse_memory_frontmatter(built)
        self.assertEqual(parsed_meta, meta)
        self.assertEqual(parsed_body, body)


class TestMakeUnifiedDiff(unittest.TestCase):
    def test_no_change(self):
        diff = server.make_unified_diff("abc", "abc", "file.txt")
        self.assertEqual(diff, "")

    def test_add_line(self):
        diff = server.make_unified_diff("line1\n", "line1\nline2\n", "test.txt")
        self.assertIn("+++ b/test.txt", diff)
        self.assertIn("+line2", diff)

    def test_remove_line(self):
        diff = server.make_unified_diff("line1\nline2\n", "line1\n", "test.txt")
        self.assertIn("--- a/test.txt", diff)
        self.assertIn("-line2", diff)

    def test_modify_line(self):
        diff = server.make_unified_diff("old\n", "new\n", "test.txt")
        self.assertIn("-old", diff)
        self.assertIn("+new", diff)


class TestNowIso(unittest.TestCase):
    def test_returns_string(self):
        self.assertIsInstance(server.now_iso(), str)

    def test_valid_iso_format(self):
        result = server.now_iso()
        self.assertIsNotNone(
            re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", result),
            f"Expected ISO 8601 format, got: {result}"
        )


class TestToProjectRelative(unittest.TestCase):
    def test_posix_path(self):
        root = Path("/home/user/project")
        target = Path("/home/user/project/sub/dir/file.py")
        result = server.to_project_relative(root, target)
        self.assertEqual(result, "sub/dir/file.py")

    def test_same_directory(self):
        root = Path("/project")
        target = Path("/project")
        result = server.to_project_relative(root, target)
        self.assertEqual(result, ".")


if __name__ == "__main__":
    unittest.main()

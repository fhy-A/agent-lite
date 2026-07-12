"""
P1 Edit Pipeline Tests — fuzzy matching, propose_edit, apply_edit.

Run: python -m pytest tests/test_edit_pipeline.py -v
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


# ═══════════════════════════════════════════════════════════════════
# 1. _fuzzy_find — 5 strategies
# ═══════════════════════════════════════════════════════════════════

class TestFuzzyFind(unittest.TestCase):

    def setUp(self):
        self.handler = object.__new__(server.AgentLiteHandler)

    # ── Exact match ──
    def test_exact_match(self):
        text = "line1\nline2\nline3\n"
        result = self.handler._fuzzy_find(text, "line2")
        self.assertEqual(result, "line2")

    def test_exact_multiline_match(self):
        text = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        result = self.handler._fuzzy_find(text, "def bar():\n    pass")
        self.assertEqual(result, "def bar():\n    pass")

    def test_line_ending_normalization(self):
        text = "line1\r\nline2\r\nline3\r\n"
        fragment = "line2\n"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("line2", result)

    # ── Single-line: strip match ──
    def test_single_line_stripped_match(self):
        text = "    hello world    \nother line\n"
        fragment = "hello world"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("hello world", result.strip())

    def test_single_line_no_match(self):
        text = "line1\nline2\nline3\n"
        result = self.handler._fuzzy_find(text, "nonexistent")
        self.assertIsNone(result)

    # ── Strategy 1: rstrip match ──
    def test_rstrip_match(self):
        text = "def foo():  \n    return 1  \n\ndef bar():  \n    return 2  \n"
        fragment = "def bar():\n    return 2"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("def bar()", result)

    # ── Strategy 2: tab→space normalization ──
    def test_tab_to_space_match(self):
        text = "def foo():\n\tpass\n"
        fragment = "def foo():\n    pass"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("def foo()", result)

    def test_tab_to_space_in_both(self):
        text = "\tdef foo():\n\t\tpass\n"
        fragment = "    def foo():\n        pass"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)

    # ── Strategy 3: full strip match ──
    def test_full_strip_match(self):
        text = "  line1  \n  line2  \n  line3  \n"
        fragment = "line1\nline2"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("line1", result)

    # ── Strategy 5: difflib approximate match ──
    def test_approximate_match_similar_but_not_exact(self):
        text = "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n"
        fragment = "def add(x, y):\n    return x + y"
        result = self.handler._fuzzy_find(text, fragment)
        # At 65% threshold, this should match the original lines
        self.assertIsNotNone(result)

    def test_approximate_match_no_match_below_threshold(self):
        text = "def add(a, b):\n    return a + b\n"
        fragment = "completely different thing here wow"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNone(result)

    # ── Empty fragment handling ──
    def test_empty_fragment_after_trim(self):
        text = "line1\nline2\n"
        fragment = "\n\n"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNone(result)

    def test_blank_lines_in_fragment_skipped(self):
        text = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        fragment = "def foo():\n\n    pass"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("def foo()", result)

    # ── Leading/trailing empty lines trimmed ──
    def test_leading_empty_line_trimmed(self):
        text = "first\nsecond\nthird\n"
        fragment = "\nsecond\nthird"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("second", result)

    def test_trailing_empty_line_trimmed(self):
        text = "first\nsecond\nthird\n"
        fragment = "first\nsecond\n"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("first", result)


# ═══════════════════════════════════════════════════════════════════
# 2. build_edit_payload — oldText/newText mode
# ═══════════════════════════════════════════════════════════════════

class TestBuildEditPayload(unittest.TestCase):

    def setUp(self):
        self.handler = object.__new__(server.AgentLiteHandler)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Create test file
        self.test_file = self.root / "edit_test.py"
        self.test_file.write_text(
            "def hello():\n    print('hello')\n\n\ndef goodbye():\n    print('goodbye')\n",
            encoding="utf-8",
        )
        # Mock load_config
        patcher = mock.patch.object(server, "load_config", return_value={
            "projectRoot": str(self.root),
            "newApiBaseUrl": "http://localhost:3000",
            "userHome": str(Path.home()),
        })
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    # ── oldText/newText mode ──
    def test_old_text_new_text_exact_replace(self):
        body = {
            "path": "edit_test.py",
            "oldText": "print('hello')",
            "newText": "print('hi')",
        }
        root, target, rel, old_text, new_text, diff = self.handler.build_edit_payload(body)
        self.assertIn("print('hi')", new_text)
        self.assertNotIn("print('hello')", new_text)
        self.assertIn("print('hi')", diff)
        self.assertIn("print('hello')", diff)

    def test_old_text_new_text_same_content_raises(self):
        body = {
            "path": "edit_test.py",
            "oldText": "print('hello')",
            "newText": "print('hello')",
        }
        with self.assertRaises(ValueError):
            self.handler.build_edit_payload(body)

    def test_old_text_not_found_raises(self):
        body = {
            "path": "edit_test.py",
            "oldText": "this does not exist in the file",
            "newText": "replacement",
        }
        with self.assertRaises(ValueError):
            self.handler.build_edit_payload(body)

    # ── newContent mode (full file overwrite) ──
    def test_new_content_mode(self):
        body = {
            "path": "edit_test.py",
            "newContent": "def new_func():\n    return 42\n",
        }
        root, target, rel, old_text, new_text, diff = self.handler.build_edit_payload(body)
        self.assertEqual(new_text, "def new_func():\n    return 42\n")
        self.assertIn("def new_func", new_text)
        self.assertTrue(diff)

    def test_new_content_no_change_raises(self):
        original = self.test_file.read_text(encoding="utf-8")
        body = {
            "path": "edit_test.py",
            "newContent": original,
        }
        with self.assertRaises(ValueError):
            self.handler.build_edit_payload(body)

    # ── Validation ──
    def test_missing_both_modes_raises(self):
        body = {"path": "edit_test.py"}
        with self.assertRaises(ValueError):
            self.handler.build_edit_payload(body)

    def test_non_file_target_raises(self):
        body = {
            "path": str(self.root),  # directory, not file
            "newContent": "test",
        }
        with self.assertRaises(ValueError):
            self.handler.build_edit_payload(body)

    # ── New file creation ──
    def test_new_file_with_new_content(self):
        body = {
            "path": "brand_new.py",
            "newContent": "print('new file')\n",
        }
        root, target, rel, old_text, new_text, diff = self.handler.build_edit_payload(body)
        self.assertEqual(old_text, "")
        self.assertEqual(new_text, "print('new file')\n")
        # diff shows the creation
        self.assertIn("print('new file')", diff)

    # ── Unicode ──
    def test_unicode_content(self):
        self.test_file.write_text("# 中文注释\nprint('你好')\n", encoding="utf-8")
        body = {
            "path": "edit_test.py",
            "oldText": "# 中文注释",
            "newText": "# Chinese comment",
        }
        root, target, rel, old_text, new_text, diff = self.handler.build_edit_payload(body)
        self.assertIn("Chinese comment", new_text)
        self.assertNotIn("中文注释", new_text)


# ═══════════════════════════════════════════════════════════════════
# 3. Full propose_edit + apply_edit flow via HTTP-like handler calls
# ═══════════════════════════════════════════════════════════════════

class TestEditRoundtrip(unittest.TestCase):

    def setUp(self):
        self.handler = object.__new__(server.AgentLiteHandler)
        self.handler.send_json = mock.Mock()
        self.handler.read_body_json = mock.Mock()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.test_file = self.root / "roundtrip.py"
        self.test_file.write_text(
            "VERSION = '1.0.0'\n\ndef main():\n    print('v1')\n",
            encoding="utf-8",
        )
        # Setup data dirs for backups
        self.data_tmp = tempfile.TemporaryDirectory()
        self.backup_dir = Path(self.data_tmp.name) / "file-backups"
        self.backup_dir.mkdir(parents=True)
        patcher_config = mock.patch.object(server, "load_config", return_value={
            "projectRoot": str(self.root),
            "newApiBaseUrl": "http://localhost:3000",
            "userHome": str(Path.home()),
        })
        patcher_backup = mock.patch.object(server, "FILE_BACKUP_DIR", self.backup_dir)
        self.mock_config = patcher_config.start()
        self.mock_backup = patcher_backup.start()
        self.addCleanup(patcher_config.stop)
        self.addCleanup(patcher_backup.stop)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.data_tmp.cleanup)

    def test_propose_edit_returns_diff(self):
        self.handler.read_body_json.return_value = {
            "path": "roundtrip.py",
            "oldText": "print('v1')",
            "newText": "print('v2')",
        }
        server.AgentLiteHandler.tool_propose_edit(self.handler)
        call_args = self.handler.send_json.call_args[0][0]
        self.assertTrue(call_args.get("ok"))
        self.assertIn("print('v1')", call_args.get("diff", ""))
        self.assertIn("print('v2')", call_args.get("diff", ""))
        self.assertIn("newContent", call_args)

    def test_apply_edit_writes_file(self):
        self.handler.read_body_json.return_value = {
            "path": "roundtrip.py",
            "oldText": "print('v1')",
            "newText": "print('v2')",
        }
        server.AgentLiteHandler.tool_apply_edit(self.handler)
        call_args = self.handler.send_json.call_args[0][0]
        self.assertTrue(call_args.get("ok"))
        # Verify file was actually modified
        content = self.test_file.read_text(encoding="utf-8")
        self.assertIn("print('v2')", content)
        self.assertNotIn("print('v1')", content)

    def test_apply_edit_creates_backup(self):
        self.handler.read_body_json.return_value = {
            "path": "roundtrip.py",
            "oldText": "print('v1')",
            "newText": "print('v3')",
        }
        server.AgentLiteHandler.tool_apply_edit(self.handler)
        call_args = self.handler.send_json.call_args[0][0]
        self.assertTrue(call_args.get("ok"))
        self.assertIsNotNone(call_args.get("backupPath"))
        # Backup file should exist
        backup_path = Path(call_args["backupPath"])
        self.assertTrue(backup_path.exists())
        backup_content = backup_path.read_text(encoding="utf-8")
        self.assertIn("print('v1')", backup_content)

    def test_apply_edit_mtime_conflict_returns_409(self):
        current_mtime = int(self.test_file.stat().st_mtime * 1000)
        self.handler.read_body_json.return_value = {
            "path": "roundtrip.py",
            "oldText": "print('v1')",
            "newText": "print('v4')",
            "expectedMtime": current_mtime + 999999,  # wrong mtime
        }
        server.AgentLiteHandler.tool_apply_edit(self.handler)
        # Check that send_json was called with 409
        for call in self.handler.send_json.call_args_list:
            kwargs = call[1] if len(call) > 1 else {}
            if kwargs.get('status') == 409:
                return  # Test passes
        # If no 409 found, check the last call
        last_data = self.handler.send_json.call_args[0][0]
        self.assertFalse(last_data.get("ok", True), f"Expected conflict but got: {last_data}")

    def test_apply_edit_mtime_match_succeeds(self):
        current_mtime = int(self.test_file.stat().st_mtime * 1000)
        self.handler.read_body_json.return_value = {
            "path": "roundtrip.py",
            "oldText": "print('v1')",
            "newText": "print('v5')",
            "expectedMtime": current_mtime,  # matching mtime
        }
        # Need to reset send_json mock from previous test
        self.handler.send_json = mock.Mock()
        server.AgentLiteHandler.tool_apply_edit(self.handler)
        call_args = self.handler.send_json.call_args[0][0]
        self.assertTrue(call_args.get("ok"), f"Expected success but got: {call_args}")


# ═══════════════════════════════════════════════════════════════════
# 4. Fuzzy find — real-world edit scenarios
# ═══════════════════════════════════════════════════════════════════

class TestFuzzyFindRealWorld(unittest.TestCase):

    def setUp(self):
        self.handler = object.__new__(server.AgentLiteHandler)

    def test_python_function_replace(self):
        text = (
            "def calculate_total(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item.price\n"
            "    return total\n"
            "\n"
            "def format_output(total):\n"
            "    return f'${total:.2f}'\n"
        )
        fragment = (
            "def calculate_total(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item.price\n"
            "    return total"
        )
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("calculate_total", result)

    def test_html_element_replace(self):
        text = (
            "<div class='container'>\n"
            "  <h1>Title</h1>\n"
            "  <p>Content here</p>\n"
            "</div>\n"
        )
        fragment = "<h1>Title</h1>\n  <p>Content here</p>"
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn("<h1>Title</h1>", result)

    def test_json_block_replace(self):
        text = (
            "{\n"
            '  "name": "app",\n'
            '  "version": "1.0",\n'
            '  "dependencies": {\n'
            '    "react": "^18.0"\n'
            "  }\n"
            "}\n"
        )
        fragment = '"version": "1.0"'
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)
        self.assertIn('"version": "1.0"', result)

    def test_whitespace_drift_tolerance(self):
        text = "def foo():\n    return 1\n"
        # Model might return fragment with slightly different whitespace
        fragment = "def foo():\n  return 1"  # 2 spaces instead of 4
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)

    def test_mixed_indentation(self):
        text = (
            "class User:\n"
            "    def __init__(self):\n"
            "        self.name = ''\n"
            "        self.age = 0\n"
        )
        fragment = (
            "class User:\n"
            "    def __init__(self):\n"
            "        self.name = ''\n"
        )
        result = self.handler._fuzzy_find(text, fragment)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()

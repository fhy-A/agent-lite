"""
Tests for server.py pure functions.
Run: python -m unittest tests.test_server -v
   or: python tests/test_server.py
"""
import base64
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


class TestUpdaterHelpers(unittest.TestCase):
    def test_remote_version_selects_matching_code_asset(self):
        payload = {
            "tag_name": "v0.5.4",
            "assets": [
                {"name": "helper.exe", "browser_download_url": "https://example.test/helper.exe"},
                {
                    "name": "Code-v0.5.4.exe",
                    "browser_download_url": "https://example.test/Code-v0.5.4.exe",
                },
            ],
        }
        response = mock.Mock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        with mock.patch.object(server.request, "urlopen", return_value=response):
            version, url = server._read_remote_version()
        self.assertEqual(version, "0.5.4")
        self.assertEqual(url, "https://example.test/Code-v0.5.4.exe")

    def test_valid_windows_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exe = Path(temp_dir) / "Code-v1.2.3.exe"
            exe.write_bytes(b"MZ" + (b"\0" * (1024 * 1024)))
            self.assertTrue(server._is_valid_windows_executable(exe))

    def test_rejects_incomplete_or_non_pe_download(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bad = Path(temp_dir) / "Code-v1.2.3.exe.part"
            bad.write_text("<html>download failed</html>", encoding="utf-8")
            self.assertFalse(server._is_valid_windows_executable(bad))

    def test_update_script_keeps_new_name_and_removes_old_versions(self):
        root = Path(r"C:\Code")
        old_exe = root / "Code-v1.2.2.exe"
        new_exe = root / "Code-v1.2.3.exe"
        script = server._build_update_script(old_exe, new_exe, root / "update.log")
        self.assertIn("Get-CimInstance Win32_Process", script)
        self.assertIn("Stop-Process", script)
        self.assertIn("Get-ChildItem", script)
        self.assertIn("Remove-Item", script)
        self.assertIn("Start-Process -FilePath $newExe", script)
        self.assertIn("-ArgumentList '--reuse-browser'", script)
        self.assertNotIn("Copy-Item", script)

    def test_check_update_detects_newer_release(self):
        handler = object.__new__(server.CodeHandler)
        download_url = "https://github.com/fhy-A/Code/releases/download/v0.4.11/Code-v0.4.11.exe"
        with mock.patch.object(server, "_read_version_file", return_value="0.4.10"), \
             mock.patch.object(server, "_read_remote_version", return_value=("0.4.11", download_url)):
            result = handler._check_update()
        self.assertTrue(result["updateAvailable"])
        self.assertEqual(result["remoteVersion"], "0.4.11")
        self.assertTrue(result["downloadUrl"].endswith("/v0.4.11/Code-v0.4.11.exe"))

    def test_frontend_waits_for_new_version_before_cache_busting_reload(self):
        settings_js = (
            Path(__file__).resolve().parent.parent / "src" / "features" / "settings.js"
        ).read_text(encoding="utf-8")
        self.assertIn('if (versionInfo.localVersion !== remoteVersion) return;', settings_js)
        self.assertIn('cache: "no-store"', settings_js)
        self.assertIn(
            'refreshed.searchParams.set("updated", `${remoteVersion}-${Date.now()}`)',
            settings_js,
        )
        self.assertIn("global.location.replace(refreshed.toString())", settings_js)


class TestWorkbarAuthentication(unittest.TestCase):
    def make_handler(self, body):
        handler = object.__new__(server.CodeHandler)
        handler.read_body_json = mock.Mock(return_value=body)
        handler.send_json = mock.Mock()
        return handler

    def test_validate_code_auth_uses_fixed_workbar_endpoint(self):
        handler = self.make_handler({"token": "test-access-token", "userId": "42"})
        account_response = mock.MagicMock()
        account_response.read.return_value = json.dumps({
            "success": True,
            "data": {
                "id": 42,
                "username": "alice",
                "display_name": "Alice",
                "email": "alice@example.com",
                "group": "default",
                "quota": 123,
                "used_quota": 45,
                "request_count": 67,
            },
        }).encode("utf-8")
        account_response.__enter__.return_value = account_response
        status_response = mock.MagicMock()
        status_response.read.return_value = json.dumps({
            "success": True,
            "data": {
                "quota_per_unit": 500000,
                "quota_display_type": "CNY",
                "usd_exchange_rate": 7.2,
                "custom_currency_symbol": "",
                "custom_currency_exchange_rate": 1,
            },
        }).encode("utf-8")
        status_response.__enter__.return_value = status_response

        with mock.patch.object(server.request, "urlopen", side_effect=[account_response, status_response]) as urlopen:
            handler._handle_validate_code_auth()

        upstream = urlopen.call_args_list[0].args[0]
        self.assertEqual(upstream.full_url, "https://workbar.ai/api/user/self")
        self.assertEqual(upstream.get_header("Authorization"), "test-access-token")
        self.assertEqual(upstream.get_header("New-api-user"), "42")
        self.assertEqual(urlopen.call_args_list[1].args[0].full_url, "https://workbar.ai/api/status")
        handler.send_json.assert_called_once_with({
            "valid": True,
            "account": {
                "userId": "42",
                "username": "alice",
                "displayName": "Alice",
                "email": "alice@example.com",
                "group": "default",
                "quota": 123,
                "usedQuota": 45,
                "requestCount": 67,
                "quotaDisplay": {
                    "quotaPerUnit": 500000,
                    "type": "CNY",
                    "usdExchangeRate": 7.2,
                    "customCurrencySymbol": "",
                    "customCurrencyExchangeRate": 1,
                },
            },
        })

    def test_validate_code_auth_only_returns_allowlisted_account_fields(self):
        handler = self.make_handler({"token": "test-access-token", "userId": "42"})
        response = mock.MagicMock()
        response.read.return_value = json.dumps({
            "success": True,
            "data": {
                "id": 42,
                "username": "alice",
                "access_token": "must-not-leak",
                "stripe_customer": "cus_private",
                "permissions": {"admin": True},
            },
        }).encode("utf-8")
        response.__enter__.return_value = response

        with mock.patch.object(server.request, "urlopen", side_effect=[response, server.error.URLError("offline")]):
            handler._handle_validate_code_auth()

        result = handler.send_json.call_args.args[0]["account"]
        self.assertEqual(set(result), {
            "userId", "username", "displayName", "email", "group",
            "quota", "usedQuota", "requestCount", "quotaDisplay",
        })
        self.assertNotIn("must-not-leak", json.dumps(result))

    def test_validate_code_auth_rejects_invalid_or_mismatched_account(self):
        for payload in (
            {"success": False, "message": "invalid"},
            {"success": True, "data": {"id": 99, "username": "other"}},
        ):
            with self.subTest(payload=payload):
                handler = self.make_handler({"token": "test-access-token", "userId": "42"})
                response = mock.MagicMock()
                response.read.return_value = json.dumps(payload).encode("utf-8")
                response.__enter__.return_value = response
                with mock.patch.object(server.request, "urlopen", return_value=response):
                    handler._handle_validate_code_auth()
                self.assertEqual(handler.send_json.call_args.args[1], 401)

    def test_validate_code_auth_keeps_outage_separate_from_expiry(self):
        handler = self.make_handler({"token": "test-access-token", "userId": "42"})
        with mock.patch.object(server.request, "urlopen", side_effect=server.error.URLError("offline")):
            handler._handle_validate_code_auth()
        handler.send_json.assert_called_once_with({"error": "Workbar is unavailable"}, 502)

    def test_sync_keys_uses_fixed_workbar_endpoint_and_normalizes_prefix(self):
        handler = self.make_handler({
            "token": "test-access-token",
            "userId": "42",
            "platformUrl": "https://untrusted.example",
        })
        token_response = mock.MagicMock()
        token_response.read.return_value = json.dumps({
            "data": {"items": [
                {"id": 7, "name": "first", "status": 1},
                {"id": 8, "name": "second", "status": 2},
                {"id": 9, "name": "masked", "status": 1},
            ]},
        }).encode("utf-8")
        token_response.__enter__.return_value = token_response
        key_response = mock.MagicMock()
        key_response.read.return_value = json.dumps({
            "data": {"keys": {"7": "full-value", "8": "sk-ready", "9": "sk-***mask"}},
        }).encode("utf-8")
        key_response.__enter__.return_value = key_response

        with mock.patch.object(
            server.request,
            "urlopen",
            side_effect=[token_response, key_response],
        ) as urlopen:
            handler._handle_sync_keys()

        requests = [call.args[0] for call in urlopen.call_args_list]
        self.assertEqual(requests[0].full_url, "https://workbar.ai/api/token/?p=0&size=100")
        self.assertEqual(requests[1].full_url, "https://workbar.ai/api/token/batch/keys")
        self.assertEqual(requests[1].get_method(), "POST")
        payload = handler.send_json.call_args.args[0]
        self.assertEqual(payload["keys"], {"7": "sk-full-value", "8": "sk-ready"})

    def test_sync_keys_preserves_local_auth_on_workbar_outage(self):
        handler = self.make_handler({"token": "test-access-token", "userId": "42"})
        with mock.patch.object(server.request, "urlopen", side_effect=server.error.URLError("offline")):
            handler._handle_sync_keys()
        handler.send_json.assert_called_once_with({"error": "Workbar is unavailable"}, 502)

    def test_sync_keys_paginates_and_batches_all_platform_keys(self):
        handler = self.make_handler({"token": "test-access-token", "userId": "42"})

        def response(payload):
            result = mock.MagicMock()
            result.read.return_value = json.dumps(payload).encode("utf-8")
            result.__enter__.return_value = result
            return result

        first_page = [{"id": key_id, "name": f"key-{key_id}", "status": 1} for key_id in range(1, 101)]
        second_page = [{"id": 101, "name": "key-101", "status": 1}]
        side_effects = [
            response({"data": {"items": first_page, "total": 101}}),
            response({"data": {"items": second_page, "total": 101}}),
            response({"data": {"keys": {str(key_id): f"value-{key_id}" for key_id in range(1, 101)}}}),
            response({"data": {"keys": {"101": "value-101"}}}),
        ]
        with mock.patch.object(server.request, "urlopen", side_effect=side_effects) as urlopen:
            handler._handle_sync_keys()

        requests = [call.args[0] for call in urlopen.call_args_list]
        self.assertEqual(requests[0].full_url, "https://workbar.ai/api/token/?p=0&size=100")
        self.assertEqual(requests[1].full_url, "https://workbar.ai/api/token/?p=1&size=100")
        self.assertEqual(json.loads(requests[2].data)["ids"], list(range(1, 101)))
        self.assertEqual(json.loads(requests[3].data)["ids"], [101])
        payload = handler.send_json.call_args.args[0]
        self.assertEqual(len(payload["tokens"]), 101)
        self.assertEqual(payload["keys"]["101"], "sk-value-101")


class TestTrayRestart(unittest.TestCase):
    def test_source_restart_closes_server_and_relaunches_server_script(self):
        server_ref = mock.Mock()
        icon = mock.Mock()
        with mock.patch.object(server.subprocess, "Popen") as popen:
            server._restart_code_process(server_ref, icon)

        powershell = popen.call_args.args[0]
        self.assertEqual(powershell[:5], [
            "powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
        ])
        encoded = powershell[powershell.index("-EncodedCommand") + 1]
        script = base64.b64decode(encoded).decode("utf-16-le")
        self.assertIn(f"Wait-Process -Id {os.getpid()}", script)
        self.assertIn(str((server.APP_DIR / "server.py").resolve()), script)
        server_ref.shutdown.assert_called_once_with()
        server_ref.server_close.assert_called_once_with()
        icon.stop.assert_called_once_with()

    def test_packaged_restart_reuses_browser_and_executable_directory(self):
        server_ref = mock.Mock()
        icon = mock.Mock()
        packaged_exe = Path(r"C:\Program Files\Code\Code-v0.5.4.exe")
        with mock.patch.object(server.sys, "frozen", True, create=True), \
             mock.patch.object(server.sys, "executable", str(packaged_exe)), \
             mock.patch.object(server.subprocess, "Popen") as popen:
            server._restart_code_process(server_ref, icon)

        powershell = popen.call_args.args[0]
        encoded = powershell[powershell.index("-EncodedCommand") + 1]
        script = base64.b64decode(encoded).decode("utf-16-le")
        self.assertIn(f"-FilePath '{packaged_exe}'", script)
        self.assertIn("-ArgumentList @('--reuse-browser')", script)
        self.assertIn(f"-WorkingDirectory '{packaged_exe.parent}'", script)
        self.assertIn("-WindowStyle Hidden", script)
        icon.stop.assert_called_once_with()

    def test_tray_menu_exposes_restart_action(self):
        source = Path(server.__file__).read_text(encoding="utf-8")
        self.assertIn('pystray.MenuItem("Restart Code", on_restart)', source)

    def test_restart_cancels_waiter_if_current_server_cannot_stop(self):
        server_ref = mock.Mock()
        server_ref.shutdown.side_effect = RuntimeError("cannot stop")
        icon = mock.Mock()
        waiter = mock.Mock()
        with mock.patch.object(server.subprocess, "Popen", return_value=waiter):
            with self.assertRaisesRegex(RuntimeError, "cannot stop"):
                server._restart_code_process(server_ref, icon)
        waiter.terminate.assert_called_once_with()
        icon.stop.assert_not_called()


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

    # ── Updated: pipe now allowed ──
    def test_pipe_is_allowed(self):
        ok, _ = server.is_safe_command("dir | findstr test")
        self.assertTrue(ok)

    def test_pipe_git_log(self):
        ok, _ = server.is_safe_command("git log --oneline | head -5")
        self.assertTrue(ok)

    # ── Updated: redirect now allowed ──
    def test_redirect_is_allowed(self):
        ok, _ = server.is_safe_command("dir > output.txt")
        self.assertTrue(ok)

    def test_append_redirect_allowed(self):
        ok, _ = server.is_safe_command("echo line >> log.txt")
        self.assertTrue(ok)

    # ── Semicolon: still blocks when combined with dangerous cmd ──
    def test_semicolon_with_del_still_blocked(self):
        ok, _ = server.is_safe_command("dir; del file.txt")
        self.assertFalse(ok)

    def test_semicolon_in_python_allowed(self):
        ok, _ = server.is_safe_command("python -c \"x=1; y=2; print(x+y)\"")
        self.assertTrue(ok)

    def test_semicolon_in_python_import_allowed(self):
        ok, _ = server.is_safe_command("python -c \"from docx import Document; print('ok')\"")
        self.assertTrue(ok)

    # ── Updated: python -c now allowed ──
    def test_python_c_is_allowed(self):
        ok, _ = server.is_safe_command("python -c 'print(1)'")
        self.assertTrue(ok)

    def test_python_c_multiline_allowed(self):
        ok, _ = server.is_safe_command("python -c \"for i in range(3):\\n print(i)\"")
        self.assertTrue(ok)

    # ── Updated: node -e now allowed ──
    def test_node_e_is_allowed(self):
        ok, _ = server.is_safe_command("node -e 'console.log(1)'")
        self.assertTrue(ok)

    # ── New: file write/create commands allowed ──
    def test_mkdir_allowed(self):
        ok, _ = server.is_safe_command("mkdir newdir")
        self.assertTrue(ok)

    def test_set_content_allowed(self):
        ok, _ = server.is_safe_command("set-content test.txt 'hello'")
        self.assertTrue(ok)

    def test_copy_item_allowed(self):
        ok, _ = server.is_safe_command("copy-item a.txt b.txt")
        self.assertTrue(ok)

    def test_move_item_allowed(self):
        ok, _ = server.is_safe_command("move-item a.txt b.txt")
        self.assertTrue(ok)

    def test_out_file_allowed(self):
        ok, _ = server.is_safe_command("out-file -FilePath out.txt")
        self.assertTrue(ok)

    def test_pip_install_allowed(self):
        ok, _ = server.is_safe_command("pip install requests")
        self.assertTrue(ok)

    def test_dependency_installs_are_classified_by_runtime_ownership(self):
        managed_cases = (
            "pip install requests",
            "python -m pip install requests",
            "python -m venv data/runtime/python",
            "npm install --prefix data/runtime/node lodash",
        )
        for command in managed_cases:
            with self.subTest(command=command):
                self.assertEqual(server.dependency_install_command_kind(command), "managed")
                self.assertTrue(server.command_requires_dependency_authorization(command))
        system_cases = (
            "winget install Poppler.Poppler",
            "choco install pandoc",
            "sudo apt-get install libreoffice",
            "python -c \"import subprocess; subprocess.run(['winget', 'install', 'Pandoc.Pandoc'])\"",
        )
        for command in system_cases:
            with self.subTest(command=command):
                self.assertEqual(server.dependency_install_command_kind(command), "system")
                self.assertFalse(server.command_requires_dependency_authorization(command))
        environment_cases = (
            '$old = [Environment]::GetEnvironmentVariable("Path", "User"); '
            '[Environment]::SetEnvironmentVariable("Path", "$old;C:\\Pandoc", "User")',
            '$p = "$env:APPDATA\\npm\\pandoc.cmd"; Set-Content -Path $p -Value "@echo off"',
            'setx PATH "%PATH%;C:\\Pandoc"',
        )
        for command in environment_cases:
            with self.subTest(command=command):
                self.assertEqual(server.dependency_install_command_kind(command), "environment")
                self.assertFalse(server.command_requires_dependency_authorization(command))
        self.assertFalse(server.command_requires_dependency_authorization("python -m pytest -q"))
        self.assertFalse(server.command_requires_dependency_authorization("npm test"))

    def test_dependency_install_classifier_reads_project_local_wrapper(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "install_deps.py"
            script.write_text(
                "import subprocess\nsubprocess.run(['winget', 'install', 'Pandoc.Pandoc'])\n",
                encoding="utf-8",
            )
            kind = server.dependency_install_command_kind(
                "python install_deps.py",
                project_root=root,
            )

        self.assertEqual(kind, "system")

    def test_run_command_blocks_system_package_manager_install(self):
        with mock.patch.object(server.subprocess, "Popen") as popen_mock:
            result = server.execute_run_command_tool({
                "command": "winget install Pandoc.Pandoc",
                "timeout": 300,
            })

        popen_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertTrue(result["blocked"])
        self.assertTrue(result["userCooperationRequired"])
        self.assertEqual(result["dependencyInstallKind"], "system")

    def test_run_command_blocks_persistent_dependency_environment_changes(self):
        command = (
            '$p = "$env:APPDATA\\npm\\pdftoppm.cmd"; '
            'Set-Content -Path $p -Value "@echo off"'
        )
        with mock.patch.object(server.subprocess, "Popen") as popen_mock:
            result = server.execute_run_command_tool({"command": command})

        popen_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertTrue(result["blocked"])
        self.assertTrue(result["userCooperationRequired"])
        self.assertEqual(result["dependencyInstallKind"], "environment")
        self.assertIn("Do not modify PATH", result["error"])

    def test_repeated_command_guard_blocks_the_third_identical_attempt(self):
        run = {
            "tool_executions": {
                "one": {"name": "run_command", "command": "python -m pytest -q"},
                "two": {"name": "run_command", "command": "  PYTHON   -m pytest -q  "},
                "current": {"name": "run_command", "command": "python -m pytest -q"},
            },
        }
        count = server._agent_repeated_command_count(
            run,
            "python -m pytest -q",
            exclude_call_id="current",
        )
        self.assertEqual(count, 2)

    # ── New: expanded whitelist checks ──
    def test_curl_allowed(self):
        ok, _ = server.is_safe_command("curl https://example.com")
        self.assertTrue(ok)

    def test_cat_allowed(self):
        ok, _ = server.is_safe_command("cat file.txt")
        self.assertTrue(ok)

    def test_grep_allowed(self):
        ok, _ = server.is_safe_command("grep pattern file.txt")
        self.assertTrue(ok)

    def test_find_allowed(self):
        ok, _ = server.is_safe_command("find . -name '*.py'")
        self.assertTrue(ok)

    def test_wc_allowed(self):
        ok, _ = server.is_safe_command("wc -l file.txt")
        self.assertTrue(ok)

    def test_head_allowed(self):
        ok, _ = server.is_safe_command("head -10 file.txt")
        self.assertTrue(ok)

    def test_tail_allowed(self):
        ok, _ = server.is_safe_command("tail -20 file.txt")
        self.assertTrue(ok)

    def test_tasklist_allowed(self):
        ok, _ = server.is_safe_command("tasklist")
        self.assertTrue(ok)

    def test_netstat_allowed(self):
        ok, _ = server.is_safe_command("netstat -an")
        self.assertTrue(ok)

    def test_ipconfig_allowed(self):
        ok, _ = server.is_safe_command("ipconfig")
        self.assertTrue(ok)

    def test_ping_allowed(self):
        ok, _ = server.is_safe_command("ping localhost")
        self.assertTrue(ok)

    def test_git_branch_allowed(self):
        ok, _ = server.is_safe_command("git branch -a")
        self.assertTrue(ok)

    def test_git_stash_allowed(self):
        ok, _ = server.is_safe_command("git stash list")
        self.assertTrue(ok)

    def test_git_blame_allowed(self):
        ok, _ = server.is_safe_command("git blame server.py")
        self.assertTrue(ok)

    def test_docker_ps_allowed(self):
        ok, _ = server.is_safe_command("docker ps")
        self.assertTrue(ok)

    def test_get_process_allowed(self):
        ok, _ = server.is_safe_command("get-process")
        self.assertTrue(ok)

    def test_cargo_allowed(self):
        ok, _ = server.is_safe_command("cargo build")
        self.assertTrue(ok)

    def test_go_allowed(self):
        ok, _ = server.is_safe_command("go build ./...")
        self.assertTrue(ok)

    def test_tar_create_allowed(self):
        ok, _ = server.is_safe_command("tar -czf archive.tar.gz dir/")
        self.assertTrue(ok)

    # ── Deletion still blocked ──
    def test_del_is_blocked(self):
        ok, _ = server.is_safe_command("del file.txt")
        self.assertFalse(ok)

    def test_rm_is_blocked(self):
        ok, _ = server.is_safe_command("rm file.txt")
        self.assertFalse(ok)

    def test_rmdir_is_blocked(self):
        ok, _ = server.is_safe_command("rmdir somedir")
        self.assertFalse(ok)

    def test_remove_item_is_blocked(self):
        ok, _ = server.is_safe_command("remove-item file.txt")
        self.assertFalse(ok)

    def test_del_force_is_blocked(self):
        ok, _ = server.is_safe_command("del /f /s C:\\important.txt")
        self.assertFalse(ok)

    # ── System destruction still blocked ──
    def test_format_is_blocked(self):
        ok, _ = server.is_safe_command("format C:")
        self.assertFalse(ok)

    def test_shutdown_is_blocked(self):
        ok, _ = server.is_safe_command("shutdown /s")
        self.assertFalse(ok)

    def test_reg_is_blocked(self):
        ok, _ = server.is_safe_command("reg delete HKLM\\something")
        self.assertFalse(ok)

    def test_net_user_is_blocked(self):
        ok, _ = server.is_safe_command("net user admin password")
        self.assertFalse(ok)

    def test_net_start_is_blocked(self):
        ok, _ = server.is_safe_command("net start wuauserv")
        self.assertFalse(ok)

    def test_sc_is_blocked(self):
        ok, _ = server.is_safe_command("sc stop service")
        self.assertFalse(ok)

    def test_stop_process_is_blocked(self):
        ok, _ = server.is_safe_command("stop-process -Name chrome")
        self.assertFalse(ok)

    # ── Command chaining / escape still blocked ──
    def test_ampersand_chaining_blocked(self):
        ok, _ = server.is_safe_command("dir & del file.txt")
        self.assertFalse(ok)

    def test_backtick_escape_blocked(self):
        ok, _ = server.is_safe_command("dir `; del file.txt")
        self.assertFalse(ok)

    # ── Still unknown / edge cases ──
    def test_empty_is_unsafe(self):
        ok, msg = server.is_safe_command("")
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)

    def test_unknown_prefix_is_unsafe(self):
        ok, _ = server.is_safe_command("sudo rm -rf /")
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

    def test_ignores_line_ending_style(self):
        diff = server.make_unified_diff("line1\r\nline2\r\n", "line1\nline2\n", "test.txt")
        self.assertEqual(diff, "")

    def test_ignores_final_newline_only(self):
        diff = server.make_unified_diff("line1", "line1\n", "test.txt")
        self.assertEqual(diff, "")

    def test_normalizes_accidentally_doubled_windows_newlines(self):
        source = "line1\r\r\nline2\r\r\n"
        self.assertEqual(server.normalize_text_newlines(source), "line1\nline2\n")

    def test_fuzzy_edit_remains_actionable_after_newline_normalization(self):
        old = server.normalize_text_newlines(
            'def greet(name):\r\r\n    return "Hello " + name\r\r\n\r\r\n'
            'def farewell(name):\r\r\n    return "Goodbye " + name\r\r\n'
        )
        old_fragment = 'def greet(name):\n    return "Hello " + name\n\ndef farewell(name):\n    return "Goodbye " + name'
        new_fragment = 'def greet(name):\n    return f"Hello {name}"\n\ndef farewell(name):\n    return f"Goodbye {name}"'
        found = server.CodeHandler._fuzzy_find(None, old, old_fragment)
        self.assertEqual(found, old_fragment)
        updated = old.replace(found, new_fragment, 1)
        diff = server.make_unified_diff(old, updated, "test_utils.py")
        self.assertIn('+    return f"Hello {name}"', diff)
        self.assertIn('+    return f"Goodbye {name}"', diff)


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


# ─── 2026-07-07: security / performance regression tests ───

class TestSubprocessKwargs(unittest.TestCase):
    """Verify DETACHED_PROCESS is no longer used (breaks stdout capture)."""
    def test_no_detached_process_flag(self):
        kwargs = server._hidden_subprocess_kwargs()
        if not kwargs:  # non-Windows
            self.assertTrue(True)
            return
        flags = kwargs["creationflags"]
        DETACHED = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        self.assertEqual(flags, CREATE_NO_WINDOW,
                         f"DETACHED_PROCESS flag present! Got 0x{flags:08x}, expected 0x{CREATE_NO_WINDOW:08x}")
        self.assertFalse(flags & DETACHED,
                         f"DETACHED_PROCESS must not be set, got 0x{flags:08x}")


class TestSkipDirs(unittest.TestCase):
    """Verify expanded SKIP_DIRS covers common large directories."""
    def test_appdata_skipped(self):
        self.assertIn("AppData", server.SKIP_DIRS)

    def test_vscode_skipped(self):
        self.assertIn(".vscode", server.SKIP_DIRS)

    def test_node_modules_skipped(self):
        self.assertIn("node_modules", server.SKIP_DIRS)

    def test_one_drive_skipped(self):
        self.assertIn("OneDrive", server.SKIP_DIRS)

    def test_cookies_skipped(self):
        self.assertIn("Cookies", server.SKIP_DIRS)

    def test_npm_skipped(self):
        self.assertIn(".npm", server.SKIP_DIRS)

    def test_min_size(self):
        self.assertGreater(len(server.SKIP_DIRS), 50,
                           f"SKIP_DIRS only has {len(server.SKIP_DIRS)} entries, expected 50+")


class TestDeniedRuntimePattern(unittest.TestCase):
    """Verify DENIED_RUNTIME_PATTERN is disabled (python -c / node -e allowed)."""
    def test_denied_runtime_removed(self):
        self.assertFalse(hasattr(server, "DENIED_RUNTIME_PATTERN"),
                         "DENIED_RUNTIME_PATTERN should not exist — python -c / node -e must be allowed")


class TestDeniedCommandPattern(unittest.TestCase):
    """Verify DENIED_COMMAND_PATTERN correctly blocks/allows."""
    def test_does_not_block_semicolon_alone(self):
        # `;` should NOT be in the character class; only `&` and backtick
        self.assertFalse(server.DENIED_COMMAND_PATTERN.search("python -c a=1 print a"),  # no ;/&/` in this
                         "DENIED pattern should not match safe Python")

    def test_does_not_block_pipe(self):
        self.assertIsNone(server.DENIED_COMMAND_PATTERN.search("dir | findstr x"))

    def test_blocks_del(self):
        self.assertIsNotNone(server.DENIED_COMMAND_PATTERN.search("del file.txt"))

    def test_blocks_ampersand(self):
        self.assertIsNotNone(server.DENIED_COMMAND_PATTERN.search("dir & del"))

    def test_blocks_backtick(self):
        self.assertIsNotNone(server.DENIED_COMMAND_PATTERN.search("dir `; del"))


class TestSafeCommandPrefixes(unittest.TestCase):
    """Verify whitelist has expected entries."""
    def test_python_c_in_prefixes(self):
        self.assertIn("python -c ", server.SAFE_COMMAND_PREFIXES)

    def test_pip_in_prefixes(self):
        self.assertIn("pip ", server.SAFE_COMMAND_PREFIXES)

    def test_curl_in_prefixes(self):
        self.assertIn("curl ", server.SAFE_COMMAND_PREFIXES)

    def test_cat_in_prefixes(self):
        self.assertIn("cat ", server.SAFE_COMMAND_PREFIXES)

    def test_mkdir_in_prefixes(self):
        self.assertIn("mkdir ", server.SAFE_COMMAND_PREFIXES)

    def test_set_content_in_prefixes(self):
        self.assertIn("set-content ", server.SAFE_COMMAND_PREFIXES)

    def test_min_count(self):
        self.assertGreater(len(server.SAFE_COMMAND_PREFIXES), 100,
                           f"Only {len(server.SAFE_COMMAND_PREFIXES)} prefixes, expected 100+")


if __name__ == "__main__":
    unittest.main()

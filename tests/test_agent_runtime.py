"""Durable server-owned Agent run regression tests.

Run: python -m pytest tests/test_agent_runtime.py -v
"""

import hashlib
import json
import tempfile
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import requests

import server as server_mod


class _AgentUpstream(BaseHTTPRequestHandler):
    calls = 0
    payloads = []
    authorizations = []
    slow_started = threading.Event()
    release_slow = threading.Event()

    def log_message(self, *_args):
        return

    def do_POST(self):
        type(self).calls += 1
        type(self).authorizations.append(self.headers.get("Authorization", ""))
        length = int(self.headers.get("Content-Length", "0") or "0")
        payload = json.loads(self.rfile.read(length) or b"{}")
        type(self).payloads.append(payload)
        messages = payload.get("messages") or []
        if any(
            message.get("role") == "user" and message.get("content") == "slow request"
            for message in messages
        ):
            type(self).slow_started.set()
            type(self).release_slow.wait(timeout=3)
        tool_result_count = sum(message.get("role") == "tool" for message in messages)
        repeat_id = any(
            message.get("role") == "user" and message.get("content") == "repeat tool id"
            for message in messages
        )
        asks_user = any(
            message.get("role") == "user" and message.get("content") == "ask for target"
            for message in messages
        )
        proposes_edit = any(
            message.get("role") == "user" and message.get("content") == "propose edit"
            for message in messages
        )
        uses_network_and_skills = any(
            message.get("role") == "user"
            and message.get("content") == "inspect skill and network"
            for message in messages
        )
        runs_command = any(
            message.get("role") == "user"
            and message.get("content") in {"run approved command", "run slow command"}
            for message in messages
        )
        runs_slow_command = any(
            message.get("role") == "user" and message.get("content") == "run slow command"
            for message in messages
        )
        saves_memory = any(
            message.get("role") == "user" and message.get("content") == "remember convention"
            for message in messages
        )
        should_call_tool = tool_result_count == 0 or (repeat_id and tool_result_count < 2)
        if saves_memory and tool_result_count == 0:
            frames = [{
                "choices": [{
                    "delta": {"tool_calls": [{
                        "index": 0,
                        "id": "agent-memory-1",
                        "type": "function",
                        "function": {
                            "name": "save_memory",
                            "arguments": json.dumps({
                                "name": "runtime-convention",
                                "description": "Runtime convention",
                                "body": "AgentRun owns durable memory writes.",
                            }),
                        },
                    }]},
                    "finish_reason": "tool_calls",
                }],
            }]
        elif saves_memory:
            frames = [
                {
                    "choices": [{
                        "delta": {"content": "memory task complete"},
                        "finish_reason": "stop",
                    }],
                },
                {"choices": [], "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 3,
                    "total_tokens": 11,
                }},
            ]
        elif runs_command and tool_result_count == 0:
            command = (
                'python -c "import time; print(\'command-started\', flush=True); time.sleep(20)"'
                if runs_slow_command
                else 'python -c "print(\'agent-command\')"'
            )
            frames = [{
                "choices": [{
                    "delta": {"tool_calls": [{
                        "index": 0,
                        "id": "agent-command-1",
                        "type": "function",
                        "function": {
                            "name": "run_command",
                            "arguments": json.dumps({
                                "command": command,
                                "description": "Agent runtime command",
                            }),
                        },
                    }]},
                    "finish_reason": "tool_calls",
                }],
            }]
        elif runs_command:
            frames = [
                {
                    "choices": [{
                        "delta": {"content": "command task complete"},
                        "finish_reason": "stop",
                    }],
                },
                {"choices": [], "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 3,
                    "total_tokens": 13,
                }},
            ]
        elif uses_network_and_skills and tool_result_count == 0:
            calls = [
                ("agent-skill-1", "use_skill", {"name": "runtime-skill"}),
                (
                    "agent-skill-resource-1",
                    "read_skill_resource",
                    {"skill": "runtime-skill", "file": "references/guide.md"},
                ),
                ("agent-web-1", "web_fetch", {"url": "https://example.com/docs"}),
            ]
            frames = [{
                "choices": [{
                    "delta": {
                        "tool_calls": [
                            {
                                "index": index,
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": json.dumps(arguments),
                                },
                            }
                            for index, (call_id, name, arguments) in enumerate(calls)
                        ],
                    },
                    "finish_reason": "tool_calls",
                }],
            }]
        elif uses_network_and_skills:
            frames = [
                {
                    "choices": [{
                        "delta": {"content": "network and skill task complete"},
                        "finish_reason": "stop",
                    }],
                },
                {"choices": [], "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                }},
            ]
        elif proposes_edit and tool_result_count == 0:
            frames = [{
                "choices": [{
                    "delta": {"tool_calls": [{
                        "index": 0,
                        "id": "agent-edit-1",
                        "type": "function",
                        "function": {
                            "name": "propose_edit",
                            "arguments": json.dumps({
                                "path": "README.md",
                                "oldText": "Durable Agent",
                                "newText": "Authorized Agent",
                            }),
                        },
                    }]},
                    "finish_reason": "tool_calls",
                }],
            }]
        elif proposes_edit:
            frames = [
                {"choices": [{"delta": {"content": "edit task complete"}, "finish_reason": "stop"}]},
                {"choices": [], "usage": {"prompt_tokens": 9, "completion_tokens": 3, "total_tokens": 12}},
            ]
        elif asks_user and tool_result_count == 0:
            arguments = {
                "title": "Choose a target",
                "reason": "The target cannot be inferred from the project.",
                "questions": [{
                    "id": "target",
                    "prompt": "Which target should be analyzed?",
                    "type": "single",
                    "required": True,
                    "allowOther": False,
                    "options": [
                        {"value": "api", "label": "API", "description": "Analyze the API."},
                        {"value": "ui", "label": "UI", "description": "Analyze the UI."},
                    ],
                }],
            }
            frames = [{
                "choices": [{
                    "delta": {"tool_calls": [{
                        "index": 0,
                        "id": "agent-question-1",
                        "type": "function",
                        "function": {
                            "name": "request_user_input",
                            "arguments": json.dumps(arguments),
                        },
                    }]},
                    "finish_reason": "tool_calls",
                }],
            }]
        elif asks_user:
            frames = [
                {"choices": [{"delta": {"content": "questionnaire task complete"}, "finish_reason": "stop"}]},
                {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}},
            ]
        elif not should_call_tool:
            frames = [
                {"choices": [{"delta": {"content": "read-only task complete"}, "finish_reason": "stop"}]},
                {"choices": [], "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11}},
            ]
        else:
            frames = [
                {
                    "choices": [{
                        "delta": {
                            "reasoning_content": "reading project file",
                            "tool_calls": [{
                                "index": 0,
                                "id": "agent-call-1",
                                "type": "function",
                                "function": {"name": "read_", "arguments": "{\"pa"},
                            }],
                        },
                    }],
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "function": {"name": "file", "arguments": "th\":\"README.md\"}"},
                            }],
                        },
                        "finish_reason": "tool_calls",
                    }],
                },
                {"choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9}},
            ]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.end_headers()
        for frame in frames:
            self.wfile.write(("data: " + json.dumps(frame) + "\n\n").encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class TestDurableAgentRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), _AgentUpstream)
        cls.thread = threading.Thread(target=cls.upstream.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.upstream.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.upstream.shutdown()
        cls.upstream.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="code_agent_runtime_")
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.project_dir = Path(self.temp_dir.name) / "project"
        self.data_dir.mkdir()
        self.project_dir.mkdir()
        (self.project_dir / "README.md").write_text("# Durable Agent\n", encoding="utf-8")
        self.config_path = self.data_dir / "config.json"
        self.config_path.write_text(json.dumps({
            "projectRoot": str(self.project_dir),
            "newApiBaseUrl": self.base_url,
        }), encoding="utf-8")
        self.patchers = [
            mock.patch.object(server_mod, "DATA_DIR", self.data_dir),
            mock.patch.object(server_mod, "CONFIG_PATH", self.config_path),
            mock.patch.object(server_mod, "FILE_BACKUP_DIR", self.data_dir / "file-backups"),
            mock.patch.object(server_mod, "SKILLS_DIR", self.data_dir / "skills"),
            mock.patch.object(server_mod, "MEMORY_DIR", self.data_dir / "memory"),
        ]
        for patcher in self.patchers:
            patcher.start()
        with server_mod._agent_run_lock:
            server_mod._agent_runs.clear()
        with server_mod._model_runtime_lock:
            server_mod._model_runtime_runs.clear()
        _AgentUpstream.calls = 0
        _AgentUpstream.payloads = []
        _AgentUpstream.authorizations = []
        _AgentUpstream.slow_started.clear()
        _AgentUpstream.release_slow.clear()

    def tearDown(self):
        _AgentUpstream.release_slow.set()
        with server_mod._agent_run_lock:
            runs = list(server_mod._agent_runs.values())
        deadline = time.time() + 2
        while any(run.get("worker") is not None for run in runs) and time.time() < deadline:
            time.sleep(0.01)
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp_dir.cleanup()

    def _wait_terminal(self, run, timeout=5):
        deadline = time.time() + timeout
        with run["condition"]:
            while run["status"] not in server_mod._AGENT_RUN_TERMINAL and time.time() < deadline:
                run["condition"].wait(timeout=0.05)
        self.assertIn(run["status"], server_mod._AGENT_RUN_TERMINAL)

    def _wait_status(self, run, expected, timeout=5):
        deadline = time.time() + timeout
        with run["condition"]:
            while run["status"] != expected and time.time() < deadline:
                run["condition"].wait(timeout=0.05)
        self.assertEqual(run["status"], expected)

    def _wait_worker_idle(self, run, timeout=2):
        deadline = time.time() + timeout
        while run.get("worker") is not None and time.time() < deadline:
            time.sleep(0.01)
        self.assertIsNone(run.get("worker"))

    def test_agent_continues_without_browser_polling_and_executes_read_only_loop(self):
        run = server_mod._create_agent_run(
            "session-agent",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "inspect the project"}],
                "tools": [
                    server_mod._SERVER_TOOL_DEFINITIONS["read_file"],
                    {"type": "function", "function": {"name": "write_file", "parameters": {}}},
                ],
            },
            self.base_url,
            ["agent-secret-key"],
            allowed_tools=["read_file", "write_file"],
        )

        # Do not read a snapshot until the worker has reached a terminal state.
        self._wait_terminal(run)
        snapshot = server_mod._agent_snapshot(run, 0)

        self.assertEqual(run["status"], "completed")
        self.assertEqual(_AgentUpstream.calls, 2)
        self.assertEqual(snapshot["allowedTools"], ["read_file"])
        self.assertEqual(snapshot["round"], 2)
        self.assertEqual(snapshot["result"]["content"], "read-only task complete")
        self.assertEqual(snapshot["usage"]["total_tokens"], 20)
        self.assertEqual(len(snapshot["toolExecutions"]), 1)
        self.assertEqual(snapshot["toolExecutions"][0]["name"], "read_file")
        self.assertEqual(snapshot["toolExecutions"][0]["status"], "completed")
        self.assertIn("Durable Agent", json.dumps(snapshot["toolExecutions"][0]["result"]))
        self.assertEqual(run["keys"], [])
        self.assertEqual(
            [item["function"]["name"] for item in _AgentUpstream.payloads[0]["tools"]],
            ["read_file"],
        )
        event_types = [event["type"] for event in snapshot["events"]]
        for expected in (
            "created", "model_started", "model_completed", "tool_started",
            "tool_completed", "completed",
        ):
            self.assertIn(expected, event_types)

        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertNotIn("agent-secret-key", persisted)
        self.assertNotIn("agent-secret-key", json.dumps(snapshot))
        self.assertEqual(_AgentUpstream.authorizations, ["Bearer agent-secret-key"] * 2)

    def test_command_tool_requires_accept_or_bypass_permission(self):
        payload = {"tools": [server_mod._SERVER_TOOL_DEFINITIONS["run_command"]]}
        self.assertEqual(
            server_mod._agent_selected_tools(payload, ["run_command"], "read"),
            [],
        )
        self.assertEqual(
            server_mod._agent_selected_tools(payload, ["run_command"], "plan"),
            [],
        )
        for profile in ("accept", "bypass"):
            with self.subTest(profile=profile):
                selected = server_mod._agent_selected_tools(
                    payload, ["run_command"], profile,
                )
                self.assertEqual(
                    [item["function"]["name"] for item in selected],
                    ["run_command"],
                )

    def test_memory_tool_requires_accept_or_bypass_permission(self):
        payload = {"tools": [server_mod._SERVER_TOOL_DEFINITIONS["save_memory"]]}
        for profile in ("read", "plan"):
            with self.subTest(profile=profile):
                self.assertEqual(
                    server_mod._agent_selected_tools(payload, ["save_memory"], profile),
                    [],
                )
        for profile in ("accept", "bypass"):
            with self.subTest(profile=profile):
                selected = server_mod._agent_selected_tools(
                    payload, ["save_memory"], profile,
                )
                self.assertEqual(
                    [item["function"]["name"] for item in selected],
                    ["save_memory"],
                )

    def test_agent_saves_memory_without_browser_relay_or_authorization_pause(self):
        run = server_mod._create_agent_run(
            "memory-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "remember convention"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["save_memory"]],
            },
            self.base_url,
            ["memory-secret-key"],
            allowed_tools=["save_memory"],
            permission_profile="accept",
        )
        self._wait_terminal(run)

        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "memory task complete")
        self.assertIsNone(snapshot["pendingAuthorization"])
        self.assertEqual(len(snapshot["toolExecutions"]), 1)
        result = snapshot["toolExecutions"][0]["result"]
        self.assertEqual(result["action"], "save_memory")
        self.assertFalse(result["replayed"])
        memory_path = self.data_dir / "memory" / "runtime-convention.md"
        self.assertIn(
            "AgentRun owns durable memory writes.",
            memory_path.read_text(encoding="utf-8"),
        )
        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertNotIn("memory-secret-key", persisted)

    def test_agent_executes_network_and_skill_tools_without_browser_polling(self):
        skill_dir = self.data_dir / "skills" / "runtime-skill"
        reference_dir = skill_dir / "references"
        reference_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: runtime-skill\ndescription: Runtime test\n"
            "tools: read_file\n---\n\nFollow runtime guidance.\n",
            encoding="utf-8",
        )
        (reference_dir / "guide.md").write_text("Runtime reference", encoding="utf-8")
        web_result = {
            "ok": True,
            "action": "web_fetch",
            "url": "https://example.com/docs",
            "status": 200,
            "content": "Public documentation",
        }

        with mock.patch.dict(
            server_mod.SERVER_TOOL_REGISTRY["web_fetch"],
            {"execute": lambda _payload: dict(web_result)},
        ):
            run = server_mod._create_agent_run(
                "network-skill-session",
                {
                    "model": "test-model",
                    "messages": [{"role": "user", "content": "inspect skill and network"}],
                    "tools": [
                        server_mod._SERVER_TOOL_DEFINITIONS["use_skill"],
                        server_mod._SERVER_TOOL_DEFINITIONS["read_skill_resource"],
                        server_mod._SERVER_TOOL_DEFINITIONS["web_fetch"],
                    ],
                },
                self.base_url,
                ["network-skill-key"],
                allowed_tools=["use_skill", "read_skill_resource", "web_fetch"],
            )
            # The worker owns all three calls; no browser snapshot or tool relay
            # is needed before it reaches the final model response.
            self._wait_terminal(run)

        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "network and skill task complete")
        self.assertEqual(
            snapshot["allowedTools"],
            ["use_skill", "read_skill_resource", "web_fetch"],
        )
        executions = {item["name"]: item for item in snapshot["toolExecutions"]}
        self.assertEqual(set(executions), {"use_skill", "read_skill_resource", "web_fetch"})
        self.assertIn("runtime guidance", json.dumps(executions["use_skill"]["result"]))
        self.assertIn("Runtime reference", json.dumps(executions["read_skill_resource"]["result"]))
        self.assertEqual(executions["web_fetch"]["result"], web_result)
        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertNotIn("network-skill-key", persisted)
        self.assertNotIn("network-skill-key", json.dumps(snapshot))

    def test_accept_command_waits_for_authorization_then_executes_once(self):
        run = server_mod._create_agent_run(
            "command-accept-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "run approved command"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["run_command"]],
            },
            self.base_url,
            ["command-before-approval-key"],
            allowed_tools=["run_command"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)
        pending = server_mod._agent_snapshot(run, 0)["pendingAuthorization"]
        self.assertEqual(pending["action"], "run_command")
        self.assertIn("agent-command", pending["command"])
        execution = run["tool_executions"]["agent-command-1"]
        self.assertEqual(execution["status"], "waiting_authorization")

        decision = server_mod._submit_agent_authorization(
            run, pending["authorizationId"], "approved",
        )
        self.assertTrue(decision["authorized"])
        self.assertFalse(decision["executed"])
        self.assertEqual(run["status"], "waiting_credentials")
        self.assertEqual(execution["status"], "authorized")

        server_mod._resume_agent_run(run, ["command-after-approval-key"])
        self._wait_terminal(run)
        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "command task complete")
        command_execution = snapshot["toolExecutions"][0]
        self.assertEqual(command_execution["status"], "completed")
        self.assertTrue(command_execution["result"]["ok"])
        self.assertIn("agent-command", command_execution["result"]["stdout"])
        self.assertEqual(
            [event["type"] for event in snapshot["events"]].count("command_started"),
            1,
        )
        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertNotIn("command-before-approval-key", persisted)
        self.assertNotIn("command-after-approval-key", persisted)

    def test_rejected_command_becomes_tool_result_without_execution(self):
        run = server_mod._create_agent_run(
            "command-reject-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "run approved command"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["run_command"]],
            },
            self.base_url,
            ["command-reject-key"],
            allowed_tools=["run_command"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)
        pending = server_mod._agent_snapshot(run, 0)["pendingAuthorization"]
        with mock.patch.object(server_mod.subprocess, "Popen") as popen_mock:
            result = server_mod._submit_agent_authorization(
                run, pending["authorizationId"], "rejected",
            )
            popen_mock.assert_not_called()
        self.assertTrue(result["rejected"])
        self.assertEqual(run["status"], "waiting_credentials")
        server_mod._resume_agent_run(run, ["command-reject-resume-key"])
        self._wait_terminal(run)
        execution = server_mod._agent_snapshot(run, 0)["toolExecutions"][0]
        self.assertEqual(execution["status"], "completed")
        self.assertTrue(execution["result"]["rejected"])

    def test_bypass_command_persists_output_and_cancel_stops_process(self):
        run = server_mod._create_agent_run(
            "command-cancel-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "run slow command"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["run_command"]],
            },
            self.base_url,
            ["command-cancel-key"],
            allowed_tools=["run_command"],
            permission_profile="bypass",
        )
        deadline = time.time() + 8
        process = None
        while time.time() < deadline:
            execution = run["tool_executions"].get("agent-command-1") or {}
            process = run.get("active_process")
            if execution.get("status") == "running" and "command-started" in execution.get("stdout", ""):
                break
            time.sleep(0.05)
        self.assertIsNotNone(process)
        self.assertIsNone(process.poll())
        persisted_running = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertIn("command-started", persisted_running)

        server_mod._cancel_agent_run(run["id"])
        self._wait_terminal(run)
        self._wait_worker_idle(run)
        self.assertIsNotNone(process.poll())
        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "cancelled")
        execution = snapshot["toolExecutions"][0]
        self.assertEqual(execution["status"], "cancelled")
        self.assertTrue(execution["result"]["cancelled"])
        self.assertIn("command-started", execution["stdout"])

    def test_restart_marks_running_command_unknown_and_never_replays_it(self):
        run_id = uuid.uuid4().hex
        arguments = json.dumps({
            "command": 'python -c "print(\'must-not-run-again\')"',
            "description": "Non-replayable command",
        }, separators=(",", ":"))
        fingerprint = hashlib.sha256(f"run_command\0{arguments}".encode()).hexdigest()
        timestamp = server_mod.now_iso()
        record = {
            "version": 1,
            "id": run_id,
            "sessionId": "command-restart-session",
            "status": "tools",
            "resumeStatus": "",
            "permissionProfile": "bypass",
            "error": "",
            "baseUrl": self.base_url,
            "request": {"model": "test-model", "tool_choice": "auto"},
            "messages": [
                {"role": "user", "content": "run approved command"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "agent-command-1",
                        "type": "function",
                        "function": {"name": "run_command", "arguments": arguments},
                    }],
                },
            ],
            "tools": [server_mod._SERVER_TOOL_DEFINITIONS["run_command"]],
            "rounds": [{"round": 1, "toolCalls": [], "usage": {"total_tokens": 5}}],
            "pendingToolCalls": [{
                "index": 0,
                "id": "agent-command-1",
                "type": "function",
                "function": {"name": "run_command", "arguments": arguments},
                "arguments": json.loads(arguments),
                "parseError": "",
                "fingerprint": fingerprint,
            }],
            "toolExecutions": {
                "agent-command-1": {
                    "name": "run_command",
                    "arguments": arguments,
                    "fingerprint": fingerprint,
                    "status": "running",
                    "command": "must-not-run-again",
                    "cwd": str(self.project_dir),
                    "stdout": "partial output\n",
                    "stderr": "",
                    "startedAt": timestamp,
                    "completedAt": "",
                },
            },
            "usage": {"total_tokens": 5},
            "result": {},
            "events": [],
            "nextSeq": 1,
            "maxRounds": 4,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        server_mod.write_json(server_mod._agent_run_path(run_id), record)

        loaded = server_mod._get_agent_run(run_id)
        self.assertEqual(loaded["status"], "waiting_credentials")
        interrupted = loaded["tool_executions"]["agent-command-1"]
        self.assertEqual(interrupted["status"], "completed")
        self.assertTrue(interrupted["result"]["unknownState"])
        self.assertTrue(interrupted["result"]["notReplayed"])
        with mock.patch.object(server_mod.subprocess, "Popen") as popen_mock:
            server_mod._resume_agent_run(loaded, ["command-restart-key"])
            self._wait_terminal(loaded)
            popen_mock.assert_not_called()
        snapshot = server_mod._agent_snapshot(loaded, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "command task complete")
        self.assertTrue(snapshot["toolExecutions"][0]["result"]["notReplayed"])

    def test_restart_replays_running_memory_write_without_rewriting_file(self):
        payload = {
            "name": "runtime-convention",
            "description": "Runtime convention",
            "body": "AgentRun owns durable memory writes.",
        }
        first = server_mod.execute_registered_tool("save_memory", payload)
        self.assertFalse(first["replayed"])
        memory_path = self.data_dir / "memory" / "runtime-convention.md"
        before = memory_path.read_bytes()
        before_mtime = memory_path.stat().st_mtime_ns

        run_id = uuid.uuid4().hex
        arguments = json.dumps(payload, separators=(",", ":"))
        fingerprint = hashlib.sha256(f"save_memory\0{arguments}".encode()).hexdigest()
        timestamp = server_mod.now_iso()
        record = {
            "version": 1,
            "id": run_id,
            "sessionId": "memory-restart-session",
            "status": "tools",
            "resumeStatus": "",
            "permissionProfile": "accept",
            "error": "",
            "baseUrl": self.base_url,
            "request": {"model": "test-model", "tool_choice": "auto"},
            "messages": [
                {"role": "user", "content": "remember convention"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "agent-memory-1",
                        "type": "function",
                        "function": {"name": "save_memory", "arguments": arguments},
                    }],
                },
            ],
            "tools": [server_mod._SERVER_TOOL_DEFINITIONS["save_memory"]],
            "rounds": [{"round": 1, "toolCalls": [], "usage": {"total_tokens": 5}}],
            "pendingToolCalls": [{
                "index": 0,
                "id": "agent-memory-1",
                "type": "function",
                "function": {"name": "save_memory", "arguments": arguments},
                "arguments": payload,
                "parseError": "",
                "fingerprint": fingerprint,
            }],
            "toolExecutions": {
                "agent-memory-1": {
                    "name": "save_memory",
                    "arguments": arguments,
                    "fingerprint": fingerprint,
                    "status": "running",
                    "result": None,
                    "error": "",
                    "startedAt": timestamp,
                    "completedAt": "",
                },
            },
            "usage": {"total_tokens": 5},
            "result": {},
            "events": [],
            "nextSeq": 1,
            "maxRounds": 4,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        server_mod.write_json(server_mod._agent_run_path(run_id), record)

        loaded = server_mod._get_agent_run(run_id)
        self.assertEqual(loaded["status"], "waiting_credentials")
        original_execute = server_mod.execute_registered_tool
        with mock.patch.object(
            server_mod, "execute_registered_tool", wraps=original_execute,
        ) as execute_mock:
            server_mod._resume_agent_run(loaded, ["memory-restart-key"])
            self._wait_terminal(loaded)
            self.assertEqual(execute_mock.call_count, 1)

        snapshot = server_mod._agent_snapshot(loaded, 0)
        self.assertEqual(snapshot["status"], "completed")
        result = snapshot["toolExecutions"][0]["result"]
        self.assertTrue(result["replayed"])
        self.assertEqual(memory_path.read_bytes(), before)
        self.assertEqual(memory_path.stat().st_mtime_ns, before_mtime)
        self.assertTrue(any(
            event["type"] == "tool_completed" and event["data"].get("replayed")
            for event in snapshot["events"]
        ))
        persisted = server_mod._agent_run_path(run_id).read_text(encoding="utf-8")
        self.assertNotIn("memory-restart-key", persisted)

    def test_agent_questionnaire_waits_durably_and_continues_after_valid_answer(self):
        run = server_mod._create_agent_run(
            "question-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "ask for target"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["request_user_input"]],
            },
            self.base_url,
            ["question-secret-key"],
            allowed_tools=["request_user_input"],
        )
        self._wait_status(run, "waiting_user_input")
        self._wait_worker_idle(run)

        waiting = server_mod._agent_snapshot(run, 0)
        self.assertEqual(waiting["pendingInput"]["requestId"], "user-input-agent-question-1")
        self.assertEqual(waiting["pendingInput"]["questions"][0]["id"], "target")
        self.assertEqual(waiting["toolExecutions"][0]["status"], "waiting_user_input")
        self.assertEqual(run["keys"], [])
        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertIn('"status": "waiting_user_input"', persisted)
        self.assertNotIn("question-secret-key", persisted)

        with self.assertRaisesRegex(ValueError, "invalid choice"):
            server_mod._submit_agent_input(run, [{
                "id": "target",
                "status": "resolved",
                "values": ["invalid"],
            }])
        self.assertEqual(run["status"], "waiting_user_input")

        result = server_mod._submit_agent_input(run, [{
            "id": "target",
            "status": "resolved",
            "values": ["api"],
        }])
        self.assertEqual(result["answers"][0]["answer"], "API")
        self.assertEqual(run["status"], "waiting_credentials")
        server_mod._resume_agent_run(run, ["question-resume-key"])
        self._wait_terminal(run)

        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "questionnaire task complete")
        self.assertIsNone(snapshot["pendingInput"])
        self.assertEqual(snapshot["toolExecutions"][0]["status"], "completed")
        self.assertTrue(any(
            message.get("role") == "tool"
            and message.get("tool_call_id") == "agent-question-1"
            and '"api"' in message.get("content", "")
            for message in run["messages"]
        ))
        event_types = [event["type"] for event in snapshot["events"]]
        for expected in (
            "user_input_required", "user_input_submitted", "tool_completed",
            "waiting_credentials", "resumed", "completed",
        ):
            self.assertIn(expected, event_types)

    def test_accept_profile_waits_for_durable_edit_authorization(self):
        target = self.project_dir / "README.md"
        run = server_mod._create_agent_run(
            "edit-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "propose edit"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
            },
            self.base_url,
            ["edit-secret-key"],
            allowed_tools=["propose_edit"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)

        waiting = server_mod._agent_snapshot(run, 0)
        pending = waiting["pendingAuthorization"]
        self.assertEqual(waiting["permissionProfile"], "accept")
        self.assertEqual(pending["toolCallId"], "agent-edit-1")
        self.assertEqual(pending["path"], "README.md")
        self.assertIn("Authorized Agent", pending["diff"])
        self.assertNotIn("newContent", pending)
        self.assertEqual(target.read_text(encoding="utf-8"), "# Durable Agent\n")
        self.assertEqual(run["keys"], [])
        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertIn('"status": "waiting_authorization"', persisted)
        self.assertNotIn("edit-secret-key", persisted)

        result = server_mod._submit_agent_authorization(
            run, pending["authorizationId"], "approved",
        )
        self.assertTrue(result["applied"])
        self.assertFalse(result["replayed"])
        self.assertEqual(target.read_text(encoding="utf-8"), "# Authorized Agent\n")
        self.assertEqual(run["status"], "waiting_credentials")
        self.assertEqual(len(list((self.data_dir / "file-backups").glob("*.bak"))), 1)

        server_mod._resume_agent_run(run, ["edit-resume-key"])
        self._wait_terminal(run)
        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "edit task complete")
        self.assertIsNone(snapshot["pendingAuthorization"])
        event_types = [event["type"] for event in snapshot["events"]]
        for expected in (
            "authorization_required", "authorization_submitted",
            "tool_completed", "waiting_credentials", "resumed", "completed",
        ):
            self.assertIn(expected, event_types)

    def test_plan_profile_returns_edit_proposal_without_writing(self):
        target = self.project_dir / "README.md"
        run = server_mod._create_agent_run(
            "edit-plan-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "propose edit"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
            },
            self.base_url,
            ["edit-plan-key"],
            allowed_tools=["propose_edit"],
            permission_profile="plan",
        )
        self._wait_terminal(run)
        snapshot = server_mod._agent_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["toolExecutions"][0]["status"], "completed")
        self.assertTrue(snapshot["toolExecutions"][0]["result"]["proposalOnly"])
        self.assertEqual(target.read_text(encoding="utf-8"), "# Durable Agent\n")
        self.assertFalse((self.data_dir / "file-backups").exists())

    def test_rejected_edit_authorization_keeps_file_unchanged(self):
        target = self.project_dir / "README.md"
        run = server_mod._create_agent_run(
            "edit-reject-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "propose edit"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
            },
            self.base_url,
            ["edit-reject-key"],
            allowed_tools=["propose_edit"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)
        pending = server_mod._agent_snapshot(run, 0)["pendingAuthorization"]
        with server_mod._agent_run_lock:
            server_mod._agent_runs.pop(run["id"], None)
        loaded = server_mod._get_agent_run(run["id"])
        self.assertEqual(loaded["status"], "waiting_authorization")
        self.assertEqual(
            server_mod._agent_snapshot(loaded, 0)["pendingAuthorization"]["authorizationId"],
            pending["authorizationId"],
        )
        result = server_mod._submit_agent_authorization(
            loaded, pending["authorizationId"], "rejected",
        )
        self.assertTrue(result["rejected"])
        self.assertFalse(result["applied"])
        self.assertEqual(target.read_text(encoding="utf-8"), "# Durable Agent\n")
        self.assertFalse((self.data_dir / "file-backups").exists())

    def test_edit_proposal_apply_is_idempotent_after_written_content(self):
        proposal = server_mod.execute_propose_edit_tool({
            "path": "README.md",
            "oldText": "Durable Agent",
            "newText": "Authorized Agent",
        })
        first = server_mod.execute_apply_edit_proposal(proposal)
        second = server_mod.execute_apply_edit_proposal(proposal)
        self.assertTrue(first["applied"])
        self.assertFalse(first["replayed"])
        self.assertTrue(second["applied"])
        self.assertTrue(second["replayed"])
        self.assertEqual(len(list((self.data_dir / "file-backups").glob("*.bak"))), 1)

    def test_approved_stale_edit_returns_conflict_without_overwriting(self):
        target = self.project_dir / "README.md"
        run = server_mod._create_agent_run(
            "edit-conflict-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "propose edit"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
            },
            self.base_url,
            ["edit-conflict-key"],
            allowed_tools=["propose_edit"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)
        pending = server_mod._agent_snapshot(run, 0)["pendingAuthorization"]
        target.write_text("# Changed elsewhere\n", encoding="utf-8")
        result = server_mod._submit_agent_authorization(
            run, pending["authorizationId"], "approved",
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["conflict"])
        self.assertFalse(result["applied"])
        self.assertEqual(target.read_text(encoding="utf-8"), "# Changed elsewhere\n")
        self.assertFalse((self.data_dir / "file-backups").exists())

    def test_restart_after_write_replays_approved_edit_without_second_backup(self):
        run = server_mod._create_agent_run(
            "edit-replay-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "propose edit"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
            },
            self.base_url,
            ["edit-replay-key"],
            allowed_tools=["propose_edit"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)
        pending = server_mod._agent_snapshot(run, 0)["pendingAuthorization"]
        first = server_mod.execute_apply_edit_proposal(run["pending_authorization"]["proposal"])
        self.assertFalse(first["replayed"])
        with server_mod._agent_run_lock:
            server_mod._agent_runs.pop(run["id"], None)
        loaded = server_mod._get_agent_run(run["id"])
        second = server_mod._submit_agent_authorization(
            loaded, pending["authorizationId"], "approved",
        )
        self.assertTrue(second["replayed"])
        self.assertEqual(len(list((self.data_dir / "file-backups").glob("*.bak"))), 1)

    def test_bypass_restart_reuses_persisted_proposal_after_write(self):
        run = server_mod._create_agent_run(
            "edit-bypass-replay-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "propose edit"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
            },
            self.base_url,
            ["edit-bypass-key"],
            allowed_tools=["propose_edit"],
            permission_profile="accept",
        )
        self._wait_status(run, "waiting_authorization")
        self._wait_worker_idle(run)
        proposal = run["pending_authorization"]["proposal"]
        first = server_mod.execute_apply_edit_proposal(proposal)
        self.assertFalse(first["replayed"])
        execution = run["tool_executions"]["agent-edit-1"]
        execution["status"] = "applying_edit"
        execution["proposal"] = proposal
        run["permission_profile"] = "bypass"
        run["pending_authorization"] = None
        run["status"] = "tools"
        server_mod._persist_agent_run(run)
        with server_mod._agent_run_lock:
            server_mod._agent_runs.pop(run["id"], None)

        loaded = server_mod._get_agent_run(run["id"])
        self.assertEqual(loaded["status"], "waiting_credentials")
        with mock.patch.object(server_mod, "execute_registered_tool") as execute_mock:
            server_mod._resume_agent_run(loaded, ["edit-bypass-resume-key"])
            self._wait_terminal(loaded)
            execute_mock.assert_not_called()
        result = loaded["tool_executions"]["agent-edit-1"]["result"]
        self.assertTrue(result["replayed"])
        self.assertEqual(len(list((self.data_dir / "file-backups").glob("*.bak"))), 1)

    def test_restart_recovery_reuses_completed_tool_execution(self):
        run_id = uuid.uuid4().hex
        arguments = '{"path":"README.md"}'
        fingerprint = hashlib.sha256(f"read_file\0{arguments}".encode()).hexdigest()
        timestamp = server_mod.now_iso()
        tool_result = {
            "ok": True,
            "action": "read_file",
            "path": "README.md",
            "content": "# Durable Agent\n",
            "size": 16,
            "truncated": False,
            "lineRange": None,
        }
        record = {
            "version": 1,
            "id": run_id,
            "sessionId": "restart-session",
            "status": "tools",
            "resumeStatus": "",
            "error": "",
            "baseUrl": self.base_url,
            "request": {"model": "test-model", "tool_choice": "auto"},
            "messages": [
                {"role": "user", "content": "inspect after restart"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "agent-call-1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": arguments},
                    }],
                },
            ],
            "tools": [server_mod._SERVER_TOOL_DEFINITIONS["read_file"]],
            "rounds": [{"round": 1, "toolCalls": [], "usage": {"total_tokens": 9}}],
            "pendingToolCalls": [{
                "index": 0,
                "id": "agent-call-1",
                "type": "function",
                "function": {"name": "read_file", "arguments": arguments},
                "arguments": {"path": "README.md"},
                "parseError": "",
                "fingerprint": fingerprint,
            }],
            "toolExecutions": {
                "agent-call-1": {
                    "name": "read_file",
                    "arguments": arguments,
                    "fingerprint": fingerprint,
                    "status": "completed",
                    "result": tool_result,
                    "error": "",
                    "startedAt": timestamp,
                    "completedAt": timestamp,
                },
            },
            "usage": {"total_tokens": 9},
            "result": {},
            "events": [],
            "nextSeq": 1,
            "maxRounds": 4,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        server_mod.write_json(server_mod._agent_run_path(run_id), record)

        loaded = server_mod._get_agent_run(run_id)
        self.assertEqual(loaded["status"], "waiting_credentials")
        with mock.patch.object(server_mod, "execute_registered_tool") as execute_mock:
            server_mod._resume_agent_run(loaded, ["restart-secret-key"])
            self._wait_terminal(loaded)
            execute_mock.assert_not_called()

        snapshot = server_mod._agent_snapshot(loaded, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["content"], "read-only task complete")
        self.assertEqual(_AgentUpstream.calls, 1)
        self.assertTrue(any(
            message.get("role") == "tool" and message.get("tool_call_id") == "agent-call-1"
            for message in loaded["messages"]
        ))
        persisted = server_mod._agent_run_path(run_id).read_text(encoding="utf-8")
        self.assertNotIn("restart-secret-key", persisted)

    def test_restart_preserves_pending_questionnaire_before_credentials_resume(self):
        run = server_mod._create_agent_run(
            "question-restart-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "ask for target"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["request_user_input"]],
            },
            self.base_url,
            ["question-before-restart-key"],
            allowed_tools=["request_user_input"],
        )
        self._wait_status(run, "waiting_user_input")
        self._wait_worker_idle(run)
        run_id = run["id"]
        with server_mod._agent_run_lock:
            server_mod._agent_runs.pop(run_id, None)

        loaded = server_mod._get_agent_run(run_id)
        self.assertEqual(loaded["status"], "waiting_user_input")
        self.assertEqual(loaded["pending_input"]["toolCallId"], "agent-question-1")
        self.assertEqual(loaded["keys"], [])

        server_mod._submit_agent_input(loaded, [{
            "id": "target",
            "status": "resolved",
            "values": ["ui"],
        }])
        self.assertEqual(loaded["status"], "waiting_credentials")
        server_mod._resume_agent_run(loaded, ["question-after-restart-key"])
        self._wait_terminal(loaded)
        self.assertEqual(loaded["result"]["content"], "questionnaire task complete")
        self.assertEqual(_AgentUpstream.calls, 2)

    def test_repeated_tool_call_id_reuses_execution_but_keeps_protocol_pair(self):
        original_execute = server_mod.execute_registered_tool
        with mock.patch.object(
            server_mod,
            "execute_registered_tool",
            wraps=original_execute,
        ) as execute_mock:
            run = server_mod._create_agent_run(
                "repeat-call-session",
                {
                    "model": "test-model",
                    "messages": [{"role": "user", "content": "repeat tool id"}],
                    "tools": [server_mod._SERVER_TOOL_DEFINITIONS["read_file"]],
                },
                self.base_url,
                ["repeat-secret-key"],
                allowed_tools=["read_file"],
                max_rounds=4,
            )
            self._wait_terminal(run)

        self.assertEqual(run["status"], "completed")
        self.assertEqual(_AgentUpstream.calls, 3)
        self.assertEqual(execute_mock.call_count, 1)
        self.assertEqual(
            sum(message.get("role") == "tool" for message in run["messages"]),
            2,
        )
        replay_events = [
            event for event in run["events"]
            if event["type"] == "tool_completed" and event["data"].get("replayed")
        ]
        self.assertEqual(len(replay_events), 1)

    def test_model_round_limit_is_enforced(self):
        run = server_mod._create_agent_run(
            "round-limit-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "repeat tool id"}],
                "tools": [server_mod._SERVER_TOOL_DEFINITIONS["read_file"]],
            },
            self.base_url,
            ["round-limit-secret-key"],
            allowed_tools=["read_file"],
            max_rounds=2,
        )
        self._wait_terminal(run)

        self.assertEqual(run["status"], "failed")
        self.assertIn("exceeded 2 model rounds", run["error"])
        self.assertEqual(_AgentUpstream.calls, 2)
        self.assertEqual(run["keys"], [])

    def test_credentials_inside_payload_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            server_mod._create_agent_run(
                "session-agent",
                {
                    "model": "test-model",
                    "apiKey": "must-not-persist",
                    "messages": [{"role": "user", "content": "hi"}],
                },
                self.base_url,
                [],
            )
        with self.assertRaisesRegex(ValueError, "credentials"):
            server_mod._create_agent_run(
                "session-agent",
                {
                    "model": "test-model",
                    "extra_body": {"authorization": "Bearer must-not-persist"},
                    "messages": [{"role": "user", "content": "hi"}],
                },
                self.base_url,
                [],
            )
        with self.assertRaisesRegex(ValueError, "credentials"):
            server_mod._create_agent_run(
                "session-agent",
                {
                    "model": "test-model",
                    "messages": [{"role": "user", "content": "hi"}],
                },
                "https://secret@example.com/v1",
                [],
            )

    def test_http_create_poll_and_idempotent_cancel(self):
        server_mod.ThreadingHTTPServer.daemon_threads = True
        http_server = server_mod.ThreadingHTTPServer(
            ("127.0.0.1", 0), server_mod.CodeHandler,
        )
        thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{http_server.server_address[1]}"
        try:
            response = requests.post(
                base + "/api/agent/runs",
                json={
                    "sessionId": "http-agent",
                    "payload": {
                        "model": "test-model",
                        "messages": [{"role": "user", "content": "inspect through HTTP"}],
                        "tools": [server_mod._SERVER_TOOL_DEFINITIONS["read_file"]],
                    },
                    "allowedTools": ["read_file"],
                    "baseUrl": self.base_url,
                    "keys": ["http-secret-key"],
                },
                timeout=5,
            )
            self.assertEqual(response.status_code, 201)
            run_id = response.json()["agentRunId"]

            deadline = time.time() + 5
            snapshot = {}
            while time.time() < deadline:
                poll = requests.get(
                    f"{base}/api/agent/runs/{run_id}?cursor=0&wait=1",
                    timeout=3,
                )
                self.assertEqual(poll.status_code, 200)
                snapshot = poll.json()
                if snapshot.get("status") in server_mod._AGENT_RUN_TERMINAL:
                    break
            self.assertEqual(snapshot.get("status"), "completed")
            self.assertEqual(snapshot.get("result", {}).get("content"), "read-only task complete")
            self.assertNotIn("http-secret-key", json.dumps(snapshot))

            cancel = requests.delete(f"{base}/api/agent/runs/{run_id}", timeout=3)
            self.assertEqual(cancel.status_code, 200)
            self.assertEqual(cancel.json()["status"], "completed")
        finally:
            http_server.shutdown()
            http_server.server_close()
            thread.join(timeout=2)

    def test_http_questionnaire_submit_endpoint_resumes_same_agent_run(self):
        server_mod.ThreadingHTTPServer.daemon_threads = True
        http_server = server_mod.ThreadingHTTPServer(
            ("127.0.0.1", 0), server_mod.CodeHandler,
        )
        thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{http_server.server_address[1]}"
        try:
            created = requests.post(
                base + "/api/agent/runs",
                json={
                    "sessionId": "http-question-agent",
                    "payload": {
                        "model": "test-model",
                        "messages": [{"role": "user", "content": "ask for target"}],
                        "tools": [server_mod._SERVER_TOOL_DEFINITIONS["request_user_input"]],
                    },
                    "allowedTools": ["request_user_input"],
                    "baseUrl": self.base_url,
                    "keys": ["http-question-key"],
                },
                timeout=5,
            )
            self.assertEqual(created.status_code, 201)
            run_id = created.json()["agentRunId"]

            deadline = time.time() + 5
            snapshot = {}
            while time.time() < deadline:
                snapshot = requests.get(
                    f"{base}/api/agent/runs/{run_id}?cursor=0&wait=1",
                    timeout=3,
                ).json()
                if snapshot.get("status") == "waiting_user_input":
                    break
            self.assertEqual(snapshot.get("status"), "waiting_user_input")
            self.assertEqual(snapshot.get("pendingInput", {}).get("toolCallId"), "agent-question-1")

            submitted = requests.post(
                f"{base}/api/agent/runs/{run_id}/input",
                json={"answers": [{
                    "id": "target",
                    "status": "resolved",
                    "values": ["ui"],
                }]},
                timeout=3,
            )
            self.assertEqual(submitted.status_code, 200)
            self.assertEqual(submitted.json()["status"], "waiting_credentials")

            resumed = requests.post(
                f"{base}/api/agent/runs/{run_id}/resume",
                json={"keys": ["http-question-resume-key"], "baseUrl": self.base_url},
                timeout=3,
            )
            self.assertEqual(resumed.status_code, 200)
            deadline = time.time() + 5
            while time.time() < deadline:
                snapshot = requests.get(
                    f"{base}/api/agent/runs/{run_id}?cursor=0&wait=1",
                    timeout=3,
                ).json()
                if snapshot.get("status") in server_mod._AGENT_RUN_TERMINAL:
                    break
            self.assertEqual(snapshot.get("status"), "completed")
            self.assertEqual(snapshot.get("result", {}).get("content"), "questionnaire task complete")
        finally:
            http_server.shutdown()
            http_server.server_close()
            thread.join(timeout=2)

    def test_http_edit_authorization_endpoint_submits_durable_decision(self):
        server_mod.ThreadingHTTPServer.daemon_threads = True
        http_server = server_mod.ThreadingHTTPServer(
            ("127.0.0.1", 0), server_mod.CodeHandler,
        )
        thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{http_server.server_address[1]}"
        try:
            created = requests.post(
                base + "/api/agent/runs",
                json={
                    "sessionId": "http-edit-agent",
                    "payload": {
                        "model": "test-model",
                        "messages": [{"role": "user", "content": "propose edit"}],
                        "tools": [server_mod._SERVER_TOOL_DEFINITIONS["propose_edit"]],
                    },
                    "allowedTools": ["propose_edit"],
                    "permissionProfile": "accept",
                    "baseUrl": self.base_url,
                    "keys": ["http-edit-key"],
                },
                timeout=5,
            )
            self.assertEqual(created.status_code, 201)
            run_id = created.json()["agentRunId"]
            deadline = time.time() + 5
            snapshot = {}
            while time.time() < deadline:
                snapshot = requests.get(
                    f"{base}/api/agent/runs/{run_id}?cursor=0&wait=1",
                    timeout=3,
                ).json()
                if snapshot.get("status") == "waiting_authorization":
                    break
            pending = snapshot.get("pendingAuthorization") or {}
            self.assertEqual(snapshot.get("status"), "waiting_authorization")

            submitted = requests.post(
                f"{base}/api/agent/runs/{run_id}/authorization",
                json={
                    "authorizationId": pending.get("authorizationId"),
                    "decision": "rejected",
                },
                timeout=3,
            )
            self.assertEqual(submitted.status_code, 200)
            self.assertEqual(submitted.json()["status"], "waiting_credentials")
            self.assertTrue(submitted.json()["result"]["rejected"])
            self.assertEqual(
                (self.project_dir / "README.md").read_text(encoding="utf-8"),
                "# Durable Agent\n",
            )
        finally:
            http_server.shutdown()
            http_server.server_close()
            thread.join(timeout=2)

    def test_cancel_stops_active_model_round_and_clears_credentials(self):
        run = server_mod._create_agent_run(
            "cancel-session",
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "slow request"}],
            },
            self.base_url,
            ["cancel-secret-key"],
            allowed_tools=[],
        )
        self.assertTrue(_AgentUpstream.slow_started.wait(timeout=2))
        self.assertTrue(server_mod._cancel_agent_run(run["id"]))
        _AgentUpstream.release_slow.set()
        self._wait_terminal(run)

        self.assertEqual(run["status"], "cancelled")
        self.assertEqual(run["keys"], [])
        time.sleep(0.05)
        event_types = [event["type"] for event in run["events"]]
        self.assertEqual(event_types[-1], "cancelled")
        persisted = server_mod._agent_run_path(run["id"]).read_text(encoding="utf-8")
        self.assertNotIn("cancel-secret-key", persisted)


if __name__ == "__main__":
    unittest.main()

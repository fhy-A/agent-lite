"""Server-owned model runtime regression tests.

Run: python -m pytest tests/test_model_runtime.py -v
"""

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import server as server_mod


class _StreamingUpstream(BaseHTTPRequestHandler):
    calls = 0
    authorizations = []

    def log_message(self, *_args):
        return

    def do_POST(self):
        type(self).calls += 1
        type(self).authorizations.append(self.headers.get("Authorization", ""))
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.end_headers()
        user_content = (payload.get("messages") or [{}])[-1].get("content")
        if user_content == "call a tool":
            frames = [
                {
                    "choices": [{
                        "delta": {
                            "reasoning_content": "checking files",
                            "tool_calls": [{
                                "index": 0,
                                "id": "call-1",
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
                {
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 7,
                        "completion_tokens": 4,
                        "total_tokens": 11,
                    },
                },
            ]
        else:
            frames = [
                {"choices": [{"delta": {"reasoning_content": "checking"}}]},
                {"choices": [{"delta": {"content": "hello"}, "finish_reason": "stop"}]},
                {
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 2,
                        "total_tokens": 5,
                    },
                },
            ]
        for frame in frames:
            self.wfile.write(
                ("data: " + json.dumps(frame, ensure_ascii=False) + "\n\n").encode("utf-8")
            )
            self.wfile.flush()
            time.sleep(0.01)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class TestModelRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _StreamingUpstream.calls = 0
        _StreamingUpstream.authorizations = []
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), _StreamingUpstream)
        cls.thread = threading.Thread(target=cls.upstream.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.upstream.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.upstream.shutdown()
        cls.upstream.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        _StreamingUpstream.calls = 0
        _StreamingUpstream.authorizations = []
        with server_mod._model_runtime_lock:
            server_mod._model_runtime_runs.clear()

    def _wait_for_terminal(self, run, timeout=3):
        deadline = time.time() + timeout
        with run["condition"]:
            while run["status"] == "running" and time.time() < deadline:
                run["condition"].wait(timeout=0.05)
        self.assertNotEqual(run["status"], "running")

    def test_same_run_can_be_replayed_without_second_upstream_request(self):
        run = server_mod._create_model_runtime_run(
            "session-a",
            {"model": "test-model", "messages": [{"role": "user", "content": "hi"}]},
            self.base_url,
            ["secret-test-key"],
        )
        self._wait_for_terminal(run)

        first_browser = server_mod._runtime_snapshot(run, 0)
        refreshed_browser = server_mod._runtime_snapshot(run, 0)

        self.assertEqual(run["status"], "completed")
        self.assertEqual(_StreamingUpstream.calls, 1)
        self.assertEqual(_StreamingUpstream.authorizations, ["Bearer secret-test-key"])
        self.assertEqual(first_browser["events"], refreshed_browser["events"])
        self.assertEqual(first_browser["events"][-1]["data"], "[DONE]")
        self.assertIn("hello", json.dumps(first_browser, ensure_ascii=False))
        self.assertEqual(first_browser["result"]["content"], "hello")
        self.assertEqual(first_browser["result"]["reasoning"], "checking")
        self.assertEqual(first_browser["result"]["finishReason"], "stop")
        self.assertEqual(first_browser["result"]["usage"]["total_tokens"], 5)

    def test_runtime_aggregates_split_tool_call_without_browser_parser(self):
        run = server_mod._create_model_runtime_run(
            "session-tool",
            {"model": "test-model", "messages": [{"role": "user", "content": "call a tool"}]},
            self.base_url,
            ["secret-test-key"],
        )
        self._wait_for_terminal(run)

        snapshot = server_mod._runtime_snapshot(run, 0)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["reasoning"], "checking files")
        self.assertEqual(snapshot["result"]["finishReason"], "tool_calls")
        self.assertEqual(snapshot["result"]["usage"]["total_tokens"], 11)
        self.assertEqual(snapshot["result"]["toolCalls"], [{
            "index": 0,
            "id": "call-1",
            "type": "function",
            "function": {"name": "read_file", "arguments": "{\"path\":\"README.md\"}"},
        }])

    def test_runtime_snapshot_never_exposes_credentials_or_request_payload(self):
        run = server_mod._create_model_runtime_run(
            "session-b",
            {"model": "test-model", "messages": [{"role": "user", "content": "private"}]},
            self.base_url,
            ["secret-test-key"],
        )
        self._wait_for_terminal(run)

        snapshot_text = json.dumps(server_mod._runtime_snapshot(run, 0), ensure_ascii=False)
        self.assertNotIn("secret-test-key", snapshot_text)
        self.assertNotIn("private", snapshot_text)
        self.assertEqual(run["keys"], [])
        self.assertEqual(run["payload"], {})


if __name__ == "__main__":
    unittest.main()

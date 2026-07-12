"""
P2 Session Branching Integration Tests.

Run: python -m pytest tests/test_branch.py -v
"""
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server as server_mod


def _free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_PORT = _free_port()
_BASE = f"http://127.0.0.1:{_PORT}"


def _req(method, path, **kwargs):
    url = f"{_BASE}{path}"
    resp = requests.request(method, url, timeout=10, **kwargs)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text


class TestSessionBranching(unittest.TestCase):
    _parent_id = None
    _branch_id = None
    _sub_branch_id = None

    @classmethod
    def setUpClass(cls):
        cls.tmp_root = Path(tempfile.mkdtemp(prefix="agentlite_br_"))
        cls.tmp_data = Path(tempfile.mkdtemp(prefix="agentlite_brd_"))
        for sub in ["sessions", "memory", "skills", "attachments", "file-backups"]:
            (cls.tmp_data / sub).mkdir(parents=True, exist_ok=True)

        config = {
            "projectRoot": str(cls.tmp_root),
            "newApiBaseUrl": "http://localhost:3000",
            "userHome": str(Path.home()),
        }
        (cls.tmp_data / "config.json").write_text(json.dumps(config), encoding="utf-8")

        cls._patchers = [
            mock.patch.object(server_mod, "DATA_DIR", cls.tmp_data),
            mock.patch.object(server_mod, "CONFIG_PATH", cls.tmp_data / "config.json"),
            mock.patch.object(server_mod, "SESSIONS_DIR", cls.tmp_data / "sessions"),
            mock.patch.object(server_mod, "MEMORY_DIR", cls.tmp_data / "memory"),
            mock.patch.object(server_mod, "SKILLS_DIR", cls.tmp_data / "skills"),
            mock.patch.object(server_mod, "ATTACHMENTS_DIR", cls.tmp_data / "attachments"),
            mock.patch.object(server_mod, "FILE_BACKUP_DIR", cls.tmp_data / "file-backups"),
            mock.patch.object(server_mod, "APP_DIR", cls.tmp_root),
        ]
        for p in cls._patchers:
            p.start()

        server_mod.ThreadingHTTPServer.daemon_threads = True
        cls._server = server_mod.ThreadingHTTPServer(
            ("127.0.0.1", _PORT), server_mod.AgentLiteHandler
        )
        cls._server.socket.settimeout(2.0)
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        for p in cls._patchers:
            p.stop()

    def test_01_create_branch(self):
        """Create parent session, save messages, then branch from it."""
        # Create parent
        status, data = _req("POST", "/api/sessions", json={"title": "Parent Session"})
        self.assertEqual(status, 201)
        TestSessionBranching._parent_id = data["id"]
        self.assertTrue(Path(data["_filePath"]).exists())
        # Save messages to parent
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        _req("PUT", f"/api/sessions/{self._parent_id}", json={
            "title": "Parent Session", "messages": messages,
        })
        # Branch from parent
        status, data = _req("POST", f"/api/sessions/{self._parent_id}/branch", json={
            "title": "My Branch",
        })
        self.assertEqual(status, 201)
        self.assertIn("id", data)
        self.assertEqual(data.get("_parentId"), self._parent_id)
        self.assertEqual(data.get("_branchDepth"), 1)
        self.assertEqual(len(data.get("messages", [])), 2)
        self.assertEqual(data["messages"][0]["content"], "Hello")
        TestSessionBranching._branch_id = data["id"]

    def test_02_parent_tracks_branch(self):
        self.assertIsNotNone(self._parent_id)
        status, data = _req("GET", f"/api/sessions/{self._parent_id}")
        self.assertEqual(status, 200)
        self.assertIn(TestSessionBranching._branch_id, data.get("_branches", []))

    def test_03_list_includes_metadata(self):
        self.assertIsNotNone(self._branch_id)
        status, data = _req("GET", "/api/sessions")
        self.assertEqual(status, 200)
        sessions = data.get("data") or []
        branch = next((s for s in sessions if s["id"] == self._branch_id), None)
        self.assertIsNotNone(branch)
        self.assertEqual(branch.get("_parentId"), self._parent_id)
        self.assertEqual(branch.get("_branchDepth"), 1)

    def test_04_sub_branch_depth_2(self):
        self.assertIsNotNone(self._branch_id)
        status, data = _req("POST", f"/api/sessions/{self._branch_id}/branch", json={
            "title": "Sub-branch",
        })
        self.assertEqual(status, 201)
        self.assertEqual(data.get("_parentId"), self._branch_id)
        self.assertEqual(data.get("_branchDepth"), 2)
        TestSessionBranching._sub_branch_id = data["id"]

    def test_05_branch_not_found_404(self):
        status, data = _req("POST", "/api/sessions/nonexistent99/branch", json={})
        self.assertEqual(status, 404)

    def test_06_delete_cleans_parent_ref(self):
        self.assertIsNotNone(self._sub_branch_id)
        _req("DELETE", f"/api/sessions/{self._sub_branch_id}")
        status, data = _req("GET", f"/api/sessions/{self._branch_id}")
        self.assertNotIn(self._sub_branch_id, data.get("_branches", []))
        TestSessionBranching._sub_branch_id = None  # cleared

    def test_06b_delete_root_reparents_children(self):
        """Deleting root session promotes children to root level."""
        # Create parent A with child B
        st1, d1 = _req("POST", "/api/sessions", json={"title": "Root A"})
        self.assertEqual(st1, 201)
        _req("PUT", f"/api/sessions/{d1['id']}", json={
            "title": "Root A", "messages": [{"role": "user", "content": "msg"}],
        })
        st2, d2 = _req("POST", f"/api/sessions/{d1['id']}/branch", json={"title": "Child B"})
        self.assertEqual(st2, 201)
        # Verify child has _parentId
        st3, d3 = _req("GET", f"/api/sessions/{d2['id']}")
        self.assertEqual(d3.get("_parentId"), d1["id"])
        # Delete root
        _req("DELETE", f"/api/sessions/{d1['id']}")
        # Child should now have no _parentId (promoted to root)
        st4, d4 = _req("GET", f"/api/sessions/{d2['id']}")
        self.assertIsNone(d4.get("_parentId"))
        self.assertEqual(d4.get("_branchDepth"), 0)

    def test_07_branch_messages_independent(self):
        """Messages in branch are independent copies — parent changes don't affect branch."""
        self.assertIsNotNone(self._parent_id)
        self.assertIsNotNone(self._branch_id)
        # Add a new message to parent
        _req("PUT", f"/api/sessions/{self._parent_id}", json={
            "title": "Parent Session",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "New message in parent only"},
            ],
        })
        # Branch should still have exactly 2 messages
        status, data = _req("GET", f"/api/sessions/{self._branch_id}")
        self.assertEqual(status, 200)
        self.assertEqual(len(data.get("messages", [])), 2)
        self.assertNotIn("New message", str(data["messages"]))

    def test_08_default_branch_title(self):
        """Branch without explicit title inherits parent title (i18n prefix handled by frontend)."""
        status, data = _req("POST", f"/api/sessions/{self._parent_id}/branch", json={})
        self.assertEqual(status, 201)
        # Server uses parent title as fallback; frontend adds i18n prefix
        self.assertTrue(data.get("title"))

    def test_09_create_session_with_branch_metadata(self):
        """Creating session with _parentId directly works."""
        status, data = _req("POST", "/api/sessions", json={
            "title": "Direct Child",
            "_parentId": self._parent_id,
            "_branchDepth": 1,
        })
        self.assertEqual(status, 201)
        self.assertEqual(data.get("_parentId"), self._parent_id)


if __name__ == "__main__":
    unittest.main()

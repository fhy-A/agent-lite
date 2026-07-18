"""P0 stability regression tests.

Run: python -m pytest tests/test_p0_stability.py -v
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import server as server_mod


ROOT = Path(__file__).resolve().parent.parent
APP_SOURCE = (ROOT / "app.js").read_text(encoding="utf-8")
RUNTIME_SOURCE = (ROOT / "agent-runtime.js").read_text(encoding="utf-8")


class TestFrontendNetworkRecovery(unittest.TestCase):
    def test_request_timeout_does_not_abort_whole_agent_run(self):
        self.assertIn("function createRequestSignal(userSignal, timeoutMs)", APP_SOURCE)
        self.assertIn("timedOut = true", APP_SOURCE)
        self.assertIn("controller.abort();", APP_SOURCE)
        self.assertIn("timedOut: () => timedOut", APP_SOURCE)
        self.assertNotIn("setTimeout(() => run.abortController.abort(), FETCH_TIMEOUT_MS)", APP_SOURCE)

    def test_transient_failures_use_bounded_backoff(self):
        self.assertIn("const maxAttempts = 5", APP_SOURCE)
        self.assertIn("const delays = [1000, 2000, 4000, 8000, 15000]", APP_SOURCE)
        self.assertIn("isTransientModelError(error)", APP_SOURCE)
        self.assertIn('persistRunCheckpoint(ctx, "waiting-network", "model"', APP_SOURCE)

    def test_incomplete_sse_is_not_treated_as_success(self):
        self.assertIn("let streamCompleted = false", APP_SOURCE)
        self.assertIn('code: "stream_interrupted"', APP_SOURCE)
        self.assertIn("Stream interrupted before completion", APP_SOURCE)

    def test_runtime_poll_reconnect_is_visible_in_active_answer(self):
        for expected in (
            "onReconnect",
            "onReconnected",
            "nextRetryAt: Date.now() + delay",
        ):
            self.assertIn(expected, RUNTIME_SOURCE)
        for expected in (
            "networkReconnectStatus",
            "renderNetworkRecoveryStatus(state.sessionId)",
            'source: "runtime-poll"',
            "network-reconnect-countdown",
        ):
            self.assertIn(expected, APP_SOURCE)


class TestFrontendRefreshRecovery(unittest.TestCase):
    def test_completed_session_restore_scrolls_after_layout(self):
        self.assertIn("function scheduleMessagesScrollToBottom(sessionId = state.sessionId)", APP_SOURCE)
        self.assertIn("if (state.sessionId !== sessionId) return", APP_SOURCE)
        self.assertIn("els.messages.scrollTop = els.messages.scrollHeight", APP_SOURCE)

        load_session = APP_SOURCE[
            APP_SOURCE.index("async function loadSession(sessionId)"):
            APP_SOURCE.index("async function saveSessionState", APP_SOURCE.index("async function loadSession(sessionId)"))
        ]
        self.assertEqual(load_session.count("scheduleMessagesScrollToBottom("), 2)

        timeline = APP_SOURCE[
            APP_SOURCE.index("function renderTimeline()"):
            APP_SOURCE.index("function getToolLogDetail", APP_SOURCE.index("function renderTimeline()"))
        ]
        self.assertNotIn("els.messages.scrollTop", timeline)

    def test_recovery_is_locked_per_session(self):
        self.assertIn("async function withSessionRecoveryLock(sessionId, worker)", APP_SOURCE)
        self.assertIn("navigator.locks?.request", APP_SOURCE)
        self.assertIn("code-run-recovery-lease", APP_SOURCE)

    def test_recovery_reuses_server_runtime_stream_and_guards_side_effects(self):
        self.assertIn("function prepareMessagesForRunRecovery(messages, runState)", APP_SOURCE)
        self.assertIn('runState?.phase === "model"', APP_SOURCE)
        self.assertIn("Boolean(runState?.runtimeRunId)", APP_SOURCE)
        self.assertIn("if (hasRuntimeRun || hasServerAgent) return cleaned", APP_SOURCE)
        self.assertIn("ctx._reuseRuntimeAssistant = Boolean(ctx.runtimeRunId)", APP_SOURCE)
        self.assertIn("Before repeating any write, command, network request", APP_SOURCE)
        self.assertIn('meta: { _system: true, kind: "run-recovery" }', APP_SOURCE)

    def test_recovery_restores_saved_execution_settings(self):
        for expected in (
            "ctx.model = runState.model || ctx.model",
            "ctx.temperature = Number(runState.temperature",
            "ctx.toolPreset = runState.toolPreset",
            "ctx.permissionProfile = runState.permissionProfile",
            "ctx.thinkingLevel = runState.thinkingLevel",
        ):
            self.assertIn(expected, APP_SOURCE)

    def test_init_starts_recovery_after_models_are_loaded(self):
        models_pos = APP_SOURCE.index("await refreshModels();")
        resume_pos = APP_SOURCE.index("resumePersistedRuns().catch", models_pos)
        self.assertGreater(resume_pos, models_pos)

    def test_server_agent_checkpoint_survives_reload(self):
        for expected in (
            'executionOwner: String(',
            'agentRunId: String(',
            'agentEventCursor: Number(',
            'runState: getSessionRunState(sid)',
            'runState: { ...getSessionRunState(prevId) }',
            'persistMessages: ctx.executionOwner === "server-agent"',
            'if (options.persistMessages)',
            'ctx.executionOwner = runState.executionOwner',
            'ctx.agentRunId = String(runState.agentRunId',
            'await executeRunContext(ctx)',
        ):
            self.assertIn(expected, APP_SOURCE)

    def test_read_plan_and_accept_profiles_have_single_server_execution_owner(self):
        self.assertIn('read: new Set(["request_user_input", "list_files", "read_file", "search_files", "glob_files"])', APP_SOURCE)
        self.assertIn('return ["read", "plan", "accept"].includes(permissionProfile) ? "server-agent" : "browser"', APP_SOURCE)
        self.assertIn("executionOwner: executionOwnerForPermissionProfile(permissionProfile)", APP_SOURCE)
        self.assertIn("ctx.executionOwner = runState.executionOwner || executionOwnerForPermissionProfile(ctx.permissionProfile)", APP_SOURCE)
        self.assertIn('if (isServerOwnedRun(ctx)) return runServerAgentLoop(ctx)', APP_SOURCE)
        self.assertIn('await _callModelOnceAttempt(assistantIndex, true, ctx)', APP_SOURCE)
        server_projection = APP_SOURCE[
            APP_SOURCE.index("async function projectAgentModelStarted"):
            APP_SOURCE.index("function projectAgentModelCompleted")
        ]
        self.assertNotIn("callModelOnce(", server_projection)

    def test_server_agent_cancellation_covers_parent_and_child_runs(self):
        cancel_start = APP_SOURCE.index("function cancelSessionRun(run)")
        cancel_end = APP_SOURCE.index("function backgroundActiveForSession", cancel_start)
        cancel = APP_SOURCE[cancel_start:cancel_end]
        self.assertIn("cancelAgentRun(agentRunId)", cancel)
        self.assertIn("cancelRun(runtimeRunId)", cancel)

    def test_durable_model_projection_always_has_completion_time(self):
        projection_start = APP_SOURCE.index("function projectAgentModelCompleted")
        projection_end = APP_SOURCE.index("function projectAgentToolStarted", projection_start)
        projection = APP_SOURCE[projection_start:projection_end]
        self.assertIn("const projectedContent = splitThoughtContent(combined)", projection)
        self.assertIn("data.completedAt || event?.createdAt", projection)
        self.assertIn("_time: completedAt", projection)
        self.assertIn("assistant._time = assistant._time || completedAt", projection)


class TestServerRunStatePersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sessions_dir = Path(self.temp_dir.name)
        self.patch_sessions = mock.patch.object(server_mod, "SESSIONS_DIR", self.sessions_dir)
        self.patch_sessions.start()
        self.addCleanup(self.patch_sessions.stop)

    def make_handler(self, body):
        handler = object.__new__(server_mod.CodeHandler)
        handler.read_body_json = mock.Mock(return_value=body)
        handler.send_json = mock.Mock()
        return handler

    def test_create_summary_and_save_preserve_run_state(self):
        running = {
            "status": "waiting-network",
            "phase": "model",
            "model": "deepseek-v4-pro",
            "recoveryCount": 2,
        }
        create_handler = self.make_handler({"title": "P0", "runState": running})
        server_mod.CodeHandler.create_session(create_handler)
        created = create_handler.send_json.call_args.args[0]

        stored = json.loads(server_mod.session_path(created["id"]).read_text(encoding="utf-8"))
        self.assertEqual(stored["runState"], running)
        self.assertEqual(server_mod.session_summary(stored)["runState"], running)

        save_handler = self.make_handler({
            "title": "P0",
            "messages": [{"role": "user", "content": "continue"}],
            "stats": {"input": 3},
            "runState": {"status": "resuming", "phase": "tools"},
        })
        server_mod.CodeHandler.save_session(save_handler, created["id"])
        saved = save_handler.send_json.call_args.args[0]
        self.assertEqual(saved["runState"]["status"], "resuming")
        self.assertEqual(saved["runState"]["phase"], "tools")

    def test_ordinary_save_does_not_erase_existing_checkpoint(self):
        session_id = "stabletest01"
        server_mod.write_json(server_mod.session_path(session_id), {
            "id": session_id,
            "title": "checkpoint",
            "messages": [],
            "runState": {"status": "running", "phase": "tools"},
        })
        handler = self.make_handler({"title": "checkpoint", "messages": []})
        server_mod.CodeHandler.save_session(handler, session_id)
        saved = handler.send_json.call_args.args[0]
        self.assertEqual(saved["runState"], {"status": "running", "phase": "tools"})

    def test_session_save_persists_last_usage(self):
        initial_usage = {
            "prompt_tokens": 1250,
            "completion_tokens": 80,
            "total_tokens": 1330,
        }
        create_handler = self.make_handler({"title": "usage", "lastUsage": initial_usage})
        server_mod.CodeHandler.create_session(create_handler)
        created = create_handler.send_json.call_args.args[0]
        self.assertEqual(created["lastUsage"], initial_usage)

        updated_usage = {
            "prompt_tokens": 2400,
            "completion_tokens": 120,
            "total_tokens": 2520,
        }
        save_handler = self.make_handler({
            "title": "usage",
            "messages": [{"role": "assistant", "content": "done"}],
            "lastUsage": updated_usage,
        })
        server_mod.CodeHandler.save_session(save_handler, created["id"])

        stored = json.loads(
            server_mod.session_path(created["id"]).read_text(encoding="utf-8")
        )
        self.assertEqual(stored["lastUsage"], updated_usage)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestSubAgentFrontend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "app.js").read_text(encoding="utf-8")

    def test_subagent_system_message_stays_system(self):
        self.assertIn('if (msg.role === "system")', self.source)
        self.assertIn('return { role: "system", content: getMsgText(msg) };', self.source)

    def test_subagent_keeps_private_message_array(self):
        self.assertIn(
            'if (!ctx.isSubAgent) ctx.messages = getSessionMessages(ctx.sessionId);',
            self.source,
        )

    def test_subagent_cannot_delegate_again(self):
        self.assertIn(
            '.filter((tool) => !["task", "request_user_input"].includes(tool.function?.name))',
            self.source,
        )
        self.assertIn('禁止再次委派子 Agent', self.source)

    def test_main_agent_receives_explicit_delegation_rules(self):
        self.assertIn('const SUBAGENT_DELEGATION_RULES = `## 子 Agent 委派规则', self.source)
        self.assertIn('if (allowedToolNames.has("task"))', self.source)
        self.assertIn('parts.push(SUBAGENT_DELEGATION_RULES);', self.source)
        self.assertIn('存在两个及以上互不依赖的工作流', self.source)
        self.assertIn('不要把整个原始任务不加拆分地转交给单个子 Agent', self.source)
        self.assertIn('仅在并行收益明显高于额外成本时委派', self.source)

    def test_task_batches_use_bounded_concurrency(self):
        self.assertIn('async function mapWithConcurrency', self.source)
        self.assertIn('normalizedCalls.every((tool) => tool.action === "task")', self.source)
        self.assertIn('mapWithConcurrency(\n          normalizedCalls,\n          3,', self.source)

    def test_no_tool_text_is_not_accepted_as_success(self):
        self.assertIn('ctx.requiresToolUse && (ctx.toolCallCount || 0) === 0', self.source)
        self.assertIn('不要输出或模拟工具调用 JSON', self.source)

    def test_subagent_tools_use_grouped_authorization(self):
        self.assertIn('async function executeToolCall(tool, options = {})', self.source)
        self.assertIn('requestAuthorization(tool, options.context || null)', self.source)
        self.assertIn('context: parentCtx || null', self.source)
        self.assertIn('label: `${t("subAgentLabel")} · ${ctx.authorizationLabel || t("subTaskLabel")}`', self.source)

    def test_plan_mode_can_delegate_without_mutation_tools(self):
        self.assertIn('plan: new Set(["request_user_input", "list_files", "read_file", "search_files", "glob_files", "web_fetch", "propose_edit", "task", "use_skill", "read_skill_resource"])', self.source)
        self.assertIn('.filter((tool) => !["task", "request_user_input"].includes(tool.function?.name))', self.source)

    def test_subagent_edits_wait_for_accept_mode_authorization(self):
        self.assertIn('profile === "accept" && result.action === "propose_edit"', self.source)
        self.assertNotIn('getPermissionProfile() === "bypass" || ctx.isSubAgent', self.source)
        self.assertIn('Sub-agent edit proposals must be reviewable in the parent conversation.', self.source)

    def test_same_turn_operations_are_authorized_as_a_batch(self):
        self.assertIn('const authorizationDecisions = new Map();', self.source)
        self.assertIn('await Promise.all(gatedCalls.map(({ tool }) => requestAuthorization(tool, ctx)))', self.source)
        self.assertIn('authorizationDecision: authorizationDecisions.has(callIndex)', self.source)

    def test_authorization_panel_groups_main_and_subagents(self):
        self.assertIn('return { key: "main", label: t("mainAgentLabel") };', self.source)
        self.assertIn('function groupAuthorizations(items)', self.source)
        self.assertIn('data-auth-group=', self.source)
        self.assertIn('data-auth-action="approve"', self.source)
        self.assertIn('data-auth-action="reject-all"', self.source)

    def test_subagent_suppresses_successful_duplicate_tools(self):
        self.assertIn('successfulToolSignatures: new Set()', self.source)
        self.assertIn('此前成功的工具调用', self.source)
        self.assertIn('const maxRounds = MAX_TOOL_ROUNDS;', self.source)

    def test_subagent_is_not_stopped_by_a_small_round_limit(self):
        self.assertNotIn('ctx.isSubAgent ? 6 : MAX_TOOL_ROUNDS', self.source)
        self.assertIn('Timeout, cancellation and duplicate-tool', self.source)

    def test_parallel_subagent_usage_uses_private_ledgers(self):
        self.assertIn('if (!ctx?.isSubAgent) setSessionStats(sessionId, stats);', self.source)
        self.assertIn('mergeBackgroundUsage(sessionId, usage);', self.source)
        self.assertNotIn('mergeBackgroundUsage(sessionId, subCtx.stats);', self.source)

    def test_delegated_usage_merges_once_into_parent_task(self):
        self.assertIn('function mergeDelegatedUsage(parentCtx, childUsage)', self.source)
        self.assertEqual(
            self.source.count('mergeDelegatedUsage(parentCtx, subCtx.taskUsage);'),
            2,
        )

    def test_background_result_keeps_its_own_usage(self):
        self.assertIn('_usage: sub.usage', self.source)
        self.assertIn('_usageScope: "task"', self.source)

    def test_background_dispatch_uses_bounded_scheduler(self):
        self.assertIn('globalLimit: 3', self.source)
        self.assertIn('perSessionLimit: 2', self.source)
        self.assertIn('function pumpBackgroundDispatcher()', self.source)
        self.assertIn('backgroundActiveForSession(candidate.sessionId) < dispatcher.perSessionLimit', self.source)

    def test_background_dispatch_has_visible_lifecycle_and_timeout(self):
        self.assertIn('backgroundDispatch: { id, status: "pending" }', self.source)
        self.assertIn('updateBackgroundJob(job, "running")', self.source)
        self.assertIn('const BACKGROUND_JOB_TIMEOUT_MS = 10 * 60 * 1000;', self.source)
        self.assertIn('后台处理中', self.source)

    def test_background_messages_are_detached_from_main_model_context(self):
        self.assertIn('function isDetachedFromMainContext(msg)', self.source)
        self.assertIn('msg.meta?.detachedFromMain', self.source)
        self.assertIn('function getModelContextMessages(messages)', self.source)
        self.assertIn('.filter((msg) => !isDetachedFromMainContext(msg))', self.source)
        self.assertIn('getModelContextMessages(_streamMsgs)', self.source)
        self.assertGreaterEqual(self.source.count('detachedFromMain: true'), 3)

    def test_legacy_background_notifications_stay_out_of_model_context(self):
        self.assertIn(
            'msg.meta?.kind === "background-subagent-notify"',
            self.source,
        )

    def test_subagent_edit_projection_is_detached_from_parent_context(self):
        self.assertGreaterEqual(
            self.source.count('meta.detachedFromMain = true;'),
            2,
        )

    def test_background_dispatch_owns_abort_controller(self):
        self.assertIn('abortController: new AbortController()', self.source)
        self.assertIn('if (!ctx?.isSubAgent && sessionId === state.sessionId)', self.source)

    def test_session_saves_are_serialized(self):
        self.assertIn('_sessionSaveChains: {}', self.source)
        self.assertIn('const previous = state._sessionSaveChains[sessionId] || Promise.resolve();', self.source)
        self.assertIn('state._sessionSaveChains[sessionId] = savePromise;', self.source)

    def test_active_subagent_does_not_block_main_session_updates(self):
        self.assertNotIn('if (!sessionId || state._subAgentDepth > 0) return;', self.source)
        self.assertNotIn('if (active && state._subAgentDepth > 0) return;', self.source)


if __name__ == "__main__":
    unittest.main()

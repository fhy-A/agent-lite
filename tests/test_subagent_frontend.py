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
            '.filter((tool) => tool.function?.name !== "task")',
            self.source,
        )
        self.assertIn('禁止再次委派子 Agent', self.source)

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
        self.assertIn('label: `子 Agent · ${ctx.authorizationLabel || "子任务"}`', self.source)

    def test_plan_mode_can_delegate_without_mutation_tools(self):
        self.assertIn('plan: new Set(["list_files", "read_file", "search_files", "glob_files", "web_fetch", "propose_edit", "task", "use_skill"])', self.source)
        self.assertIn('.filter((tool) => tool.function?.name !== "task")', self.source)

    def test_subagent_edits_wait_for_accept_mode_authorization(self):
        self.assertIn('profile === "accept" && result.action === "propose_edit"', self.source)
        self.assertNotIn('getPermissionProfile() === "bypass" || ctx.isSubAgent', self.source)
        self.assertIn('Sub-agent edit proposals must be reviewable in the parent conversation.', self.source)

    def test_same_turn_operations_are_authorized_as_a_batch(self):
        self.assertIn('const authorizationDecisions = new Map();', self.source)
        self.assertIn('await Promise.all(gatedCalls.map(({ tool }) => requestAuthorization(tool, ctx)))', self.source)
        self.assertIn('authorizationDecision: authorizationDecisions.has(callIndex)', self.source)

    def test_authorization_panel_groups_main_and_subagents(self):
        self.assertIn('return { key: "main", label: "主 Agent" };', self.source)
        self.assertIn('function groupAuthorizations(items)', self.source)
        self.assertIn('data-auth-group=', self.source)
        self.assertIn('data-auth-action="approve"', self.source)
        self.assertIn('data-auth-action="reject-all"', self.source)

    def test_subagent_suppresses_successful_duplicate_tools(self):
        self.assertIn('successfulToolSignatures: new Set()', self.source)
        self.assertIn('此前成功的工具调用', self.source)
        self.assertIn('const maxRounds = ctx.isSubAgent ? 6 : MAX_TOOL_ROUNDS;', self.source)


if __name__ == "__main__":
    unittest.main()

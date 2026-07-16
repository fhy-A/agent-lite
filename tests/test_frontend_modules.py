"""Regression guards for the transitional frontend module split."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_SOURCE = (ROOT / "app.js").read_text(encoding="utf-8")
INDEX_SOURCE = (ROOT / "index.html").read_text(encoding="utf-8")
BUILD_SOURCE = (ROOT / "build_exe.py").read_text(encoding="utf-8")
STYLE_SOURCE = (ROOT / "styles.css").read_text(encoding="utf-8")


class TestFrontendCoreModules(unittest.TestCase):
    def test_core_module_files_exist(self):
        for relative_path in (
            "src/core/namespace.js",
            "src/core/icons.js",
            "src/core/utils.js",
            "src/services/notifications.js",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_scripts_load_before_runtime_and_app(self):
        scripts = (
            "./src/core/namespace.js",
            "./src/core/icons.js",
            "./src/core/utils.js",
            "./src/services/notifications.js",
            "./agent-runtime.js",
            "./app.js",
        )
        positions = [INDEX_SOURCE.index(f'src="{script}"') for script in scripts]
        self.assertEqual(positions, sorted(positions))

    def test_namespace_defines_supported_buckets(self):
        source = (ROOT / "src/core/namespace.js").read_text(encoding="utf-8")
        for bucket in ("core", "services", "features", "agent", "ui"):
            self.assertIn(f'Code.{bucket} = Code.{bucket} || {{}}', source)

    def test_modules_export_through_code_core(self):
        icons = (ROOT / "src/core/icons.js").read_text(encoding="utf-8")
        utils = (ROOT / "src/core/utils.js").read_text(encoding="utf-8")
        self.assertIn("core.icons = Object.freeze", icons)
        self.assertIn("core.utils = Object.freeze", utils)
        for name in (
            "escapeHtml",
            "formatCompact",
            "formatNumber",
            "formatElapsed",
            "estimateTokens",
        ):
            self.assertIn(name, utils)

    def test_notifications_export_through_code_services(self):
        source = (ROOT / "src/services/notifications.js").read_text(encoding="utf-8")
        self.assertIn("services.notifications = Object.freeze", source)
        self.assertIn("showToast", source)
        self.assertIn("notify", source)

    def test_app_uses_extracted_modules_without_duplicate_definitions(self):
        self.assertIn("const { uiIcon } = window.Code.core.icons", APP_SOURCE)
        self.assertIn("} = window.Code.core.utils", APP_SOURCE)
        self.assertIn(
            "const { showToast, notify: _notify } = window.Code.services.notifications",
            APP_SOURCE,
        )
        for legacy_definition in (
            "const UI_ICON_PATHS",
            "function uiIcon(",
            "function escapeHtml(",
            "function formatCompact(",
            "function formatNumber(",
            "function formatElapsed(",
            "function estimateTokens(",
            "function showToast(",
            "function _notify(",
        ):
            self.assertNotIn(legacy_definition, APP_SOURCE)

        # Preserve the current duplicate formatSize behavior until its own cleanup.
        self.assertEqual(APP_SOURCE.count("function formatSize("), 2)

    def test_packaged_exe_includes_runtime_and_module_tree(self):
        self.assertIn("APP_DIR / 'agent-runtime.js'", BUILD_SOURCE)
        self.assertIn("APP_DIR / 'src'", BUILD_SOURCE)
        self.assertIn("f\"{APP_DIR / 'src'}{';'}src\"", BUILD_SOURCE)

    def test_thought_projection_only_collects_tool_round_summaries(self):
        render_start = APP_SOURCE.index("function renderMessages()")
        assistant_start = APP_SOURCE.index('if (msg.role === "assistant") {', render_start)
        assistant_end = APP_SOURCE.index('if (msg.role === "user") {', assistant_start)
        assistant_block = APP_SOURCE[assistant_start:assistant_end]

        self.assertIn("if (msg.meta?.toolCalls?.length) {", assistant_block)
        self.assertIn("pendingThoughts.push", assistant_block)
        self.assertLess(
            assistant_block.index("if (msg.meta?.toolCalls?.length) {"),
            assistant_block.index("pendingThoughts.push"),
        )
        self.assertIn("thinking-summary-list", APP_SOURCE)
        self.assertIn(".thinking-summary-item + .thinking-summary-item", STYLE_SOURCE)

    def test_streaming_projection_preserves_status_node_and_hides_raw_reasoning(self):
        projection_start = APP_SOURCE.index("function renderFinalAssistantProjection")
        projection_end = APP_SOURCE.index("function createCompactSummaryMessage", projection_start)
        projection = APP_SOURCE[projection_start:projection_end]

        self.assertIn('data-stream-session="${escapeHtml(state.sessionId || "")}"', projection)
        self.assertNotIn('data-stream-part="thought"', projection)
        self.assertNotIn("msg.thought", projection)
        self.assertIn("preservedNodes", APP_SOURCE)
        self.assertIn("freshNode.replaceWith(preservedNode)", APP_SOURCE)


if __name__ == "__main__":
    unittest.main()

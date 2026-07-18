"""Regression guards for the transitional frontend module split."""

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_SOURCE = (ROOT / "app.js").read_text(encoding="utf-8")
RUNTIME_SOURCE = (ROOT / "agent-runtime.js").read_text(encoding="utf-8")
I18N_SOURCE = (ROOT / "src" / "core" / "i18n.js").read_text(encoding="utf-8")
API_CLIENT_SOURCE = (ROOT / "src" / "services" / "api-client.js").read_text(encoding="utf-8")
PREVIEW_SOURCE = (ROOT / "src" / "features" / "preview.js").read_text(encoding="utf-8")
FILES_SOURCE = (ROOT / "src" / "features" / "files.js").read_text(encoding="utf-8")
SKILLS_MEMORY_SOURCE = (ROOT / "src" / "features" / "skills-memory.js").read_text(encoding="utf-8")
INDEX_SOURCE = (ROOT / "index.html").read_text(encoding="utf-8")
BUILD_SOURCE = (ROOT / "build_exe.py").read_text(encoding="utf-8")
STYLE_SOURCE = (ROOT / "styles.css").read_text(encoding="utf-8")
LOGO_SOURCE = (ROOT / "assets" / "code-logo.svg").read_text(encoding="utf-8")
LOGO_EXPORT_SOURCE = (ROOT / "design" / "logo-concepts" / "export_selected_logo.py").read_text(encoding="utf-8")


class TestFrontendCoreModules(unittest.TestCase):
    def test_agent_runtime_client_exposes_durable_run_protocol(self):
        for expected in (
            "createAgentRun",
            "getAgentRun",
            "resumeAgentRun",
            "submitAgentInput",
            "submitAgentAuthorization",
            "watchAgentRun",
            "cancelAgentRun",
            '"waiting_authorization",',
            "await onEvent?.(event, snapshot)",
        ):
            self.assertIn(expected, RUNTIME_SOURCE)
        self.assertIn('clientRequestId = ""', RUNTIME_SOURCE)
        self.assertIn("clientRequestId,", RUNTIME_SOURCE)

    def test_agent_runtime_watcher_projects_events_sequentially_and_resumes_cursor(self):
        script = f"""
global.window = {{}};
const source = {json.dumps(RUNTIME_SOURCE)};
const urls = [];
const snapshots = [
  {{status: "running", events: [{{seq: 1, type: "created"}}, {{seq: 2, type: "model_started"}}]}},
  {{status: "completed", events: [{{seq: 3, type: "completed"}}], result: {{content: "ok"}}}},
];
global.fetch = async (url) => {{
  urls.push(String(url));
  return new Response(JSON.stringify(snapshots.shift()), {{
    status: 200,
    headers: {{"Content-Type": "application/json"}},
  }});
}};
eval(source);
const order = [];
(async () => {{
  const result = await window.AgentRuntime.watchAgentRun({{
    agentRunId: "agent-1",
    onEvent: async (event) => {{
      order.push(`start-${{event.seq}}`);
      await new Promise((resolve) => setTimeout(resolve, 1));
      order.push(`end-${{event.seq}}`);
    }},
  }});
  process.stdout.write(JSON.stringify({{urls, order, cursor: result.nextCursor, status: result.status}}));
}})().catch((error) => {{ console.error(error); process.exit(1); }});
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertIn("cursor=0", data["urls"][0])
        self.assertIn("cursor=2", data["urls"][1])
        self.assertEqual(
            data["order"],
            ["start-1", "end-1", "start-2", "end-2", "start-3", "end-3"],
        )
        self.assertEqual(data["cursor"], 3)
        self.assertEqual(data["status"], "completed")

    def test_agent_runtime_sends_background_idempotency_key(self):
        script = f"""
global.window = {{}};
const source = {json.dumps(RUNTIME_SOURCE)};
let captured = null;
global.fetch = async (url, options) => {{
  captured = {{url: String(url), body: JSON.parse(options.body)}};
  return new Response(JSON.stringify({{agentRunId: "agent-1", status: "model"}}), {{
    status: 201,
    headers: {{"Content-Type": "application/json"}},
  }});
}};
eval(source);
(async () => {{
  await window.AgentRuntime.createAgentRun({{
    sessionId: "session-1",
    clientRequestId: "background-123",
    payload: {{model: "test-model", messages: [{{role: "user", content: "hi"}}]}},
    keys: [],
  }});
  process.stdout.write(JSON.stringify(captured));
}})().catch((error) => {{ console.error(error); process.exit(1); }});
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertEqual(data["url"], "/api/agent/runs")
        self.assertEqual(data["body"]["clientRequestId"], "background-123")

    def test_server_agent_questionnaire_uses_durable_submit_and_reload_path(self):
        self.assertIn('name: "request_user_input"', APP_SOURCE)
        self.assertIn("const serverTools = getNativeTools(ctx.toolPreset, profileAllowedToolNames)", APP_SOURCE)
        self.assertIn('if (snapshot.status === "waiting_user_input")', APP_SOURCE)
        self.assertIn("await requestServerAgentInput(ctx, snapshot.pendingInput)", APP_SOURCE)
        self.assertIn("window.AgentRuntime.submitAgentInput(request.agentRunId", APP_SOURCE)
        self.assertIn('status: nextStatus', APP_SOURCE)
        self.assertIn('const nextStatus = resolver ? "running" : "resuming"', APP_SOURCE)
        self.assertIn('agentRunId: String(tool._agentRunId || "")', APP_SOURCE)
        self.assertIn("userInputRequest: serializeUserInputRequest(request)", APP_SOURCE)

    def test_server_agent_authorization_uses_durable_card_and_reload_path(self):
        for expected in (
            "requestServerAgentAuthorization(ctx, snapshot.pendingAuthorization)",
            "window.AgentRuntime.submitAgentAuthorization(item.agentRunId",
            'status: "waiting-authorization"',
            "authorizationRequest: serializeAuthorizationRequest(request)",
            "restoreAuthorizationRequest(session.id, session.runState?.authorizationRequest)",
            "ensureServerAuthorizationProjection(ctx, pendingAuthorization)",
            "Boolean(meta.serverManaged && !serverExecuting && !applied && !rejected)",
            "resumePersistedSessionRun(summary).catch",
        ):
            self.assertIn(expected, APP_SOURCE)
        self.assertIn("executionOwner: executionOwnerForPermissionProfile(permissionProfile)", APP_SOURCE)
        self.assertIn('return ["read", "plan", "accept", "bypass"].includes(permissionProfile) ? "server-agent" : "browser"', APP_SOURCE)
        self.assertIn("action: authorizationAction", APP_SOURCE)
        self.assertIn("pendingAuthorization.path || pendingAuthorization.command", APP_SOURCE)

    def test_server_agent_uses_profile_tools_and_projects_all_authorized_actions(self):
        for expected in (
            "const profileAllowedToolNames = getAllowedToolNamesForProfile(",
            "allowedTools: serverToolNames",
            'toolPreset === "full" && ["accept", "bypass"].includes(permissionProfile)',
            '["propose_edit", "apply_edit", "write_file", "delete_file"]',
            'const authorizationAction = String(pendingAuthorization.action || "propose_edit")',
            'command: String(pendingAuthorization.command || "")',
            "projectServerEditToolCompleted(ctx, event, callMessage, result)",
            "const decisionResult = result?.childResult || result || {}",
            'const delegatedEditCompletion = toolAction === "task" && Boolean(projection)',
        ):
            self.assertIn(expected, APP_SOURCE)
        self.assertNotIn("SERVER_AGENT_SAFE_TOOLS", APP_SOURCE)

    def test_agent_runtime_submits_authorization_id_and_decision(self):
        script = f"""
global.window = {{}};
const source = {json.dumps(RUNTIME_SOURCE)};
let captured = null;
global.fetch = async (url, options) => {{
  captured = {{url: String(url), method: options.method, body: JSON.parse(options.body)}};
  return new Response(JSON.stringify({{status: "waiting_credentials", result: {{applied: true}}}}), {{
    status: 200,
    headers: {{"Content-Type": "application/json"}},
  }});
}};
eval(source);
(async () => {{
  const result = await window.AgentRuntime.submitAgentAuthorization("agent/a", {{
    authorizationId: "authorization-1",
    decision: "approved",
  }});
  process.stdout.write(JSON.stringify({{captured, result}}));
}})().catch((error) => {{ console.error(error); process.exit(1); }});
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertEqual(data["captured"]["url"], "/api/agent/runs/agent%2Fa/authorization")
        self.assertEqual(data["captured"]["method"], "POST")
        self.assertEqual(data["captured"]["body"], {
            "authorizationId": "authorization-1",
            "decision": "approved",
        })
        self.assertTrue(data["result"]["result"]["applied"])

    def test_read_only_permission_is_user_visible(self):
        self.assertIn('data-value="read"', INDEX_SOURCE)
        self.assertIn('data-i18n="permRead"', INDEX_SOURCE)
        self.assertIn('permRead: "只读分析"', I18N_SOURCE)
        self.assertIn('permRead: "Read only"', I18N_SOURCE)

    def test_partial_think_blocks_never_leak_into_visible_content(self):
        parser_start = APP_SOURCE.index("function splitThoughtContent")
        parser_end = APP_SOURCE.index("// ── Syntax highlighting", parser_start)
        parser_source = APP_SOURCE[parser_start:parser_end]
        cases = (
            "<thi",
            "visible<t",
            "prefix <think>hidden reasoning",
            "<think>hidden</think>answer",
            "<THINK>hidden</THINK>done",
            "plain answer",
        )
        script = (
            parser_source
            + f"\nconst cases = {json.dumps(cases)};"
            + "\nprocess.stdout.write(JSON.stringify(cases.map(splitThoughtContent)));"
        )
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(
            json.loads(completed.stdout),
            [
                {"thought": "", "content": ""},
                {"thought": "", "content": "visible"},
                {"thought": "hidden reasoning", "content": "prefix"},
                {"thought": "hidden", "content": "answer"},
                {"thought": "hidden", "content": "done"},
                {"thought": "", "content": "plain answer"},
            ],
        )

    def test_core_module_files_exist(self):
        for relative_path in (
            "src/core/namespace.js",
            "src/core/icons.js",
            "src/core/utils.js",
            "src/core/i18n.js",
            "src/services/notifications.js",
            "src/services/api-client.js",
            "src/features/preview.js",
            "src/features/files.js",
            "src/features/skills-memory.js",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_scripts_load_before_runtime_and_app(self):
        scripts = (
            "./src/core/namespace.js",
            "./src/core/icons.js",
            "./src/core/utils.js",
            "./src/core/i18n.js",
            "./src/services/notifications.js",
            "./src/services/api-client.js",
            "./src/features/skills-memory.js",
            "./src/features/preview.js",
            "./src/features/files.js",
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
        i18n = (ROOT / "src/core/i18n.js").read_text(encoding="utf-8")
        self.assertIn("core.icons = Object.freeze", icons)
        self.assertIn("core.utils = Object.freeze", utils)
        self.assertIn("core.i18n = Object.freeze", i18n)
        for name in (
            "escapeHtml",
            "formatCompact",
            "formatNumber",
            "formatElapsed",
            "estimateTokens",
        ):
            self.assertIn(name, utils)

    def test_i18n_runtime_translates_interpolates_switches_and_keeps_keys_in_sync(self):
        script = """
global.window = {Code: {core: {}}};
require("./src/core/i18n.js");
let language = "zh";
const persisted = [];
const changed = [];
const runtime = window.Code.core.i18n.createI18nRuntime({
  getLanguage: () => language,
  setLanguage: (nextLanguage) => { language = nextLanguage; },
  persistLanguage: (nextLanguage) => persisted.push(nextLanguage),
  onLanguageChanged: (nextLanguage) => changed.push(nextLanguage),
});
const zh = runtime.t("editingMemory", {name: "demo"});
runtime.setLang("en");
const en = runtime.t("editingMemory", {name: "demo"});
const {LANG, I18N} = window.Code.core.i18n;
const missingKeys = {
  i18nEn: Object.keys(I18N.zh).filter((key) => !(key in I18N.en)),
  i18nZh: Object.keys(I18N.en).filter((key) => !(key in I18N.zh)),
  langEn: Object.keys(LANG.zh).filter((key) => !(key in LANG.en)),
  langZh: Object.keys(LANG.en).filter((key) => !(key in LANG.zh)),
};
process.stdout.write(JSON.stringify({zh, en, persisted, changed, missingKeys}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "zh": "编辑中：demo",
                "en": "Editing: demo",
                "persisted": ["en"],
                "changed": ["en"],
                "missingKeys": {
                    "i18nEn": [],
                    "i18nZh": [],
                    "langEn": [],
                    "langZh": [],
                },
            },
        )

    def test_notifications_export_through_code_services(self):
        source = (ROOT / "src/services/notifications.js").read_text(encoding="utf-8")
        self.assertIn("services.notifications = Object.freeze", source)
        self.assertIn("showToast", source)
        self.assertIn("notify", source)

    def test_api_client_exports_and_preserves_json_request_behavior(self):
        self.assertIn("services.apiClient = Object.freeze", API_CLIENT_SOURCE)
        script = """
global.window = {Code: {services: {}}};
const calls = [];
const responses = [
  {ok: true, status: 200, statusText: "OK", json: async () => ({value: 42})},
  {ok: false, status: 400, statusText: "Bad Request", json: async () => ({error: "broken"})},
  {ok: false, status: 502, statusText: "Bad Gateway", json: async () => { throw new Error("invalid json"); }},
  {ok: true, status: 204, statusText: "No Content", json: async () => { throw new Error("empty"); }},
];
window.fetch = async (url, options) => {
  calls.push({url, options});
  return responses.shift();
};
require("./src/services/api-client.js");
const {apiJson} = window.Code.services.apiClient;
(async () => {
  const success = await apiJson("/success", {
    method: "POST",
    headers: {"X-Trace": "trace-1"},
    body: JSON.stringify({hello: "world"}),
  });
  let serverError = "";
  let invalidError = "";
  try { await apiJson("/server-error"); } catch (error) { serverError = error.message; }
  try { await apiJson("/invalid-error"); } catch (error) { invalidError = error.message; }
  const emptySuccess = await apiJson("/empty-success");
  process.stdout.write(JSON.stringify({success, serverError, invalidError, emptySuccess, calls}));
})().catch((error) => { console.error(error); process.exit(1); });
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertEqual(data["success"], {"value": 42})
        self.assertEqual(data["serverError"], "broken")
        self.assertEqual(data["invalidError"], "HTTP 502: Bad Gateway")
        self.assertEqual(data["emptySuccess"], {})
        self.assertEqual(data["calls"][0]["url"], "/success")
        self.assertEqual(data["calls"][0]["options"]["method"], "POST")
        self.assertEqual(
            data["calls"][0]["options"]["headers"],
            {"Content-Type": "application/json", "X-Trace": "trace-1"},
        )

    def test_files_feature_exports_sorting_paths_and_attachment_flow(self):
        self.assertIn("features.files = Object.freeze", FILES_SOURCE)
        script = """
global.window = {
  Code: {features: {}},
  btoa: (binary) => Buffer.from(binary, "binary").toString("base64"),
};
require("./src/features/files.js");
const {shortPath, sortFileItems, createFilesFeature} = window.Code.features.files;
const items = [
  {name: "z-dir", path: "z-dir", type: "dir", updatedAt: "2026-01-01"},
  {name: "b.ts", path: "b.ts", type: "file", updatedAt: "2026-01-03"},
  {name: "a.js", path: "a.js", type: "file", updatedAt: "2026-01-02"},
  {name: "a-dir", path: "a-dir", type: "dir", updatedAt: "2026-01-04"},
];
const calls = [];
const inserted = [];
const elements = {
  filePicker: {value: "old", clicked: false, click() { this.clicked = true; }},
  attachFile: {disabled: false},
};
const feature = createFilesFeature({
  state: {},
  elements,
  t: (key) => key,
  escapeHtml: (value) => String(value),
  apiJson: async (url, options) => {
    calls.push({url, options});
    return {path: "attachments/demo.txt"};
  },
  insertPromptText: (value) => inserted.push(value),
});
(async () => {
  feature.pickProjectFile();
  await feature.resolvePickedFile({
    name: "demo.txt",
    arrayBuffer: async () => Uint8Array.from([104, 105]).buffer,
  });
  process.stdout.write(JSON.stringify({
    short: shortPath("C:/Users/Admin/project"),
    defaultOrder: sortFileItems(items).map((item) => item.path),
    typeOrder: sortFileItems(items, "type", true).map((item) => item.path),
    timeOrder: sortFileItems(items, "time", true).map((item) => item.path),
    pickerCleared: elements.filePicker.value,
    pickerClicked: elements.filePicker.clicked,
    attachDisabled: elements.attachFile.disabled,
    inserted,
    calls,
  }));
})().catch((error) => { console.error(error); process.exit(1); });
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertEqual(data["short"], "~\\Admin\\project")
        self.assertEqual(data["defaultOrder"], ["a-dir", "z-dir", "a.js", "b.ts"])
        self.assertEqual(data["typeOrder"], ["a-dir", "z-dir", "a.js", "b.ts"])
        self.assertEqual(data["timeOrder"], ["a-dir", "b.ts", "a.js", "z-dir"])
        self.assertEqual(data["pickerCleared"], "")
        self.assertTrue(data["pickerClicked"])
        self.assertFalse(data["attachDisabled"])
        self.assertEqual(data["inserted"], ["attachments/demo.txt"])
        self.assertEqual(data["calls"][0]["url"], "/api/attachments")
        self.assertEqual(data["calls"][0]["options"]["method"], "POST")
        self.assertEqual(
            json.loads(data["calls"][0]["options"]["body"]),
            {"name": "demo.txt", "contentBase64": "aGk="},
        )

    def test_skills_memory_feature_ranks_and_loads_context_without_app_globals(self):
        self.assertIn("features.skillsMemory = Object.freeze", SKILLS_MEMORY_SOURCE)
        script = """
global.window = {Code: {features: {}}};
require("./src/features/skills-memory.js");
const {createSkillsMemoryFeature, rankMatchedSkills} = window.Code.features.skillsMemory;
const skills = [
  {name: "python-tests", description: "Python testing", keywords: ["python+pytest"]},
  {name: "review", description: "Review changes", keywords: []},
  {name: "general", description: "python help", keywords: []},
  {name: "writing-plans", description: "python pytest plan", keywords: ["python+pytest"]},
  {name: "disabled", description: "python pytest", keywords: ["python+pytest"]},
];
const ranked = rankMatchedSkills(skills, new Set(["disabled"]), "Review this Python pytest project");
const calls = [];
const state = {skills: [], disabledSkills: new Set()};
const feature = createSkillsMemoryFeature({
  state,
  elements: {},
  apiJson: async (url) => {
    calls.push(url);
    if (url === "/api/skills?brief=1") return {data: [{name: "demo", body: null}]};
    if (url === "/api/skills/demo") return {body: "Demo instructions", path: "skills/demo", resources: {}};
    if (url === "/api/memory-context") return {found: true, count: 2, content: "memory"};
    throw new Error(`unexpected request: ${url}`);
  },
  document: {getElementById: () => null},
  storage: {setItem: () => {}},
});
(async () => {
  const loadedSkills = await feature.loadSkills();
  const loadedSkill = await feature.ensureSkillBody(loadedSkills[0]);
  const memory = await feature.loadMemoryContext();
  process.stdout.write(JSON.stringify({
    ranked: ranked.map((skill) => skill.name),
    loadedSkill,
    memory,
    calls,
  }));
})().catch((error) => { console.error(error); process.exit(1); });
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertEqual(data["ranked"], ["python-tests"])
        self.assertEqual(data["loadedSkill"]["body"], "Demo instructions")
        self.assertEqual(data["memory"], {"found": True, "count": 2, "content": "memory"})
        self.assertEqual(
            data["calls"],
            ["/api/skills?brief=1", "/api/skills/demo", "/api/memory-context"],
        )

    def test_preview_feature_exports_parsing_urls_and_width_rules(self):
        self.assertIn("features.preview = Object.freeze", PREVIEW_SOURCE)
        script = """
global.window = {Code: {features: {}}, innerWidth: 1000};
require("./src/features/preview.js");
const {createPreviewFeature, parseDelimitedText, previewRawUrl} = window.Code.features.preview;
const styles = [];
const storage = [];
const feature = createPreviewFeature({
  state: {previewWidth: 420},
  elements: {},
  apiJson: async () => ({}),
  renderMarkdown: (value) => value,
  document: {documentElement: {style: {setProperty: (...args) => styles.push(args)}}},
  storage: {setItem: (...args) => storage.push(args)},
});
const parsed = parseDelimitedText('name,note\\nAlice,"hello, world"\\nBob,"two\\nlines"\\n');
const limited = parseDelimitedText("a\\nb\\nc\\n", ",", 2);
const wide = feature.applyPreviewWidth(600, false);
const narrow = feature.applyPreviewWidth(100, true);
process.stdout.write(JSON.stringify({
  parsed,
  limited,
  wide,
  narrow,
  styles,
  storage,
  raw: previewRawUrl("folder/a b.pdf", "version 1"),
}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(completed.stdout)
        self.assertEqual(
            data["parsed"]["rows"],
            [["name", "note"], ["Alice", "hello, world"], ["Bob", "two\nlines"]],
        )
        self.assertFalse(data["parsed"]["limited"])
        self.assertEqual(data["limited"]["rows"], [["a"], ["b"]])
        self.assertTrue(data["limited"]["limited"])
        self.assertEqual(data["wide"], 480)
        self.assertEqual(data["narrow"], 250)
        self.assertEqual(data["styles"][-1], ["--preview-width", "250px"])
        self.assertEqual(data["storage"], [["code-preview-width", "250"]])
        self.assertEqual(
            data["raw"],
            "/api/file?path=folder%2Fa%20b.pdf&raw=1&v=version%201",
        )

    def test_app_uses_extracted_modules_without_duplicate_definitions(self):
        self.assertIn("const { uiIcon } = window.Code.core.icons", APP_SOURCE)
        self.assertIn("} = window.Code.core.utils", APP_SOURCE)
        self.assertIn("const { createI18nRuntime } = window.Code.core.i18n", APP_SOURCE)
        self.assertIn("const { t, setLang, applyI18n } = createI18nRuntime", APP_SOURCE)
        self.assertIn("const { apiJson } = window.Code.services.apiClient", APP_SOURCE)
        self.assertIn("const { createPreviewFeature } = window.Code.features.preview", APP_SOURCE)
        self.assertIn("const previewFeature = createPreviewFeature", APP_SOURCE)
        self.assertIn("const { createFilesFeature, shortPath } = window.Code.features.files", APP_SOURCE)
        self.assertIn("const filesFeature = createFilesFeature", APP_SOURCE)
        self.assertIn("const { createSkillsMemoryFeature } = window.Code.features.skillsMemory", APP_SOURCE)
        self.assertIn("const skillsMemoryFeature = createSkillsMemoryFeature", APP_SOURCE)
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
            "const LANG =",
            "const I18N =",
            "function t(key",
            "function setLang(",
            "function applyI18n(",
            "async function apiJson(",
            "function applyPreviewWidth(",
            "function renderPreviewNotice(",
            "function renderCodePreview(",
            "function renderPreviewModeActions(",
            "function sanitizePreviewHtml(",
            "function renderMarkdownPreview(",
            "function parseDelimitedText(",
            "function renderDelimitedTablePage(",
            "function renderDelimitedPreview(",
            "function currentImageFitScale(",
            "function applyImagePreviewScale(",
            "function renderImagePreviewActions(",
            "function renderImagePreview(",
            "function renderPdfPreview(",
            "function markActiveFile(",
            "function formatPreviewMeta(",
            "async function loadFile(",
            "function startPreviewAutoRefresh(",
            "function shortPath(",
            "function arrayBufferToBase64(",
            "async function uploadAttachment(",
            "async function pickProjectFile(",
            "async function resolvePickedFile(",
            "function showFileContextMenu(",
            "function renderFileTree(",
            "async function loadFiles(",
            "function goUpDir(",
            "function toggleCwdDropdown(",
            "function renderRecentFolders(",
            "function addRecentFolder(",
            "async function loadSkills(",
            "async function ensureSkillBody(",
            "async function getMatchedSkillPrompts(",
            "function showSkillsPanel(",
            "function renderSkillsList(",
            "async function showSkillDetail(",
            "function openSkillEditor(",
            "function closeSkillEditor(",
            "async function saveSkillEdit(",
            "function toggleSkill(",
            "async function deleteSkillConfirm(",
            "function showSlashSuggestions(",
            "async function loadMemoryContext(",
            "function updateMemoryContextIndicator(",
            "async function showMemoryPanel(",
            "function hideMemoryPanel(",
            "async function renderMemoryList(",
            "async function editMemory(",
            "async function deleteMemory(",
            "async function saveMemorySubmit(",
            "function renderMemoryPanel(",
            "function clearMemoryForm(",
            "async function refreshSettingsMemoryList(",
            "function renderSkillsInSettings(",
            "function renderSettingsSkillsSidebar(",
            "async function showSkillDetailInSettings(",
            "function showToast(",
            "function _notify(",
        ):
            self.assertNotIn(legacy_definition, APP_SOURCE)

        # Preserve the current duplicate formatSize behavior until its own cleanup.
        self.assertEqual(APP_SOURCE.count("function formatSize("), 2)
        self.assertNotIn('onclick="cwdPickFolderAction()"', INDEX_SOURCE)
        self.assertNotIn('onclick="cwdUseHomeFolder()"', INDEX_SOURCE)

    def test_packaged_exe_includes_runtime_and_module_tree(self):
        self.assertIn("APP_DIR / 'agent-runtime.js'", BUILD_SOURCE)
        self.assertIn("APP_DIR / 'src'", BUILD_SOURCE)
        self.assertIn("f\"{APP_DIR / 'src'}{';'}src\"", BUILD_SOURCE)
        self.assertIn("APP_DIR / 'code-icon.png'", BUILD_SOURCE)
        self.assertIn("APP_DIR / 'assets'", BUILD_SOURCE)

    def test_code_brand_mark_and_minimal_welcome_stay_in_sync(self):
        upper_path = "M80 13A40 40 0 0 1 80 93"
        lower_path = "M80 147A40 40 0 0 1 80 67"
        for source in (INDEX_SOURCE, APP_SOURCE, LOGO_SOURCE):
            self.assertIn(upper_path, source)
            self.assertIn(lower_path, source)
            self.assertIn('stroke="currentColor"', source)
            self.assertNotIn("#2563EB", source)
            self.assertNotIn("#BFDBFE", source)
        self.assertIn(".logo-svg {", STYLE_SOURCE)
        self.assertIn("--brand-mark: #000000;", STYLE_SOURCE)
        self.assertIn("--brand-mark: #ffffff;", STYLE_SOURCE)
        self.assertIn("color: var(--brand-mark);", STYLE_SOURCE)
        self.assertIn("draw.rounded_rectangle", LOGO_EXPORT_SOURCE)
        self.assertIn(
            'draw_mark(draw, "#FFFFFF", SCALE, optical_small_size=True)',
            LOGO_EXPORT_SOURCE,
        )
        self.assertIn('render_transparent_mark("#000000")', LOGO_EXPORT_SOURCE)
        self.assertIn('render_transparent_mark("#FFFFFF")', LOGO_EXPORT_SOURCE)
        self.assertTrue((ROOT / "code-icon.ico").is_file())
        self.assertTrue((ROOT / "code-icon.png").is_file())
        self.assertTrue((ROOT / "assets" / "code-icon.png").is_file())
        self.assertTrue((ROOT / "assets" / "code-logo-black.svg").is_file())
        self.assertTrue((ROOT / "assets" / "code-logo-white.svg").is_file())
        self.assertTrue((ROOT / "assets" / "code-logo-black.png").is_file())
        self.assertTrue((ROOT / "assets" / "code-logo-white.png").is_file())
        self.assertTrue((ROOT / "assets" / "code-wordmark.svg").is_file())
        self.assertIn("function renderCodeWordmark", APP_SOURCE)
        self.assertIn('viewBox="0 0 130 54"', APP_SOURCE)

        welcome_start = APP_SOURCE.index('<div class="welcome-screen">')
        welcome_end = APP_SOURCE.index("const timeline", welcome_start)
        welcome = APP_SOURCE[welcome_start:welcome_end]
        self.assertIn('class="welcome-wordmark welcome-brand-lockup"', welcome)
        self.assertIn('class="welcome-command-line"', welcome)
        self.assertIn('class="welcome-product"', welcome)
        self.assertIn('renderCodeWordmark("welcome-typed-brand")', welcome)
        self.assertIn('class="welcome-travel-caret"', welcome)
        self.assertNotIn('<div class="welcome-product">Code</div>', welcome)
        self.assertNotIn('class="welcome-mark-stage"', welcome)
        self.assertIn('t("welcomeHeadline")', welcome)
        self.assertNotIn('class="welcome-actions"', welcome)
        self.assertNotIn("data-welcome-prompt=", welcome)
        self.assertNotIn("function bindWelcomeActions()", APP_SOURCE)
        self.assertNotIn(".welcome-actions {", STYLE_SOURCE)
        self.assertIn("function playWelcomeMotion(root)", APP_SOURCE)
        self.assertIn('window.matchMedia("(prefers-reduced-motion: reduce)")', APP_SOURCE)
        self.assertIn("const promptRect = els.prompt.getBoundingClientRect();", APP_SOURCE)
        self.assertIn("background: var(--text);", STYLE_SOURCE)
        self.assertIn("@keyframes welcomeCaretType", STYLE_SOURCE)
        self.assertIn("width: min(680px, calc(100% - 48px));", STYLE_SOURCE)

    def test_thought_projection_only_collects_tool_round_summaries(self):
        render_start = APP_SOURCE.index("function renderMessages()")
        assistant_start = APP_SOURCE.index('if (msg.role === "assistant") {', render_start)
        assistant_end = APP_SOURCE.index('if (msg.role === "user") {', assistant_start)
        assistant_block = APP_SOURCE[assistant_start:assistant_end]

        self.assertIn(
            'const streamingToolRound = msg.streaming && msg._streamProjection === "thinking"',
            assistant_block,
        )
        self.assertIn(
            "if (msg.meta?.toolCalls?.length || streamingToolRound) {",
            assistant_block,
        )
        self.assertIn("pendingThoughts.push", assistant_block)
        self.assertLess(
            assistant_block.index("if (msg.meta?.toolCalls?.length || streamingToolRound) {"),
            assistant_block.index("pendingThoughts.push"),
        )
        projection_start = APP_SOURCE.index("function renderThinkingProjection")
        projection_end = APP_SOURCE.index("function isEditSuggestionMessage", projection_start)
        projection = APP_SOURCE[projection_start:projection_end]
        self.assertIn('data-stream-kind="thinking"', projection)
        self.assertIn('data-stream-part="summary"', projection)
        self.assertNotIn('t("thoughtProcess")', projection)
        self.assertNotIn(".thinking-process .role", STYLE_SOURCE)
        self.assertIn("const hasVisibleSummary = summaries.some", projection)
        self.assertIn('if (!hasVisibleSummary) return ""', projection)
        self.assertNotIn('thinking-process.is-empty', STYLE_SOURCE)
        self.assertNotIn("MAX_LEN", projection)
        self.assertNotIn("truncate", projection)
        thought_style_start = STYLE_SOURCE.index(".thinking-summary-list {")
        thought_style_end = STYLE_SOURCE.index("}", thought_style_start)
        thought_style = STYLE_SOURCE[thought_style_start:thought_style_end]
        self.assertIn("color: var(--text)", thought_style)
        self.assertIn("font-size: 14.5px", thought_style)
        self.assertIn("line-height: 1.76", thought_style)
        role_style_start = STYLE_SOURCE.rindex(".role {")
        role_style_end = STYLE_SOURCE.index("}", role_style_start)
        role_style = STYLE_SOURCE[role_style_start:role_style_end]
        self.assertIn("font-size: 12px", role_style)
        self.assertIn("line-height: 1.4", role_style)
        self.assertIn("letter-spacing: .015em", role_style)
        self.assertIn('.msg.assistant > .role:not(.is-empty)::after', STYLE_SOURCE)
        role_rule_start = STYLE_SOURCE.index('.msg.assistant > .role:not(.is-empty)::after')
        role_rule_end = STYLE_SOURCE.index("}", role_rule_start)
        role_rule = STYLE_SOURCE[role_rule_start:role_rule_end]
        self.assertIn("min-width: 24px", role_rule)
        self.assertIn("flex: 1 1 auto", role_rule)
        self.assertNotIn("\n  width: 24px;", role_rule)
        self.assertIn(".thinking-summary-item + .thinking-summary-item", STYLE_SOURCE)
        spacing_start = STYLE_SOURCE.index(".thinking-summary-item + .thinking-summary-item")
        spacing_end = STYLE_SOURCE.index("}", spacing_start)
        self.assertIn("margin-top: .65em", STYLE_SOURCE[spacing_start:spacing_end])
        thought_spacing_start = STYLE_SOURCE.rindex(".thinking-process {")
        thought_spacing_end = STYLE_SOURCE.index("}", thought_spacing_start)
        self.assertIn("margin-bottom: 20px", STYLE_SOURCE[thought_spacing_start:thought_spacing_end])

    def test_streaming_projection_switches_kind_without_leaking_raw_reasoning(self):
        projection_start = APP_SOURCE.index("function renderFinalAssistantProjection")
        projection_end = APP_SOURCE.index("function createCompactSummaryMessage", projection_start)
        projection = APP_SOURCE[projection_start:projection_end]

        self.assertIn('data-stream-session="${escapeHtml(state.sessionId || "")}"', projection)
        self.assertIn('const streamKind = msg._streamProjection === "answer" ? "answer" : "pending"', projection)
        self.assertIn('data-stream-kind="${streamKind}"', projection)
        self.assertIn('streamKind === "pending" ? " is-pending" : ""', projection)
        self.assertIn('data-stream-role', projection)
        self.assertIn('streaming-answer-role${showModel ? "" : " is-empty"}', projection)
        self.assertNotIn('data-stream-part="thought"', projection)
        self.assertNotIn("msg.thought", projection)
        patch_start = APP_SOURCE.index("function patchStreamingAssistantMessage")
        patch_end = APP_SOURCE.index("function scheduleStreamingAssistantPatch", patch_start)
        patch = APP_SOURCE[patch_start:patch_end]
        self.assertIn('streamKind === "thinking"', patch)
        self.assertIn('streamKind !== "answer" || !visibleContent', patch)
        self.assertIn('data-stream-part="summary"', patch)
        self.assertIn('msg._streamProjection === "thinking" && visibleContent', patch)
        self.assertIn("renderSessionMessages(sessionId)", patch)
        self.assertNotIn("preservedNodes", APP_SOURCE)
        self.assertNotIn("appendChild(preservedNode)", APP_SOURCE)

        self.assertIn('_streamProjection: "pending"', APP_SOURCE)

        render_start = APP_SOURCE.index("function renderMessages()")
        render_end = APP_SOURCE.index("function isProcessMessage", render_start)
        render = APP_SOURCE[render_start:render_end]
        self.assertIn("els.messageList.innerHTML = html", render)
        self.assertNotIn("els.messages.innerHTML = html", render)
        self.assertIn("pruneStaleStreamingNodes(state.sessionId)", render)

    def test_tool_round_finalization_is_atomic(self):
        helper_start = APP_SOURCE.index("function finalizeStreamingAssistantMessage")
        helper_end = APP_SOURCE.index("function parseSseLine", helper_start)
        helper = APP_SOURCE[helper_start:helper_end]
        self.assertIn(
            "updateAssistantMessage(index, rawContent, false, sessionId, targetMessages, true)",
            helper,
        )
        self.assertLess(helper.index("current.meta.toolCalls = toolCalls"), helper.index("renderSessionMessages"))

        stream_start = APP_SOURCE.index("const toolCallsByIndex = new Map()")
        stream_end = APP_SOURCE.index("function _safeMd", stream_start)
        stream = APP_SOURCE[stream_start:stream_end]
        self.assertIn(
            'markStreamingAssistantProjection(assistantIndex, "thinking"',
            stream,
        )
        self.assertGreaterEqual(stream.count("finalizeStreamingAssistantMessage("), 2)

    def test_active_run_banner_uses_one_stable_task_status(self):
        helper_start = APP_SOURCE.index("function ensureActiveRunBannerStructure")
        helper_end = APP_SOURCE.index("function normalizeResponseUsage", helper_start)
        helper = APP_SOURCE[helper_start:helper_end]
        self.assertEqual(helper.count("banner.innerHTML ="), 1)
        self.assertIn('nodes.label.textContent = t("processingLabel")', helper)
        self.assertIn("nodes.timer.textContent = getRunTimerDisplay(sessionId)", helper)
        self.assertNotIn("run-model", helper)
        self.assertNotIn("data-active-run-phase", helper)
        self.assertNotIn("function setTaskPhase", APP_SOURCE)
        self.assertNotIn("_taskPhase", APP_SOURCE)
        self.assertNotIn("executingTool", APP_SOURCE)

    def test_active_run_banner_uses_stable_anchor_above_thought_process(self):
        wrapper = """<div id="messages" class="messages">
            <div id="messageList" class="message-list"></div>
            <div id="activeRunBanner" class="active-run-banner hidden"></div>
          </div>"""
        self.assertIn(wrapper, INDEX_SOURCE)
        self.assertLess(INDEX_SOURCE.index('id="activeRunBanner"'), INDEX_SOURCE.index('id="chatForm"'))

        render_start = APP_SOURCE.index("function renderMessages()")
        render_end = APP_SOURCE.index("function isProcessMessage", render_start)
        render = APP_SOURCE[render_start:render_end]
        user_start = render.index('if (msg.role === "user") {')
        user_end = render.index("continue;", user_start)
        user_projection = render[user_start:user_end]
        self.assertLess(
            user_projection.index("rows.push(renderUserProjection(msg, j))"),
            user_projection.index("insertActiveRunAnchor()"),
        )
        self.assertIn('data-active-run-anchor', render)
        self.assertLess(render.index("parkActiveRunBanner();\n  els.messageList.innerHTML = html"), render.index("mountActiveRunBanner();", render.index("els.messageList.innerHTML = html")))

        helper_start = APP_SOURCE.index("function parkActiveRunBanner")
        helper_end = APP_SOURCE.index("function syncActiveRunBanner", helper_start)
        helper = APP_SOURCE[helper_start:helper_end]
        self.assertIn("els.messages.appendChild(banner)", helper)
        self.assertIn("anchor.appendChild(banner)", helper)

        banner_start = STYLE_SOURCE.index(".active-run-banner {")
        banner_end = STYLE_SOURCE.index(".active-run-banner.visible", banner_start)
        banner = STYLE_SOURCE[banner_start:banner_end]
        self.assertIn("position: static", banner)
        self.assertIn("width: 100%", banner)
        self.assertNotIn("bottom:", banner)
        self.assertNotIn("transform:", banner)

        line_start = STYLE_SOURCE.index(".active-run-line {")
        line_end = STYLE_SOURCE.index(".active-run-indicator", line_start)
        line = STYLE_SOURCE[line_start:line_end]
        self.assertIn("display: inline-flex", line)
        self.assertNotIn("background:", line)
        self.assertNotIn("border:", line)
        self.assertNotIn("border-radius:", line)

        self.assertIn("--composer-safe-bottom", STYLE_SOURCE)
        self.assertIn("function syncComposerSafeArea()", APP_SOURCE)
        self.assertIn("new ResizeObserver(syncComposerSafeArea)", APP_SOURCE)


if __name__ == "__main__":
    unittest.main()

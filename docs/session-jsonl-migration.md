# Code 会话存储 JSON → JSONL 迁移方案

## Context

当前每次保存会话都要序列化并重写整个 JSON 文件（含完整 messages 数组）。147 个现有会话，最大 4MB+。流式输出时频繁全量写入，浪费 I/O 且崩溃风险大。

目标：拆分为双文件存储，元数据用 JSON（全量重写），消息用 JSONL（逐行追加）。

## 两阶段策略

| 阶段 | 范围 | 效果 |
|------|------|------|
| **Phase 1** | 纯后端改动，API 契约不变 | 消息已拆到 JSONL，崩溃安全，前端零改动 |
| **Phase 2** | 新增前端增量追加 | 流式输出时只发新消息，不再全量传输 |

---

## Phase 1：后端存储拆分（前端零改动）

### 1.1 新增核心函数（server.py，接在 `write_json` 后，~line 797）

```
messages_path(session_id)    → SESSIONS_DIR / f"{id}.jsonl"
read_jsonl(path)             → 逐行 parse，跳过空行/损坏行，返回 list[dict]
write_jsonl(path, messages)  → 全量写入（atomic: temp + os.replace）
append_jsonl(path, messages) → 追加写入（open "a"，受 _json_write_lock 保护）
count_jsonl_lines(path)      → 快速行数统计（不 parse）
read_last_jsonl_line(path)   → seek 到文件尾部读最后一行，提取 _time
```

### 1.2 迁移函数（server.py）

```python
def migrate_session_if_needed(session_id):
    """幂等迁移：旧 .json（含 messages）→ .json（纯元数据）+ .jsonl"""
    if jsonl 已存在: return
    读旧 JSON → 提取 messages → write_jsonl → 从 JSON 删 messages → write_json
```

受 `_json_write_lock` 保护，避免并发双重迁移。

### 1.3 修改现有端点（全部在 server.py）

| 函数 | 行号 | 改动 |
|------|------|------|
| `get_sessions` | 2002 | 每个 session 先调 `migrate_session_if_needed`；`session_summary` 用 `count_jsonl_lines` + `read_last_jsonl_line` |
| `get_session` | 2013 | 先迁移；读 meta JSON + read_jsonl → 合并返回 |
| `create_session` | 2022 | meta 写 JSON（不含 messages），messages 写 JSONL |
| `save_session` | 2043 | meta → write_json；messages → write_jsonl（全量覆写，Phase 1 折衷） |
| `archive_session` | 2066 | `shutil.copy2` JSONL 到 archive 目录 |
| `delete_session` | 2080 | `unlink` 两个文件（.json + .jsonl） |
| `branch_session` | 2120 | `shutil.copy2` 父 JSONL → 子 JSONL；`_branchMsgCount` 用 `count_jsonl_lines` |
| `session_summary` | 1098 | `messageCount` 从 meta 或 `count_jsonl_lines` 取；`lastMessageTime` 用 `read_last_jsonl_line` |

### 1.4 启动迁移（server.py main，~line 711）

```python
for path in SESSIONS_DIR.glob("*.json"):
    try: migrate_session_if_needed(path.stem)
    except Exception: print(f"[WARN] migrate failed: {path}")
```

### 1.5 API 契约保证

- `GET /api/sessions/{id}` 仍然返回完整 session（含 messages 数组）
- `PUT /api/sessions/{id}` 仍然接收完整 messages 数组
- 前端 **完全不动**

---

## Phase 2：前端增量追加

### 2.1 新增 API 端点（server.py）

**`POST /api/sessions/{id}/messages`**：
- 接收 `{"messages": [...]}`
- `append_jsonl` 逐条追加
- 更新 meta JSON 的 `updatedAt` 和 `messageCount`
- 返回 `{"ok": true, "appended": N}`

路由：在 `do_POST` 中优先匹配 `/messages` 后缀，再匹配 `/branch`。

### 2.2 前端新增函数（app.js）

```js
appendSessionMessages(sessionId, newMessages)  // POST /api/sessions/{id}/messages
getPersistedCount(sessionId)                    // 已持久化到磁盘的消息数
markMessagesPersisted(sessionId, count)         // 更新追踪
```

### 2.3 修改 `saveSessionState`（app.js line 5820）

- 计算 delta：`newMsgs = allMessages.slice(persistedCount)`
- delta 非空 → `appendSessionMessages`（只发新消息）
- 元数据（title, stats, runState）→ PUT `/api/sessions/{id}`（不含 messages）
- 全程不发送完整 messages 数组

### 2.4 流式保存策略

- **进行中的消息不追加**：`allMessages.slice(persisted, -1)` 排除最后一条（正在流式输出）
- **流结束时**：`clearRunCheckpoint` 中 flush 全部含最后一条
- **切会话时**：`cacheActiveSessionState` 中 flush 剩余
- **页面关闭前**：`beforeunload` + `navigator.sendBeacon` 兜底

### 2.5 加载时重置追踪

`loadSession` 中：`markMessagesPersisted(id, messages.length)`

---

## 测试更新

| 测试文件 | 改动 |
|----------|------|
| `tests/test_session_persistence.py` | +JSONL atomic 写入测试、+并发追加测试、+损坏行恢复测试 |
| `tests/test_branch.py` | +分支后 JSONL 文件拷贝验证、`_branchMsgCount` 正确性 |
| `tests/test_routes.py` | +`POST /api/sessions/{id}/messages` 端点测试 |
| `tests/test_concurrency.py` | +并发 append_jsonl 50 条消息完整性测试 |
| `tests/test_p0_stability.py` | 更新直接读 session JSON 的测试（消息已移到 JSONL） |
| **新增** `tests/test_migration.py` | 迁移幂等性、元数据保留、空会话迁移、并发迁移安全 |

---

## 实施顺序

1. JSONL I/O 函数（`read_jsonl`, `write_jsonl`, `append_jsonl`, `count_jsonl_lines`, `read_last_jsonl_line`, `messages_path`）
2. `migrate_session_if_needed` + 启动迁移
3. `create_session` + `save_session`（最核心的两个写入函数）
4. `get_session` + `get_sessions`（读取兼容）
5. `delete_session` + `branch_session` + `archive_session`
6. `session_summary` 适配
7. 写测试 + 跑全量 → 确认 412 项通过
8. Phase 2：新增 append 端点 + 前端增量保存
9. Phase 2 测试 + 手动验证

## 验证

1. `python -m pytest tests/ -q` — 全量通过
2. 新建会话 → 发消息 → 检查 `data/sessions/{id}.jsonl` 逐行正确
3. 打开旧会话 → 自动迁移 → 消息完整无损
4. 长对话流式输出 → JSONL 增量追加（不重写全文件）
5. 强制杀进程 → 重启 → 最多丢最后一条未完成消息
6. 分支 → 子会话 JSONL 是父会话的独立副本

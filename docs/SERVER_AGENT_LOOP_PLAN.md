# 服务端 Agent 循环迁移计划

## 目标

让一次 Code 任务由本地 Python 服务完整持有。浏览器只负责提交任务、展示事件和处理用户决策；页面刷新、切换会话或完全关闭后，服务端仍能继续执行无需人工确认的模型轮次与工具调用。

## 当前边界

截至 2026-07-18，服务端同时具备两层运行时：单次模型轮次由 `/api/runtime/runs` 持有；独立的 `/api/agent/runs` 持久化多轮消息，自动执行首批四个只读工具，并通过 `waiting_user_input` 持久等待结构化问卷答案。正式界面的“只读分析”权限是显式所有权开关：该档位由 AgentRun 编排完整任务，其余权限档位仍由浏览器端 `runAgentLoop()` 编排。

正式界面目前有两条互斥链路：

1. “只读分析”提交任务级 AgentRun，服务端独立完成模型与只读工具续轮，必要时持久暂停问卷并接收浏览器答案；浏览器按游标投影事件，并直接附着当前子模型运行时保持原有流式体验；
2. 计划、接受编辑和自动模式继续提交单轮模型运行，工具与续轮仍由浏览器执行；
3. 会话检查点记录执行所有者，任何任务只会进入其中一条链路，不做自动降级或双重消费；
4. 刷新、切换会话和页面关闭不会取消 AgentRun，恢复时按持久游标重放尚未投影的事件。

只读 AgentRun 已成为正式界面的可选产品能力，并已接管无副作用的问卷等待，但不是写入类任务的默认执行器；在副作用协议迁移完成前，不能将写入、命令、权限确认或子任务交给该链路。

## 目标所有权

| 能力 | 当前所有者 | 目标所有者 |
|---|---|---|
| 上游模型连接与重试 | 服务端 | 服务端 |
| SSE 原始事件缓存 | 服务端 | 服务端 |
| 模型轮次结构化结果 | 服务端（阶段 1） | 服务端 |
| Agent 消息构造 | 只读档位在服务端；其他档位在浏览器 | 服务端 |
| 工具注册与执行编排 | 四个只读工具在服务端；其他工具在浏览器 | 服务端 |
| 结构化问卷等待状态 | 服务端状态机；浏览器只提交答案 | 服务端状态机；浏览器只提交答案 |
| 副作用权限决定 | 浏览器 | 服务端状态机；浏览器只提交决定 |
| 子任务调度 | 浏览器 | 服务端 |
| 会话投影与界面渲染 | 浏览器 | 浏览器 |

## 迁移阶段

### 阶段 1：结构化模型轮次结果（已完成）

- 服务端在保存原始 SSE 的同时聚合 `content`、`reasoning`、分片 `tool_calls`、`finish_reason` 和 `usage`。
- `GET /api/runtime/runs/{id}` 的快照新增 `result`，浏览器原有原始事件重放协议保持不变。
- 请求 Payload 与 API Key 在轮次结束后仍立即清空，结构化结果不包含凭据。
- 这一阶段不改变现有前端 Agent 行为，也不引入额外网络等待。

### 阶段 2：服务端工具注册表（首批已完成）

- 已将 `list_files`、`read_file`、`search_files`、`glob_files` 从 HTTP Handler 拆成可直接调用的服务函数。
- `SERVER_TOOL_REGISTRY` 为首批工具声明 `effect=read`、`idempotent=true` 和 `background=true`。
- HTTP `/api/tools/*` 已改为调用注册表，与未来 Agent 循环共用同一实现，避免两套行为漂移。
- `request_user_input` 已作为 `effect=interaction`、`idempotent=true`、`background=false` 的暂停型控制工具加入注册表，不进入普通 HTTP 工具执行器。
- 后续写入、命令、网络与子任务工具将在各自的权限和幂等协议确定后加入注册表。

### 阶段 3：持久化 AgentRun 状态机（只读闭环已完成）

- 已新增任务级 `AgentRun`，持有模型参数、消息、轮次、工具结果、累计用量、状态和事件游标，并写入 `data/agent-runs/{id}.json`。
- 当前状态包含 `model`、`tools`、`waiting_credentials`、`waiting_user_input`、`completed`、`failed`、`cancelled`；`pendingInput`、对应工具执行和事件均随 AgentRun 持久化。
- `list_files`、`read_file`、`search_files`、`glob_files` 可在浏览器完全不轮询时自动完成“模型 → 工具 → 模型”闭环。
- 工具执行前持久化调用 ID、规范化参数与指纹；已完成结果可复用，重复调用不会再次触发执行，但仍补齐模型协议要求的工具结果消息。
- API Key 仅保留在内存；服务重启后活动模型/工具任务转为 `waiting_credentials`，而 `waiting_user_input` 保持可回答。答案成为工具结果后再进入凭据恢复，从持久化检查点继续。
- 正式前端已通过“只读分析”显式切换到 AgentRun；其他权限档位保持原链路，避免同一个工具调用同时被浏览器和服务端消费。

### 阶段 4：前端投影与问卷已完成；权限和写入待迁移

- [已完成] 会话检查点保存 `executionOwner`、`agentRunId`、`agentEventCursor` 和当前子模型 `runtimeRunId`；前端按序投影 AgentRun 事件，并使用“只读分析”完成单一执行所有权切换。
- [已完成] 子模型轮次继续走原 SSE 投影；若短期运行时已过期，则从持久 `model_completed` 事件回填完整回答，不重新请求模型。
- [已完成] 事件游标与对应消息快照有序持久化，刷新、切换会话、页面关闭、取消和服务重启凭据恢复均接入同一检查点。
- [已完成] `request_user_input` 由服务端生成、规范化并持久暂停；浏览器复用原问卷面板，支持逐题保存、刷新恢复和独立端点提交，服务端校验答案后补齐同一工具调用结果。
- 服务端生成副作用待确认事项并暂停任务；浏览器通过独立端点提交允许或拒绝。
- `plan`、`accept`、`bypass` 权限语义在服务端统一校验，前端不能绕过。
- 写入和删除继续保留备份；恢复任务时先核对工具幂等标识和目标文件状态。

### 阶段 5：子任务与前端瘦身

- 子 Agent 迁移到服务端调度器，继承主任务的工具策略且不能自行提升权限。
- `app.js` 删除 Agent 编排逻辑，只保留任务提交、事件投影、用户决策和本地交互。
- 完成浏览器关闭、服务重启、多会话并发、取消、问卷与副作用恢复的端到端测试。

## 不变量

- API Key 不进入运行快照、会话文件、事件日志或错误正文。
- 同一轮工具调用只能由一个所有者执行；迁移期间禁止前后端同时消费同一 `tool_call_id`。
- 所有写入、删除和命令继续经过现有安全检查，不因下沉而放宽权限。
- 原始 SSE 流畅度不能为了后台执行而增加整轮缓冲。
- 旧会话和 v0.5.4 的运行检查点必须可以恢复或明确失败，不能静默丢失任务。

## 阶段 1 API

运行快照新增：

```json
{
  "result": {
    "content": "最终回答增量合并结果",
    "reasoning": "思考摘要增量合并结果",
    "toolCalls": [
      {
        "index": 0,
        "id": "call_123",
        "type": "function",
        "function": {
          "name": "read_file",
          "arguments": "{\"path\":\"README.md\"}"
        }
      }
    ],
    "finishReason": "tool_calls",
    "usage": {
      "prompt_tokens": 120,
      "completion_tokens": 30,
      "total_tokens": 150
    }
  }
}
```

`events`、`nextCursor`、`status` 和取消接口保持兼容，现有前端无需立即切换。

## 阶段 3 API

- `POST /api/agent/runs`：提交 `sessionId`、模型 `payload`、`baseUrl`、内存态 `keys`、可选 `allowedTools` 与 `maxRounds`。
- `GET /api/agent/runs/{id}?cursor=N&wait=25`：按游标读取状态、事件、累计用量、工具执行记录和最终结果。
- `POST /api/agent/runs/{id}/resume`：服务重启后向 `waiting_credentials` 任务重新注入 Key 并继续。
- `POST /api/agent/runs/{id}/input`：向 `waiting_user_input` 任务提交结构化答案；服务端按持久问题校验答案、完成对应工具调用并转入凭据恢复。
- `DELETE /api/agent/runs/{id}`：取消模型请求和 AgentRun；对已进入终态的任务保持幂等。

持久化记录包含请求选项、消息、轮次、工具检查点、`pendingInput` 和事件，但不包含 API Key。显式 Base URL 禁止嵌入用户名或密码，Payload 顶层及嵌套模型选项中的凭据字段会被拒绝。当前 AgentRun 只会向模型暴露注册表中的安全只读工具，以及唯一的暂停型交互工具 `request_user_input`。

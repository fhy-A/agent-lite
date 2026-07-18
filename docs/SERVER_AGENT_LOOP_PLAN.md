# 服务端 Agent 循环迁移计划

## 目标

让一次 Code 任务由本地 Python 服务完整持有。浏览器只负责提交任务、展示事件和处理用户决策；页面刷新、切换会话或完全关闭后，服务端仍能继续执行无需人工确认的模型轮次与工具调用。

## 当前边界

截至 2026-07-18，服务端同时具备两层运行时：单次模型轮次由 `/api/runtime/runs` 持有；独立的 `/api/agent/runs` 持久化多轮消息，并能按任务工具策略自动执行项目读取、网络、Skills、命令、项目记忆、直接文件变更和子任务。每个 `task` 都会创建独立持久 Child AgentRun，记录父运行与父工具调用，继承模型、权限和工具策略但移除再次委派与交互问卷；同一模型轮次最多同时运行 3 个子任务，空位释放后再启动排队调用，父模型工具结果严格按原调用顺序回填。子任务授权经父任务代理，取消向子任务传播，完成结果和用量只合并一次，服务重启后复用原 Child AgentRun。正式界面的 `read`、`plan` 和 `accept` 已切换到服务端单一执行所有权；`bypass` 暂时保留浏览器链路，等待明确产品入口和端到端边界。

正式界面目前有两条互斥链路：

1. “只读分析”“计划”和“接受编辑”提交任务级 AgentRun，服务端按权限档位独立完成模型与工具续轮，必要时持久暂停问卷或授权并接收浏览器决定；浏览器按游标投影事件，并直接附着当前子模型运行时保持原有流式体验；
2. 自动模式继续提交单轮模型运行，工具与续轮仍由浏览器执行；
3. 会话检查点记录执行所有者，任何任务只会进入其中一条链路，不做自动降级或双重消费；
4. 刷新、切换会话和页面关闭不会取消 AgentRun，恢复时按持久游标重放尚未投影的事件。

AgentRun 已接管正式界面的只读、计划和接受编辑任务。计划提案保持只预览、不落盘；接受编辑的编辑、直接写入、删除和命令均由服务端持久暂停授权，浏览器仅展示真实动作与目标并提交决定。自动模式尚未迁移，任何任务仍只会进入一条所有权链路，禁止浏览器与 AgentRun 同时消费同一工具调用。

## 目标所有权

| 能力 | 当前所有者 | 目标所有者 |
|---|---|---|
| 上游模型连接与重试 | 服务端 | 服务端 |
| SSE 原始事件缓存 | 服务端 | 服务端 |
| 模型轮次结构化结果 | 服务端（阶段 1） | 服务端 |
| Agent 消息构造 | `read` / `plan` / `accept` 在服务端；`bypass` 在浏览器 | 服务端 |
| 工具注册与执行编排 | 全部工具及有界并发子任务均已在服务端；`bypass` 尚未切换 | 服务端 |
| 结构化问卷等待状态 | 服务端状态机；浏览器只提交答案 | 服务端状态机；浏览器只提交答案 |
| 副作用权限决定 | `accept` 由服务端状态机持有；浏览器只展示并提交决定 | 服务端状态机；浏览器只提交决定 |
| 子任务调度 | 服务端持久 Child AgentRun，单轮并发上限 3，结果顺序稳定 | 服务端 |
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
- `propose_edit` 已作为 `effect=proposal`、`idempotent=true` 工具加入注册表；计划档位只返回提案，接受编辑档位持久等待授权，自动档位可通过同一幂等应用服务执行。正式界面的计划与接受编辑已经切换，自动档位仍待迁移。
- `web_fetch`、`use_skill` 和 `read_skill_resource` 已拆成可直接调用的服务函数并加入注册表；现有 HTTP 路由与 AgentRun 共用实现，运行结果可进入持久工具检查点而无需浏览器中继。
- Skill 资源读取只允许 `scripts/`、`references/` 和 `assets/` 内的文件，并同时校验 Skill 名称和解析后的资源根目录，拒绝跨目录访问。
- `run_command` 已作为 `effect=command`、`idempotent=false` 工具加入注册表；HTTP 与 AgentRun 共用安全检查和进程服务，`accept` 持久等待授权，`bypass` 可直接执行。运行输出按上限持续写入工具检查点，取消会终止进程树，服务重启后绝不自动重放已启动命令。
- `save_memory` 已作为 `effect=memory_write`、`idempotent=true`、`background=true` 工具加入注册表；`accept` / `bypass` 可由 AgentRun 直接执行。HTTP 与 AgentRun 共用原子写入服务，已存内容一致时返回重放结果而不改写文件。
- `write_file` / `delete_file` 已作为 `effect=file_mutation`、`idempotent=true`、`background=true` 工具加入注册表；HTTP 和 AgentRun 共用路径校验、备份和变更实现。模型不具有独立建目录工具：写入时的父目录由写入服务创建，其余目录操作继续经受控命令。
- `task` 已作为 `effect=delegation`、`idempotent=true`、`background=true` 加入注册表；仅 `plan` / `accept` / `bypass` 可选择。同一模型轮次最多并发启动 3 个 Child AgentRun，额外调用等待空位，全部结果按父工具调用顺序写入消息协议。

### 阶段 3：持久化 AgentRun 状态机（已完成）

- 已新增任务级 `AgentRun`，持有模型参数、消息、轮次、工具结果、累计用量、状态和事件游标，并写入 `data/agent-runs/{id}.json`。
- 当前状态包含 `model`、`tools`、`waiting_credentials`、`waiting_user_input`、`waiting_authorization`、`completed`、`failed`、`cancelled`；`pendingInput`、`pendingAuthorization`、对应工具执行和事件均随 AgentRun 持久化。
- `list_files`、`read_file`、`search_files`、`glob_files`、`web_fetch`、`use_skill` 和 `read_skill_resource` 可在浏览器完全不轮询时自动完成“模型 → 工具 → 模型”闭环；正式“只读分析”入口仍只暴露四个本地项目读取工具，保持现有产品边界不变。
- `run_command` 可在 `accept` 授权后或 `bypass` 策略下由 AgentRun 执行；stdout/stderr 尾部、字符计数和最后输出时间随运行持久化。活动命令被取消时同步终止进程，服务重启遇到 `running` 检查点时生成 `unknownState + notReplayed` 工具结果，让模型基于不确定状态继续而不是重复执行。
- `save_memory` 的执行状态和结果随 AgentRun 持久化；若服务在文件替换完成但工具结果尚未落盘时退出，恢复后会以相同参数重放，通过内容一致性识别原结果，不重写文件或更新修改时间。
- `write_file` / `delete_file` 在 `accept` 下先进入持久授权，批准决定落盘并重新注入凭据后才执行；`bypass` 可直接执行。写入使用原子替换和稳定备份识别重放；删除在真正移除目标前先落盘稳定备份与操作收据，恢复时可区分“本次已删除”和“原本就不存在”。
- `task` 为每个父工具调用创建独立 AgentRun，并持久化 `parentAgentRunId`、`parentToolCallId` 与深度。子任务继承父任务模型、权限和允许工具，但移除 `task` 与 `request_user_input`，不能嵌套委派或打开自己的问卷；子任务副作用授权由父任务稳定代理，批准后随父任务凭据恢复继续。
- 父任务取消会同步取消活动子任务；子任务终态、工具统计和用量写回父工具结果，用量通过持久标记只合并一次。父进程在子任务完成后、父工具结果落盘前退出时，恢复会按原 Child AgentRun ID 复用结果，不再次请求子模型。
- 工具执行前持久化调用 ID、规范化参数与指纹；已完成结果可复用，重复调用不会再次触发执行，但仍补齐模型协议要求的工具结果消息。
- API Key 仅保留在内存；服务重启后活动模型/工具任务转为 `waiting_credentials`，而 `waiting_user_input` 与 `waiting_authorization` 保持可提交决定。答案或授权结果成为工具结果后再进入凭据恢复，从持久化检查点继续。
- 正式前端的 `read`、`plan` 和 `accept` 已显式切换到 AgentRun；`bypass` 保持原链路，避免同一个工具调用同时被浏览器和服务端消费。

### 阶段 4：前端投影、问卷、授权与正式变更所有权（已完成）

- [已完成] 会话检查点保存 `executionOwner`、`agentRunId`、`agentEventCursor` 和当前子模型 `runtimeRunId`；前端按序投影 AgentRun 事件，并使用“只读分析”完成单一执行所有权切换。
- [已完成] 子模型轮次继续走原 SSE 投影；若短期运行时已过期，则从持久 `model_completed` 事件回填完整回答，不重新请求模型。
- [已完成] 事件游标与对应消息快照有序持久化，刷新、切换会话、页面关闭、取消和服务重启凭据恢复均接入同一检查点。
- [已完成] `request_user_input` 由服务端生成、规范化并持久暂停；浏览器复用原问卷面板，支持逐题保存、刷新恢复和独立端点提交，服务端校验答案后补齐同一工具调用结果。
- [已完成] `propose_edit` 共用原 HTTP 编辑构建服务；`plan` 只返回提案，`accept` 生成稳定授权 ID 并进入 `waiting_authorization`，浏览器客户端可通过独立端点提交 `approved` / `rejected`。
- [已完成] 编辑应用同时核对提案内容哈希、原文件哈希和 mtime，并在进程内串行执行备份、同目录原子替换与写后校验；若崩溃发生在写入后、状态落盘前，重复批准会识别最终内容并复用结果，不产生第二次写入或备份。
- [已完成] 文件在等待授权期间被其他任务修改时返回冲突工具结果，不覆盖新内容；拒绝决定同样补成原 `tool_call_id` 的正式工具结果。
- [已完成] 正式前端将 `pendingAuthorization` 投影为现有 diff 审查卡片，以稳定授权 ID 去重；卡片和决定进度进入会话检查点。刷新后即使原 Promise 已消失，也能直接提交决定并恢复同一个 AgentRun；会话切换只显示当前会话的授权项。
- [已完成] `web_fetch`、`use_skill` 和 `read_skill_resource` 已进入服务端注册表和 AgentRun 持久执行链；HTTP 工具接口共用同一实现，工具结果和凭据边界由自动化闭环验证。
- [已完成] `run_command` 已接入服务端注册表、持久授权、增量输出、超时、取消和不可重放恢复；批准决定先持久化为 `authorized`，恢复凭据后才启动进程，拒绝直接补成工具结果。
- [已完成] `save_memory` 已接入服务端注册表和 AgentRun，HTTP/后台任务共用幂等原子写入服务，恢复重放不重写已保存记忆。
- [已完成] `write_file` / `delete_file` 已接入共享服务、持久授权和 AgentRun 恢复；写入重放不重写或重复备份，删除重放通过操作收据识别原结果。
- [已完成] 建立持久 Child AgentRun、父子关系、权限继承、授权代理、取消传播、用量合并、重启复用，以及同轮最多 3 个子任务的有界并发和确定性结果排序。
- [已完成] 正式 `plan` / `accept` 任务切换为 AgentRun 单一执行所有者；工具集合按任务保存的权限档位和工具预设恢复，`plan` 不获得命令与直接变更能力，`accept` 的副作用均走持久授权。
- [已完成] 授权界面按真实动作展示编辑、写入、删除或命令；文件变更复用同一 diff 投影承接批准、执行和最终结果，子任务代理授权读取嵌套结果，不生成重复工具结果或错误的拒绝状态。
- [已完成] 人工验证计划提案不落盘、接受模式写入授权在刷新后恢复、删除授权完成清理，以及运行中停止任务；自动化完整回归为 `537 passed, 25 subtests passed`。
- [待完成] 为 `bypass` 建立明确的产品入口与正式前端端到端验证。

### 阶段 5：子任务与前端瘦身（服务端子任务协议已完成）

- [已完成] 子 Agent 迁移到服务端持久调度器，继承主任务的模型、权限和工具策略且不能自行提升权限或嵌套委派。
- [已完成] 对同轮多个子任务实施并发上限 3 的调度，排队调用在空位释放后启动，模型工具结果保持原调用顺序。
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

- `POST /api/agent/runs`：提交 `sessionId`、模型 `payload`、`baseUrl`、内存态 `keys`、可选 `allowedTools`、`maxRounds` 与 `permissionProfile`。
- `GET /api/agent/runs/{id}?cursor=N&wait=25`：按游标读取状态、事件、累计用量、工具执行记录和最终结果。
- `POST /api/agent/runs/{id}/resume`：服务重启后向 `waiting_credentials` 任务重新注入 Key 并继续。
- `POST /api/agent/runs/{id}/input`：向 `waiting_user_input` 任务提交结构化答案；服务端按持久问题校验答案、完成对应工具调用并转入凭据恢复。
- `POST /api/agent/runs/{id}/authorization`：向 `waiting_authorization` 任务提交稳定授权 ID 和 `approved` / `rejected` 决定；编辑批准会完成幂等应用，命令批准先持久化为待执行授权，拒绝则直接形成工具结果，随后均转入凭据恢复。
- `DELETE /api/agent/runs/{id}`：取消模型请求和 AgentRun；对已进入终态的任务保持幂等。

持久化记录包含请求选项、消息、轮次、工具检查点、父子 AgentRun 关系、`pendingInput`、`pendingAuthorization` 和事件，但不包含 API Key。显式 Base URL 禁止嵌入用户名或密码，Payload 顶层及嵌套模型选项中的凭据字段会被拒绝。服务端会按权限档位筛选工具：`read` 只允许只读工具和问卷；`plan` / `accept` / `bypass` 可获得编辑提案与 `task`；只有 `accept` / `bypass` 可获得命令、记忆和直接文件变更。Child AgentRun 会进一步移除 `task` 与 `request_user_input`。

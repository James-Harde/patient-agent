# Development Log

## 2026-08-13

### Change (7) — 清空会话主动取消与 SSE 防竞态

修复 `/chat` 在生成期间清空后，旧 SSE 请求仍可能通过 `done`、`error`、`catch` 或 `finally` 把页面从“空闲”改回“已完成/请求失败”，或污染紧接着发起的新一轮请求的问题。

**实际修改：**

- `Agent/app/static/chat.js`
  - 新增模块级 `_requestGeneration` 和 `_activeRequest`，每轮请求使用递增 `requestId` 与独立 `AbortController`。
  - fetch 传入 `controller.signal`；清空会话时先递增 generation 并移除活动请求引用，再调用 `abort()`。
  - `readAgentEventStream()` 在读取响应、处理每个 `status/delta/done/error` 以及跨分片循环前后检查当前 `requestId`；请求失效时静默取消 reader 并返回。
  - `onSubmit()` 在构建图片请求体后、fetch 返回后、流读取完成后、`catch` 和 `finally` 中检查 `requestId`。旧请求的成功、异常和收尾都不能更新页面。
  - 主动中断或失效请求不会创建失败消息，不显示“请求失败/请求中断”。
  - `clearChat()` 立即清空消息、图片和输入，清理全部计时器，恢复发送按钮并设置“空闲”。
  - 计时器 Map 改用消息对象作为键；回调同时校验相同索引仍指向同一消息，避免清空后新消息复用旧索引时被旧计时器更新。

**保持不变：**

- 未修改后端 SSE 路由、Agent 编排、模型调用、工具逻辑、TTS、记忆、数据库、FAISS、RAG、MCP、LangGraph、`/query` 或 `app.js`。
- 清空会话仅重置当前浏览器页面，不发起删除接口，不删除 SQLite 对话记忆、长期记忆、患者资料或 FAISS 数据。
- 未引入依赖、WebSocket 或测试文件。

**验证结果：**

- `node --check Agent/app/static/chat.js` 通过。
- 使用内存 DOM/fetch/ReadableStream 模拟验证：生成中清空会触发 abort 且持续保持空闲；旧 `done/error/catch/finally` 不再写回；清空后立即发起新一轮时旧事件和旧 finally 不影响新消息或发送按钮；正常请求仍完成并自动折叠。
- 未运行真实浏览器、真实模型、图片或 TTS 人工验收；当前状态为“主动取消修复已实现，等待人工验收”。

**本任务修改文件：**

- `Agent/app/static/chat.js`
- `DEV_STATUS.md`
- `DEV_LOG.md`
- `MANUAL_TESTS.md`

### Remaining Issues

- 按 `MANUAL_TESTS.md` 完成四项浏览器人工验收。

---

### Change (6) — SSE 执行过程等待体验：呼吸动画与等待计时

在 Change (5) 的“可折叠执行过程”基础上，补充等待期间的轻量反馈，解决模型等待时页面看起来像静止卡住的问题。未重写现有实现，未开始 LangGraph。

**实际修改：**

- `Agent/app/static/chat.js`
  - 新增模块级计时器管理（`_activeTimers`、`_clearMessageTimer`、`_clearAllTimers`、`_startElapsedTimer`），每个消息用 `setInterval` 每秒刷新一次等待秒数。
  - 每个进行中步骤记录 `_startedAt`；完成后记录 `_duration`（秒），用于折叠后展开查看真实耗时。
  - 进行中步骤显示“正在 X · N 秒”；已完成步骤显示“已完成 X · N 秒”；失败步骤显示“X 失败 · N 秒”。
  - `planning` 步骤新增固定、安全说明“模型正在判断需要调用哪些业务能力”，仅在进行中显示。
  - 收到下一条真实 status（`tool/started` 或 `generating`）时停止上一阶段计时并将上一阶段标记完成，再为新阶段开始计时。
  - `done` 后停止所有计时器、把剩余进行中步骤标记完成、记录耗时并自动折叠执行过程。
  - `error` 后停止所有计时器、保留已完成步骤、当前步骤标记失败、显示“执行失败”、不自动折叠。
  - 清空会话（`clearChat`）、发起下一轮请求（`onSubmit` 开头）、请求失败路径都会清理旧计时器，避免内存泄漏和上一轮状态串到下一轮。
  - 计时器只更新等待秒数；所有步骤仍由真实 SSE `status` 事件驱动，不伪造工具调用或虚假进度。
- `Agent/app/static/styles.css`
  - 新增 `@keyframes breathe`，对进行中步骤的圆点标记应用 1.6s 呼吸动画。
  - 新增 `.execution-step-body`（纵向布局）和 `.execution-step-subtext`（次要说明）样式。

**保持不变：**

- 未修改 `Agent/app/orchestration/patient_agent.py` 和 `Agent/app/api/routes.py`：现有 `planning` → `tool/started|completed` → `generating` 的 SSE 状态已足够让前端正确结束 planning 阶段，无需补充事件。
- 未修改 `chat.html`、`routes.py`、`/query`、`app.js`、数据库、模型配置、TTS、RAG、FAISS、MCP、LangGraph 或其他业务逻辑。
- 未引入新依赖。
- 不展示模型原始思维链、`reasoning_content`、Prompt、Planner 内容、工具参数、工具原始结果、模型草稿或患者敏感信息。

**验证结果：**

- `node --check Agent/app/static/chat.js` 通过。
- `Agent/app/orchestration/patient_agent.py` 与 `Agent/app/api/routes.py` 通过 `ast.parse` 语法检查（UTF-8）。
- 未运行需要真实模型、数据库、浏览器和 TTS 的人工测试；当前状态为“已实现，等待用户人工验收”。

**本任务修改文件：**

- `Agent/app/static/chat.js`
- `Agent/app/static/styles.css`
- `DEV_STATUS.md`
- `DEV_LOG.md`
- `MANUAL_TESTS.md`

### Remaining Issues

- 按 `MANUAL_TESTS.md` 新增的“等待体验”章节完成浏览器人工验收。

---

### Change (5) — SSE execution process display

在现有 SSE 链路上补充了 `/chat` 每轮助手消息内的轻量级执行过程展示。本次展示的是实际业务阶段，不是模型思维链。

**实际修改：**

- `PatientAgent.run_stream()` 在最终回答开始流式生成前发送 `generating` 状态。
- 每次真实工具调用前发送 `tool / started`，工具正常返回后发送 `tool / completed`；工具抛出异常时发送 `tool / failed` 后继续走现有安全 `error` 事件。
- Agent 内部工具名映射为安全中文名称；未知工具统一显示“调用业务工具”。状态事件不包含工具参数、原始结果、患者敏感字段、Prompt、Planner 内容或模型草稿。
- `/chat` 复用助手消息底部原有 `message-meta` 折叠区域，将“工具调用”改为“执行过程”，不再渲染 `tool_outputs` 原始 JSON。
- 执行中折叠区自动展开并实时更新同一条步骤的进行中/完成/失败状态；`done` 后自动折叠并显示步骤总数；`error` 时保持展开并显示执行失败。
- 页面右上角只保留“回复中 / 已完成 / 请求失败”等整体状态；没有新增页面级时间线或更改聊天布局。

**SSE status 变化：**

```text
event: status
data: {"stage":"planning"}

event: status
data: {"stage":"tool","status":"started","name":"验证患者身份"}

event: status
data: {"stage":"tool","status":"completed","name":"验证患者身份"}

event: status
data: {"stage":"generating"}
```

工具失败时使用：

```text
event: status
data: {"stage":"tool","status":"failed","name":"验证患者身份"}
```

**保持不变：**

- `delta` 仍只包含最终回答文本；Planner、工具执行和草稿没有伪装成逐字思考。
- `POST /api/agent/query/stream`、`POST /api/agent/query`、TTS、记忆保存、图片输入和 Agent 工具业务逻辑保持原有链路。
- `/query`、`app.js`、数据库、模型配置、RAG、FAISS、MCP 和 LangGraph 均未在本任务中修改。

**验证结果：**

- 已运行无副作用的 Python AST 语法检查与 `node --check`。
- 已用内存中的假 LLM/工具和分片 SSE 数据验证状态顺序、工具完成时机、中文安全名称、步骤更新、完成折叠及异常保留。
- 未运行需要真实模型、数据库、浏览器和 TTS 的人工测试；当前状态为“已实现，等待人工验收”。

**本任务修改文件：**

- `Agent/app/orchestration/patient_agent.py`
- `Agent/app/static/chat.js`
- `Agent/app/static/styles.css`
- `DEV_STATUS.md`
- `DEV_LOG.md`
- `MANUAL_TESTS.md`

### Remaining Issues

- 按 `MANUAL_TESTS.md` 完成三组浏览器人工验收，重点观察真实工具开始/完成时序和完成后的自动折叠。

---

### Change (4) — SSE streaming output

实现了从 OpenAI-compatible 模型响应到浏览器渲染的完整 SSE 流式链路。

**实现内容：**

- `LLMClient.stream_complete()` 使用 `chat.completions.create(..., stream=True)`，仅逐段产出非空 `delta.content`。
- `PatientAgent.run()` 与 `run_stream()` 共用 Planner 和工具执行循环；流式版本发送 `planning`、`tool` 状态，并只通过模型原生流式 Finalizer 产出最终答案。
- 新增 `POST /api/agent/query/stream`，以 `status`、`delta`、`done`、`error` SSE 事件返回 JSON 数据。
- SSE 在 `done` 前完成 TTS、短期对话保存和长期记忆触发；流式请求使用独立数据库 Session，并在结束或异常时关闭。
- `/chat` 改用 `fetch` POST JSON 和 `ReadableStream`，支持图片请求体、UTF-8 分片解码、跨网络块的 SSE 事件拼接、增量文本渲染和最终音频/工具结果补全。
- 原 `POST /api/agent/query` 的请求、响应和业务行为保持不变；其 TTS 与记忆收尾改为和流式端点复用相同辅助函数。

**安全边界：**

- 流式端点不返回 Planner debug，避免暴露内部计划、提示词或思维链。
- 流中异常转换为固定的可展示错误消息；日志只记录异常类型，不输出 Key、内部配置或堆栈。

**验证结果：**

- Python 三个修改模块通过 `compile()` 语法检查。
- `chat.js` 通过 `node --check`，并通过任意字节分片的 SSE 解析测试。
- 使用假 LLM/工具的针对性测试覆盖非流式兼容、状态事件、模型原生增量累积、SSE JSON 边界和最终结果一致性。
- 需要有效 LLM/TTS 配置的浏览器与 `curl.exe -N` 实机测试尚未运行。

**受影响文件：**

- `Agent/app/llm/llm.py`
- `Agent/app/orchestration/patient_agent.py`
- `Agent/app/api/routes.py`
- `Agent/app/static/chat.js`
- `DEV_STATUS.md`
- `DEV_LOG.md`
- `MANUAL_TESTS.md`

### Remaining Issues

- 按 `MANUAL_TESTS.md` 完成带真实模型、图片、TTS 和记忆写入的手工验收。

---

### Change (3) — 结构与命名收口

轻量级结构整理，不实现新功能，不引入新框架，不大改 demo。

**移动 / 重命名的文件：**

| 旧路径 | 新路径 | 说明 |
|---|---|---|
| `app/llm/qwen_client.py` | `app/llm/llm.py` | 类名 `QwenClient` → `LLMClient` |
| `app/llm/qwen_speech_client.py` | `app/llm/speech_client.py` | 类名 `QwenSpeechClient` → `SpeechClient` |
| `app/llm/qwen_mcp_agent.py` | `app/orchestration/patient_agent.py` | 类名 `QwenMCPAgent` → `PatientAgent` |
| `app/services/memory_vector_service.py` | `app/services/rag/memory_vector_service.py` | 移至 rag 子包，使用 `llm_env` 读取配置 |

**新增文件：**

| 文件 | 说明 |
|---|---|
| `app/llm/llm_env.py` | 集中读取 LLM / Embedding / TTS 环境变量 |
| `app/llm/__init__.py` | 包标记 |
| `app/orchestration/__init__.py` | 包标记 |
| `app/orchestration/patient_agent.py` | Agent 编排（后续替换为 LangGraph） |
| `app/services/rag/__init__.py` | 包标记 |

**删除的旧文件：**

- `app/llm/qwen_client.py`
- `app/llm/qwen_speech_client.py`
- `app/llm/qwen_mcp_agent.py`
- `app/llm/__init__.py`（旧版，已用新版替换）
- `app/llm_env/` 整个目录（上次任务的中间产物，位置错误）
- `app/services/memory_vector_service.py`（旧位置）

**更新的 import：**

| 旧 import | 新 import |
|---|---|
| `from app.llm.qwen_client import QwenClient` | `from app.llm.llm import LLMClient` |
| `from app.llm.qwen_speech_client import QwenSpeechClient` | `from app.llm.speech_client import SpeechClient` |
| `from app.llm.qwen_mcp_agent import QwenMCPAgent` | `from app.orchestration.patient_agent import PatientAgent` |
| `from app.services import memory_vector_service` | `from app.services.rag import memory_vector_service` |

**受影响文件：**
- `app/api/routes.py` — 更新了 3 条 import 和 3 处类名引用
- `scripts/test_qwen_agent.py` — 更新了 2 条 import 和 2 处类名引用
- `app/services/memory_service.py` — 更新了 memory_vector_service import 路径
- `Agent/.env.example` — 改为纯通用配置，移除 QWEN_* 主配置占位

**没有改变的内容：**
- 业务逻辑、工具调用、Agent 编排行为完全不变
- FAISS 索引 / 检索 / 写入行为不变
- TTS 音频格式和生成逻辑不变
- 前端 HTML/CSS/JS 不变
- 数据库模型和 service 层不变

### Reason

去掉业务代码中的 `qwen_*` 文件名和 `Qwen*` 类名绑定，让项目结构和命名更通用，方便后续切换模型 provider 或编排框架。

### Manual Test Result

Not run.

### Remaining Issues

- None for this task.

---

## 2026-08-11

### Change (2) — Generalize model config names

Added generic `LLM_*`, `EMBEDDING_*`, and `TTS_*` environment variables with fallback to legacy `QWEN_*` / `DASHSCOPE_*` variables. Existing `.env` files with only `QWEN_*` keys continue to work unchanged.

**Fallback chains:**

| Component | Config | Resolution order |
|---|---|---|
| Chat / Agent | API key | `LLM_API_KEY` → `QWEN_API_KEY` |
| Chat / Agent | Base URL | `LLM_BASE_URL` → `QWEN_BASE_URL` → DashScope default |
| Chat / Agent | Model | `LLM_MODEL` → `QWEN_MODEL` → `qwen-vl-plus-latest` |
| Embedding | API key | `EMBEDDING_API_KEY` → `LLM_API_KEY` → `QWEN_API_KEY` |
| Embedding | Base URL | `EMBEDDING_BASE_URL` → `LLM_BASE_URL` → `QWEN_BASE_URL` → DashScope default |
| Embedding | Model | `EMBEDDING_MODEL` → `QWEN_EMBEDDING_MODEL` → `text-embedding-v4` |
| Embedding | Dimensions | `EMBEDDING_DIMENSIONS` → `QWEN_EMBEDDING_DIMENSIONS` → `1024` |
| TTS | API key | `TTS_API_KEY` → `DASHSCOPE_API_KEY` → `QWEN_API_KEY` |
| TTS | Model | `TTS_MODEL` → `QWEN_TTS_MODEL` → `cosyvoice-v3-flash` |
| TTS | Voice | `TTS_VOICE` → `QWEN_TTS_VOICE` → `longanyang` |
| TTS | WebSocket URL | `TTS_WEBSOCKET_URL` → `DASHSCOPE_WEBSOCKET_URL` → DashScope WS default |

### Reason

The project hard-coded Qwen/DashScope-specific env var names (`QWEN_API_KEY`, `QWEN_MODEL`, etc.), which makes it harder to switch to other model providers. The new generic names decouple the config layer from the provider while keeping full backward compatibility.

### Impacted Files

- `Agent/app/llm/qwen_client.py` — `QwenClient.__init__` now resolves `LLM_API_KEY` → `QWEN_API_KEY`, same for model and base URL.
- `Agent/app/services/memory_vector_service.py` — Added `_resolve_api_key()` and `_resolve_base_url()` helpers; `_embedding_model()` and `_embedding_dimensions()` now check `EMBEDDING_*` first, then `QWEN_EMBEDDING_*`.
- `Agent/app/llm/qwen_speech_client.py` — `QwenSpeechClient.__init__` now resolves `TTS_API_KEY` → `DASHSCOPE_API_KEY` → `QWEN_API_KEY`, and similarly for model, voice, and WebSocket URL.
- `Agent/.env.example` — Added generic `LLM_*`, `EMBEDDING_*`, `TTS_*` sections alongside legacy `QWEN_*` section.
- `DEV_STATUS.md` — Marked task 1 as Done, updated Active Task and Next Step.
- `DEV_LOG.md` — This entry.
- `MANUAL_TESTS.md` — Added "模型配置通用化测试" section.

### Manual Test Result

Not run.

### Remaining Issues

- None for this task.

---

### Change (1)

Created baseline secondary-development coordination documents:

- `DEV_STATUS.md`
- `DEV_LOG.md`
- `MANUAL_TESTS.md`

### Reason

The project will be developed in stages across tools. A shared status file, change log, and manual acceptance checklist make it clear what is done, what is pending, and how each change should be tested by a human.

### Impacted Files

- `DEV_STATUS.md`
- `DEV_LOG.md`
- `MANUAL_TESTS.md`

### Manual Test Result

Not run. This is a documentation-only setup step.

### Remaining Issues

- Review the roadmap order before starting feature work.
- Next implementation task should be generic model configuration naming with `QWEN_*` fallback.

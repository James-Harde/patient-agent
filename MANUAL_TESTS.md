# Manual Tests

Run commands from `E:\patient-Agent\Agent` unless noted.

## Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with valid keys before testing Agent, embedding, image, or speech features.

**重要提醒（2026-08-12 结构与命名收口后）：**
`.env` 现在使用通用变量名。至少需要配置：

```env
LLM_API_KEY="你的真实key"
LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL="qwen-vl-plus-latest"
EMBEDDING_API_KEY="你的真实key"
TTS_API_KEY="你的真实key"
```

旧的 `QWEN_*` 变量不再被读取。如果没有配置上述变量，LLM / Embedding / TTS 都会在启动时报明确的配置缺失错误。

## Start The App

```powershell
python -m uvicorn app.main:app --reload
```

Expected result:

- The server starts on `http://127.0.0.1:8000`.
- No import or environment errors appear in the terminal.

Troubleshooting:

- If dependencies are missing, rerun `pip install -r requirements.txt`.
- If the port is busy, stop the existing process or run Uvicorn on another port.
- If you see `LLM_API_KEY is not configured`, check that `.env` has the new generic variable names.

## Health Check

Open:

```text
http://127.0.0.1:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

## Swagger API Page

Open:

```text
http://127.0.0.1:8000/docs
```

Expected result:

- Swagger loads.
- Agent, Patients, Medical Cases, Visit Records, and Memory endpoints are visible.

## Query Page

Open:

```text
http://127.0.0.1:8000/query
```

Test input:

```text
我是王建国，编号是P0003，手机号是13800000003，请帮我查询最近一次就诊记录。
```

Expected result:

- The page sends a request to `/api/agent/query`.
- The answer is based on tool results and does not invent patient records.
- If speech is enabled, an audio player appears after the answer.

## Chat Page

Open:

```text
http://127.0.0.1:8000/chat
```

Test input:

```text
我是王建国，编号是P0003，手机号是13800000003，请帮我总结最近的复诊情况。
```

Expected result:

- A user message and assistant message appear in the chat.
- If a voice is selected, an MP3 playback control appears after the assistant response.

## Agent Smoke Script

```powershell
python scripts/test_qwen_agent.py "我是王建国，编号是P0003，手机号是13800000003，请查询最近一次就诊记录"
```

Expected result:

- JSON is printed.
- `answer` is present.
- `tool_outputs` includes relevant patient verification or visit-record lookup results.

## Image Input Smoke Test

```powershell
python scripts/test_qwen_agent.py "请结合这张图片做说明" --image-file data\wang_jianguo_ecg_test.jpg
```

Expected result:

- The script accepts the image.
- The answer references image content only when the model can inspect it.

## Speech Feature Check

Use `/query` or `/chat`, select a voice instead of `none`, and ask a normal Agent question.

Expected result:

- The response contains a `speech_download_url`.
- A file is written under `data/generated_audio/`.
- The browser audio control can play the MP3.

Troubleshooting:

- Confirm `.env` has a valid key.
- Confirm `dashscope` is installed from `requirements.txt`.
- TTS uses a speech model, not the chat or vision model.

## Pre-Change / Post-Change Rule

Before and after every feature change, run at least:

1. Health check.
2. `/query` basic Agent test.
3. Any feature-specific test listed in the development task.

Do not treat pytest as the primary acceptance signal for this project. Manual behavior must match the requested feature.

---

## 结构与命名收口测试（2026-08-12）

本测试验证文件移动、类名重命名、import 同步后应用仍能正常运行。

### 前置条件

1. 完成 Environment Setup。
2. `.env` 中使用新的通用变量名（`LLM_*` / `EMBEDDING_*` / `TTS_*`），不要使用旧的 `QWEN_*` 变量。
3. 确认 `requirements.txt` 中的依赖已安装。

---

### 测试 1：启动服务

```powershell
cd E:\patient-Agent\Agent
python -m uvicorn app.main:app --reload
```

预期：
- 服务在 `http://127.0.0.1:8000` 启动。
- 终端不出现 `ImportError` 或 `ModuleNotFoundError`。
- 终端不出现 `LLM_API_KEY is not configured` 等配置缺失错误（前提是 `.env` 已正确配置）。

---

### 测试 2：健康检查

打开：

```text
http://127.0.0.1:8000/api/health
```

预期返回：

```json
{"status":"ok"}
```

---

### 测试 3：Query 页面测试

打开：

```text
http://127.0.0.1:8000/query
```

输入：

```text
我是王建国，编号是P0003，手机号是13800000003，请帮我查询最近一次就诊记录。
```

预期：
- 页面正常返回回答。
- 不出现 import error 或 500 错误。
- 回答内容基于工具结果，不编造患者记录。

---

### 测试 4：Chat 页面测试

打开：

```text
http://127.0.0.1:8000/chat
```

输入：

```text
我是王建国，编号是P0003，手机号是13800000003，请帮我总结最近的复诊情况。
```

预期：
- 页面正常返回回答。
- 不出现 import error 或 500 错误。

---

### 测试 5：脚本测试

```powershell
python scripts/test_qwen_agent.py "我是王建国，编号是P0003，手机号是13800000003，请查询最近一次就诊记录"
```

预期：
- 输出 JSON，包含 `answer` 和 `tool_outputs`。
- 脚本不报 `ImportError` 或 `ModuleNotFoundError`。

---

### 测试 6：语音测试

在 `/query` 或 `/chat` 页面选择一个音色（不要选 none），提交查询。

预期：
- 返回的响应中包含 `speech_download_url`。
- 浏览器能播放生成的音频。

---

### 验收标准

| # | 标准 | 测试 |
|---|---|---|
| 1 | 服务能正常启动，无 import error | 1 |
| 2 | `/api/health` 返回 `{"status":"ok"}` | 2 |
| 3 | `/query` 页面 Agent 查询正常工作 | 3 |
| 4 | `/chat` 页面 Agent 查询正常工作 | 4 |
| 5 | `test_qwen_agent.py` 脚本正常运行 | 5 |
| 6 | 选择语音播报时 TTS 能生成可播放的音频 | 6 |
| 7 | 业务代码中不再出现 `qwen_client`、`qwen_mcp_agent`、`qwen_speech_client`、`QwenClient`、`QwenMCPAgent`、`QwenSpeechClient` 引用 | grep 验证 |
| 8 | 无 `__pycache__`、`*.pyc`、`__MACOSX`、`.DS_Store` 被纳入变更 | git status 验证 |

---

## 模型配置通用化测试（已废弃）

以下测试针对 2026-08-11 的变更 2（模型配置通用化）。变更 3（结构与命名收口）后 `.env` 不再支持 `QWEN_*` 回退，这些测试仅作为历史参考保留。

### 前置条件

完成 Environment Setup，确保 `.env` 中至少有一组有效的 API key。

---

### 测试 A：仅使用旧 QWEN_* 配置（向后兼容）

1. 编辑 `.env`，**注释或删除**所有 `LLM_*`、`EMBEDDING_*`、`TTS_*` 开头的变量，只保留原有的 `QWEN_*` 变量：

```env
QWEN_API_KEY="你的真实key"
QWEN_MODEL="qwen-vl-plus-latest"
QWEN_TTS_MODEL="cosyvoice-v3-flash"
QWEN_TTS_VOICE="longanyang"
QWEN_EMBEDDING_MODEL="text-embedding-v4"
QWEN_EMBEDDING_DIMENSIONS="1024"
```

2. 启动应用：

```powershell
python -m uvicorn app.main:app --reload
```

3. 验证：
   - `/api/health` 返回 `{"status":"ok"}`
   - `/query` 页面输入测试查询（如 "我是王建国，编号P0003，手机号13800000003，请帮我查询最近一次就诊记录"），能正常返回回答
   - `/chat` 页面同样可正常对话

4. 预期结果：所有功能与改前一致，无报错。

---

### 测试 B：使用新 LLM_* / EMBEDDING_* / TTS_* 配置

1. 编辑 `.env`，**注释或删除**所有 `QWEN_*` 和 `DASHSCOPE_*` 开头的变量，改为使用新的通用变量（值可以与旧变量相同）：

```env
LLM_API_KEY="你的真实key"
LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL="qwen-vl-plus-latest"

EMBEDDING_API_KEY="你的真实key"
EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_MODEL="text-embedding-v4"
EMBEDDING_DIMENSIONS="1024"

TTS_API_KEY="你的真实key"
TTS_MODEL="cosyvoice-v3-flash"
TTS_VOICE="longanyang"
TTS_WEBSOCKET_URL="wss://dashscope.aliyuncs.com/api-ws/v1/inference"
```

2. 重启应用。

3. 验证：
   - `/api/health` 返回 `{"status":"ok"}`
   - `/query` 页面输入测试查询，能正常返回回答
   - `/chat` 页面可正常对话
   - 选择语音播报时，TTS 能生成 `speech_download_url` 且音频可播放
   - Agent smoke script 可正常运行：

   ```powershell
   python scripts/test_qwen_agent.py "我是王建国，编号是P0003，手机号是13800000003，请查询最近一次就诊记录"
   ```

4. 预期结果：行为与测试 A 完全一致，说明新变量名已生效。

---

### 测试 C：混合配置（新变量优先）

1. 编辑 `.env`，同时设置新旧变量但使用**不同的 model 值**来验证优先级：

```env
# 新变量（应被优先读取）
LLM_MODEL="qwen-plus"

# 旧变量（应被忽略，因为新变量已设置）
QWEN_MODEL="qwen-vl-plus-latest"
```

2. 重启应用，查看启动日志或运行 Agent 查询。

3. 预期结果：实际使用的模型是 `qwen-plus`（新变量），而非 `qwen-vl-plus-latest`（旧变量）。

---

### 验收标准

| # | 标准 | 测试 |
|---|---|---|
| 1 | 只使用旧 QWEN_* 配置，原有 Agent 查询仍可运行 | A |
| 2 | 改用新的 LLM_* 配置，普通 Agent 查询仍可运行 | B |
| 3 | Embedding 写入/检索不因变量名变更导致启动失败 | A + B |
| 4 | TTS 选择语音播报时仍能生成 speech_download_url | B |
| 5 | /api/health、/query、/chat 仍可访问 | A + B |

---

## SSE 流式输出测试（2026-08-12）

### 前置条件

1. 完成 Environment Setup，并配置有效的 `LLM_*`；测试语音时还需有效的 `TTS_*`。
2. 在 `E:\patient-Agent\Agent` 启动服务：

```powershell
python -m uvicorn app.main:app --reload
```

### 测试 1：SSE 协议与真实增量

在另一个 PowerShell 窗口运行：

```powershell
curl.exe -N -X POST "http://127.0.0.1:8000/api/agent/query/stream" `
  -H "Content-Type: application/json" `
  -d '{"query":"请简要说明复诊前要准备什么","images":[],"debug_planner":false,"enable_speech":false,"speech_voice":"longanyang","speech_format":"mp3"}'
```

预期：

- 响应头 `Content-Type` 为 `text/event-stream`，并包含 `Cache-Control: no-cache`、`X-Accel-Buffering: no`。
- 首先出现 `event: status`，数据为 `{"stage":"planning"}`。
- 如果 Agent 调用工具，会按真实时序出现 `{"stage":"tool","status":"started","name":"安全中文名称"}` 和对应的 `completed`；工具异常时为 `failed`。
- 最终回答由多个模型原生 `event: delta` 事件逐步到达，而不是等待完整答案后一次返回。
- 每个事件中的 `data:` 都是合法 JSON，中文不是 `\uXXXX` 转义，并以空行分隔。
- 最后一个业务事件是 `event: done`；其中 `answer` 等于所有 `delta.text` 顺序拼接后的完整文本，且包含 `tool_outputs`、`planner_debug: null` 和语音字段。

故障排查：

- PowerShell 的 `curl` 可能是别名，请明确使用 `curl.exe`；`-N` 用于关闭客户端输出缓冲。
- 如果只收到 `error`，检查服务端日志中的异常类型以及 `LLM_*` 配置；SSE 数据不应出现 Key、堆栈或内部提示词。
- 如果反向代理后集中返回所有文本，确认代理没有覆盖 `X-Accel-Buffering: no`，并关闭代理响应缓冲。

### 测试 2：工具阶段与患者查询

请求体中的 `query` 改为：

```text
我是王建国，编号是P0003，手机号是13800000003，请查询最近一次就诊记录
```

预期：

- 收到 `planning` 状态。
- 至少收到身份验证或就诊记录查询的 `tool / started` 和 `tool / completed` 状态，事件中只公开安全中文名称，不包含内部函数名、参数、结果、内部计划或提示词。
- 最终 `delta` 前收到 `{"stage":"generating"}`。
- `done.tool_outputs` 包含实际工具结果，回答不编造患者记录。
- `done.planner_debug` 始终为 `null`，即使请求体传入 `debug_planner: true`。

### 测试 3：聊天页逐段渲染

打开 `http://127.0.0.1:8000/chat`，发送普通文本问题。

预期：

- 浏览器请求为 `POST /api/agent/query/stream`，请求体仍是 JSON。
- 页面右上角只显示“回复中”，完成后变为“已完成”；细分阶段显示在本轮助手消息底部自动展开的“执行过程”内。
- 助手气泡在请求结束前持续增加文本；中文字符完整，不出现乱码或半个字符。
- 完成后同一个助手气泡显示最终答案，“执行过程”自动折叠，不新增重复回答气泡，也不显示 `tool_outputs` 原始 JSON。

### 测试 4：图片 + POST 流式请求

在聊天页选择一张测试图片，再发送：

```text
请结合这张图片做说明
```

预期：

- 请求仍发送到流式端点，JSON 的 `images` 中包含 Base64 和 MIME type。
- 页面先显示本地图片预览，再逐段显示模型回答。
- 流式解析不会因图片请求体较大而丢事件或重复内容。

### 测试 5：TTS 在 done 前完成

在聊天页选择非 `none` 的音色并发送问题。

预期：

- 文本 `delta` 先逐段显示；文本完成后等待非流式 TTS。
- `done` 到达时包含 `speech_download_url`、`speech_mime_type`、`speech_model` 和 `speech_voice`。
- 页面在同一个助手气泡中出现可播放的 MP3 控件。
- `done` 之后没有新的业务事件。

### 测试 6：记忆收尾与原接口回归

使用可解析到测试患者的查询完成一次流式请求，然后检查短期记忆接口；再调用原接口：

```powershell
curl.exe "http://127.0.0.1:8000/api/memory/conversations?patient_id=3&limit=2"

curl.exe -X POST "http://127.0.0.1:8000/api/agent/query" `
  -H "Content-Type: application/json" `
  -d '{"query":"请简要说明复诊前要准备什么","images":[],"debug_planner":false,"enable_speech":false,"speech_voice":"longanyang","speech_format":"mp3"}'
```

预期：

- 收到流式 `done` 时，本轮 user/assistant 短期记忆已保存；达到 10 条消息的触发点时，长期记忆刷新已完成。
- 原 `POST /api/agent/query` 仍返回单个 JSON，字段和原有行为不变。

### 测试 7：安全错误事件

在隔离测试环境中临时使用无效模型配置，或发送模型明确拒绝的内容，然后调用流式端点。

预期：

- HTTP 流建立后，以 `event: error` 和 `{"message":"可展示的错误"}` 结束，不返回服务端堆栈、API Key、Base URL 或内部提示词。
- 页面保留已经收到的部分文本（如果有），并显示安全的“请求失败”或“请求中断”提示。
- 数据库 Session 被关闭，后续正常请求仍可使用数据库。

### 验收标准

| # | 标准 | 测试 |
|---|---|---|
| 1 | SSE 头、事件 JSON、空行边界和中文编码正确 | 1 |
| 2 | Planner/工具阶段可见，但 CoT、内部提示词和敏感错误不可见 | 1、2、7 |
| 3 | 最终答案来自模型原生流并与 `done.answer` 一致 | 1 |
| 4 | 聊天页支持 POST JSON、图片和跨网络分片解析 | 3、4 |
| 5 | TTS、对话记忆和长期记忆触发在 `done` 前完成 | 5、6 |
| 6 | 原非流式接口的行为和响应格式保持不变 | 6 |

---

## SSE 执行过程展示测试（2026-08-12，等待人工验收）

本节验证 `/chat` 展示的是可审计的真实业务步骤，而不是模型内部思维链。测试时声音选择“无”，避免 TTS 等待干扰对流式过程的观察。

### 前置条件

1. 配置有效的 `LLM_*`，并按前文步骤启动服务。
2. 打开 `http://127.0.0.1:8000/chat`。
3. 打开浏览器开发者工具的 Network 面板，保留本轮 `/api/agent/query/stream` 请求以便检查 SSE。

### 测试 1：无工具回答

声音选择“无”，输入：

```text
请分五点详细说明高血压患者的日常注意事项，每点至少三句话。
```

预期：

- 本轮助手消息创建时，其底部同步出现并自动展开“执行过程”。
- 先显示“正在理解并规划问题”；收到 `generating` 后，该步骤变为“已完成理解并规划问题”，并显示“正在生成最终回答”。
- 助手正文只逐段显示最终回答，不显示 Planner、Prompt、模型草稿或逐字思考。
- 右上角始终只显示“回复中”，完成后变为“已完成”，不显示工具名或细分阶段。
- 收到 `done` 后“生成最终回答”变为完成，执行过程自动折叠，标题为“执行完成，共 2 个步骤”。
- 点击折叠标题可重新展开查看两条步骤。

### 测试 2：工具调用

声音选择“无”，输入：

```text
我是王建国，编号是 P0003，手机号是 13800000003，请查询最近一次就诊记录并总结重点。
```

预期：

- 实时依次看到规划、患者身份验证、就诊记录查询和生成最终回答；实际工具选择仍以 Agent 返回为准，不制造未执行的步骤。
- 工具开始时显示“正在验证患者身份”或“正在查询就诊记录”；真实工具返回后，同一条步骤更新为“已完成验证患者身份”或“已完成查询就诊记录”，不重复计算开始/完成两条。
- SSE 中工具事件只包含安全中文名称，例如：

  ```text
  event: status
  data: {"stage":"tool","status":"started","name":"验证患者身份"}

  event: status
  data: {"stage":"tool","status":"completed","name":"验证患者身份"}
  ```

- 页面执行过程不显示 `verify_patient_identity`、`get_patient_visit_records` 等内部函数名，也不显示手机号、工具参数、原始返回 JSON、Prompt 或 `planner_debug`。
- 最终回答继续通过 `delta` 逐段显示；`done` 后执行过程自动折叠，标题中的 N 等于规划 + 实际工具数 + 生成回答。
- 手动展开后主要内容仍是安全步骤摘要，不出现 `done.tool_outputs` 的原始 JSON。

### 测试 3：异常与兼容

#### 3A. 异常展示

在隔离测试环境中让工具或模型流产生异常，不修改生产数据。

预期：

- 工具失败时，先收到对应的 `tool / failed` 状态，再收到安全的 `error` 事件。
- 本轮折叠区标题显示“执行失败”并保持展开；已完成步骤继续显示完成，当前失败步骤显示失败。
- 页面正文可以保留异常前已收到的最终回答片段，但不显示堆栈、Key、内部配置或敏感数据。
- 右上角显示“请求失败”。

#### 3B. 兼容性回归

分别检查：

1. `/query` 仍调用 `POST /api/agent/query`，一次返回完整 JSON；Query 页面没有执行过程 UI。
2. `/chat` 仍调用 `POST /api/agent/query/stream`，使用 `fetch` POST + `ReadableStream`，没有改成 `EventSource`。
3. 在 `/chat` 选择图片后发送，图片预览和流式回答保持正常。
4. 选择一个音色再发送，最终 `done` 仍补齐音频控件；本项仅验证兼容，观察步骤流时仍建议选择“无”。
5. 点击“清空会话”，消息、图片选择和状态恢复原有空闲状态。

### 验收记录

| 测试 | 结果 | 备注 |
|---|---|---|
| 无工具回答 | 待人工验收 | 重点检查 2 个步骤和完成自动折叠 |
| 工具调用 | 待人工验收 | 重点检查真实开始/完成时序和敏感信息边界 |
| 异常与兼容 | 待人工验收 | 重点检查失败保持展开、Query/图片/TTS/清空回归 |

---

## SSE 等待体验测试（2026-08-13，等待人工验收）

本节验证模型等待期间页面不再静止：进行中步骤有呼吸动画、等待秒数每秒变化、`done` 自动折叠并保留真实耗时、`error` 保留步骤不折叠、计时器在清空和连续两轮时正确清理。声音选择“无”，避免 TTS 等待干扰观察。

### 前置条件

1. 配置有效的 `LLM_*`，按前文步骤启动服务。
2. 打开 `http://127.0.0.1:8000/chat`。
3. 打开浏览器开发者工具 Network 面板，保留本轮 `/api/agent/query/stream` 请求。

### 测试 1：等待秒数与呼吸动画

声音选择“无”，输入：

```text
我是王建国，编号是 P0003，手机号是 13800000003，请查询最近一次就诊记录并总结重点。
```

预期：

- 助手消息底部自动展开“执行过程”，先显示“正在理解并规划问题”，其下方的次要说明显示“模型正在判断需要调用哪些业务能力”。
- 该步骤旁边的等待秒数从 1 秒开始每秒递增（“正在理解并规划问题 · 8 秒”等形式），页面不会看起来静止卡住。
- 进行中步骤的圆点标记有轻微的呼吸式脉冲动画。
- 真正收到工具事件后，才依次出现“验证患者身份”“查询就诊记录”等步骤；工具步骤同样有呼吸动画和等待秒数。
- 页面不显示手机号、工具参数、原始结果、Prompt 或模型思维链。

### 测试 2：完成自动折叠与真实耗时

继续上一测试，等待请求完成。

预期：

- 收到 `done` 后，所有计时停止，进行中步骤变为“已完成”，执行过程自动折叠，标题为“执行完成，共 N 个步骤”。
- 页面主要显示最终回答（逐段出现）。
- 手动展开后，每条已完成步骤显示真实耗时（例如“已完成患者身份验证 · 3 秒”），而不是伪造的进度百分比。

### 测试 3：异常停止计时并保留步骤

在隔离测试环境中让工具或模型流产生异常（不修改生产数据）。

预期：

- 收到 `error` 后，所有计时立即停止，等待秒数不再变化。
- 已完成步骤继续显示完成；当前失败步骤显示“失败”并带耗时。
- 折叠标题显示“执行失败”，执行过程保持展开、不自动折叠。
- 页面不显示堆栈、Key、内部配置或敏感数据。

### 测试 4：清空会话与连续两轮

1. 在请求进行中点击“清空会话”。
2. 再连续发送两轮消息（等第一轮完成后再发第二轮）。

预期：

- 清空会话后，旧步骤和旧计时器不再更新，页面回到空闲状态。
- 连续两轮消息的计时器互不串扰，第一轮完成折叠后，第二轮独立开始计时，没有残留的秒数跳动或上一轮状态。

### 测试 5：/query 非流式回归

打开 `http://127.0.0.1:8000/query`，输入同一查询。

预期：

- 仍调用 `POST /api/agent/query`，一次返回完整 JSON，行为与之前一致，没有执行过程 UI 或等待计时。

### 验收记录

| 测试 | 结果 | 备注 |
|---|---|---|
| 等待秒数与呼吸动画 | 待人工验收 | 重点检查秒数递增、呼吸动画、planning 固定说明 |
| 完成自动折叠与真实耗时 | 待人工验收 | 重点检查折叠、展开后耗时真实 |
| 异常停止计时并保留步骤 | 待人工验收 | 重点检查计时停止、不折叠 |
| 清空会话与连续两轮 | 待人工验收 | 重点检查旧计时器清理、互不串扰 |
| /query 非流式回归 | 待人工验收 | 重点检查原接口不变 |

---

## SSE 主动取消与清空防竞态测试（2026-08-13，等待人工验收）

本节验证“清空会话”会真正中断当前浏览器 fetch，并隔离旧请求的后续事件。清空只影响当前页面，不应检查或修改数据库、长期记忆、患者资料和 FAISS 数据。观察流式行为时声音选择“无”。

### 测试 1：生成期间清空

1. 打开 `http://127.0.0.1:8000/chat`，声音选择“无”。
2. 输入一个较长问题并发送。
3. 等待执行步骤开始计时后立即点击“清空会话”。
4. 保持页面不操作并等待至少 30 秒。

预期：

- 点击后当前 fetch 立即被浏览器中断，消息、图片选择、输入内容和执行过程立即清空。
- 所有计时器停止，发送按钮立即恢复可用，右上角立即显示“空闲”。
- 30 秒内及之后状态都保持“空闲”，不能变成“已完成”或“请求失败”。
- 旧消息、旧执行步骤和“请求失败/请求中断”文本均不能重新出现。
- 清空操作不调用任何数据库或记忆删除接口。

### 测试 2：清空后立即发起新一轮

1. 第一轮执行期间点击“清空会话”。
2. 不等待旧网络请求结束，立即输入第二个问题并发送。

预期：

- 第二轮只显示自己的步骤、计时和流式回答。
- 第一轮的 `status`、`delta`、`done`、`error` 不得写入第二轮消息。
- 第一轮的 `catch` 不显示错误，第一轮的 `finally` 不得提前启用发送按钮或改变第二轮状态。
- 第二轮执行期间发送按钮保持禁用，完成后才恢复；执行过程正常自动折叠，状态变为“已完成”。

### 测试 3：正常请求回归

不清空会话，正常发送一个问题并等待完成。

预期：

- 等待秒数与呼吸动画正常。
- 最终回答通过 `delta` 逐段出现。
- `done` 后执行过程自动折叠，右上角变为“已完成”，发送按钮恢复可用。
- 普通服务器错误仍按原逻辑显示“请求失败”；只有用户主动取消静默结束。

### 测试 4：Query 回归

打开 `http://127.0.0.1:8000/query` 并发送单轮查询。

预期：

- 仍调用 `POST /api/agent/query`，一次返回完整答案。
- Query 页面行为完全不变，没有 SSE 取消或执行过程 UI。

### 验收记录

| 测试 | 结果 | 备注 |
|---|---|---|
| 生成期间清空 | 待人工验收 | 重点观察等待 30 秒后仍为空闲 |
| 清空后立即发起新一轮 | 待人工验收 | 重点观察旧事件和旧 finally 不影响第二轮 |
| 正常请求回归 | 待人工验收 | 重点观察计时、动画、流式文本和完成折叠 |
| Query 回归 | 待人工验收 | 重点确认仍为非流式普通接口 |

---

## LangGraph 等价迁移测试（2026-08-13，等待人工验收）

本节验证 `PatientAgent` 内部手写 `while` 工具循环替换为 LangGraph `StateGraph` 后，对外行为与迁移前一致。迁移只改编排层，Prompt、工具、模型、记忆、TTS 和前端均未改。观察流式行为时声音选择“无”。

### 前置条件

1. 安装依赖（新增 `langgraph`）：

   ```powershell
   pip install -r requirements.txt
   ```

2. 配置有效的 `LLM_*`（测试语音时还需 `TTS_*`）。
3. 在 `E:\patient-Agent\Agent` 启动服务：

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

### 测试 1：启动与健康检查

打开：

```text
http://127.0.0.1:8000/api/health
```

预期：

- 终端不出现 `ImportError` / `ModuleNotFoundError`（尤其是 `langgraph`）。
- 返回 `{"status":"ok"}`。

### 测试 2：非流式回归

打开 `http://127.0.0.1:8000/query`，输入：

```text
我是王建国，编号是 P0003，手机号是 13800000003，请查询最近一次就诊记录并总结重点。
```

预期：

- 仍调用 `POST /api/agent/query`，一次返回完整 JSON。
- 工具结果与回答行为与迁移前一致，不编造患者记录。

### 测试 3：SSE 无工具

打开 `http://127.0.0.1:8000/chat`，声音选择“无”，输入：

```text
高血压日常注意事项
```

预期：

- 事件顺序为 `planning` → `generating` → 多个 `delta` → `done`。
- 回答逐段出现，无工具事件。

### 测试 4：SSE 工具调用

在 `/chat` 输入：

```text
我是王建国，编号是 P0003，手机号是 13800000003，请查询最近一次就诊记录并总结重点。
```

预期：

- 真实显示身份验证、记录查询的开始/完成状态，顺序为 `planning` → 工具 `started`/`completed` → `generating` → `delta` → `done`。
- 结果基于真实工具返回，不编造，SSE 不泄露工具参数、原始结果、Prompt、Planner 内容或思维链。

### 测试 5：主动取消

在回答过程中点击“清空会话”，随后立即发送新问题。

预期：

- 清空后立即空闲，旧请求不能重新写回；新问题不串轮，行为与迁移前一致。

### 测试 6：图片与 TTS

分别上传图片、选择一个音色（非 none）发送问题。

预期：

- 图片预览与模型回答正常；TTS 仍返回 `speech_download_url`，音频可播放。

### 验收记录

| 测试 | 结果 | 备注 |
|---|---|---|
| 启动与健康检查 | 待人工验收 | 重点检查 langgraph 可导入 |
| 非流式回归 | 待人工验收 | 重点检查 `/query` 行为与迁移前一致 |
| SSE 无工具 | 待人工验收 | 重点检查 planning → generating → delta → done |
| SSE 工具调用 | 待人工验收 | 重点检查真实开始/完成状态且不泄露敏感信息 |
| 主动取消 | 待人工验收 | 重点检查清空后空闲、不串轮 |
| 图片与 TTS | 待人工验收 | 重点检查图片与语音不受影响 |

---

## MCP 工具层一期测试（2026-08-13，等待人工验收）

本节验证 `PatientAgent` 已改为通过真实 MCP client/server 协议（本地 stdio `app.mcp_server`）调用四个业务工具，取代对 `mcp_tool_service` 的直接调用。观察流式行为时声音选择“无”。

### 前置条件

1. 确认依赖安装：`mcp` 版本满足 `>=1.12.0,<2.0.0`（当前环境 `mcp 1.12.4`），`langgraph 1.2.11` 可导入。
2. 本仓库当前唯一的虚拟环境是仓库根目录的 `.venv312`（`E:\patient-Agent\.venv312`）；以下命令从 `E:\patient-Agent\Agent` 运行，解释器用 `..\.venv312\Scripts\python.exe`。
3. 无需手工启动第二个服务、不占用新端口：`MCPToolClient` 会通过 `sys.executable -m app.mcp_server` 自行拉起并关闭 stdio 子进程。

### 测试 1：MCP 工具发现

在 `E:\patient-Agent\Agent` 运行一行 Python 命令：

```powershell
..\.venv312\Scripts\python.exe -c "from app.mcp_client import MCPToolClient; print([t['name'] for t in MCPToolClient().list_tools()])"
```

预期：

- 恰好返回四个白名单工具（顺序不保证）：

  ```text
  ['verify_patient_identity', 'get_patient_profile', 'get_patient_medical_cases', 'get_patient_visit_records']
  ```

- 每个工具的 schema 为普通 JSON Schema（`type`/`properties`/`required`），不含 `anyOf`/`title`/`default`；例如 `verify_patient_identity` 的 `required` 为 `["patient_code"]`，`get_patient_visit_records` 含可选 `limit`（integer）。
- 终端会出现类似 `Processing request of type ListToolsRequest` 的 server 日志，证明发现经过 MCP server。

### 测试 2：MCP 单工具调用

```powershell
..\.venv312\Scripts\python.exe -c "import json; from app.mcp_client import MCPToolClient; print(json.dumps(MCPToolClient().call_tool('verify_patient_identity', {'patient_code':'P0003','phone':'13800000003'}), ensure_ascii=False))"
```

预期：

- 返回结构化 dict，例如：

  ```json
  {"verified": true, "reason": "ok", "patient": {"id": 3, "patient_code": "P0003", "full_name": "王建国", "gender": "male", "phone_masked": "138****0003", "id_number_masked": "3101********1234"}}
  ```

- 手机号/身份证以掩码返回，不输出明文。
- 终端出现 `Processing request of type CallToolRequest` 日志，确认调用经过 MCP 协议而非直接 service。
- 用白名单外工具名调用（如 `call_tool('not_a_tool', {})`）会抛 `MCPToolError`，且不拉起 server 子进程。

### 测试 3：`/query` 回归

启动服务（见“Start The App”）后打开 `http://127.0.0.1:8000/query`，输入：

```text
我是王建国，编号是 P0003，手机号是 13800000003，请查询最近一次就诊记录。
```

预期：

- 仍调用 `POST /api/agent/query`，一次返回完整 JSON。
- 工具结果与回答行为与迁移前一致，基于真实就诊记录、不编造。
- `/api/health` 返回 `{"status":"ok"}`，无 import error。

### 测试 4：`/chat` 回归

打开 `http://127.0.0.1:8000/chat`，声音选择“无”，输入同一查询。

预期：

- 事件顺序为 `planning` → 工具 `started`/`completed` → `generating` → 多个 `delta` → `done`。
- 工具步骤只显示安全中文名称（如“验证患者身份”“查询就诊记录”），不出现内部函数名、手机号、工具参数、原始返回 JSON、Prompt 或 `planner_debug`。
- 最终回答逐段出现，`done.tool_outputs` 含实际工具结果。

### 测试 5：主动取消

在 `/chat` 回答过程中点击“清空会话”，随后立即发送新问题。

预期：

- 清空后立即空闲，旧请求不写回，旧 `done/error/catch/finally` 不影响新一轮。
- 行为与迁移前一致（MCP 工具层不改变取消与防竞态逻辑）。

### 测试 6：MCP 异常

在不修改业务数据的前提下模拟 MCP 失败，例如在隔离环境中临时把 `MCPToolClient` 指向一个不存在的 server 模块，或调用白名单外工具名。

预期：

- 显示安全的 `error` 事件，工具步骤标记为 `failed`。
- 错误信息不泄露患者参数、API Key、完整工具结果或服务端堆栈；日志只记录异常类型。
- 数据库 Session 正常关闭，后续正常请求仍可用。

### 验收记录

| 测试 | 结果 | 备注 |
|---|---|---|
| MCP 工具发现 | 待人工验收 | 重点检查恰好 4 个白名单工具与干净 schema |
| MCP 单工具调用 | 待人工验收 | 重点检查结构化结果、掩码字段、经过 MCP |
| `/query` 回归 | 待人工验收 | 重点检查工具结果与迁移前一致 |
| `/chat` 回归 | 待人工验收 | 重点检查 planning → tool → generating → delta → done |
| 主动取消 | 待人工验收 | 重点检查清空后空闲、不串轮 |
| MCP 异常 | 待人工验收 | 重点检查安全 error、步骤失败、不泄露 |

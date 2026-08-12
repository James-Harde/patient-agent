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

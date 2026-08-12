# Manual Tests

Run commands from `E:\patient-Agent\Agent` unless noted.

## Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with a valid Qwen/DashScope key before testing Agent, embedding, image, or speech features.

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

## 模型配置通用化测试

本测试验证新的通用环境变量（`LLM_*` / `EMBEDDING_*` / `TTS_*`）和旧的 `QWEN_*` 变量都能正常工作。

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

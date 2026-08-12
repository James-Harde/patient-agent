# Development Log

## 2026-08-12

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

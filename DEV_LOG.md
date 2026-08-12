# Development Log

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

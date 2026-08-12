# Development Status

## Current Goal

结构与命名收口 — 把模型调用、配置读取、语音调用、Agent 编排、RAG 检索放到更清晰的位置，去掉业务代码中的 qwen_* 文件名和 Qwen* 类名绑定。

## Working Agreement

- Keep the existing native HTML/CSS/JavaScript frontend; do not migrate to React.
- Use manual acceptance tests as the primary validation method.
- Every feature or replacement must include test inputs, expected behavior, and troubleshooting notes.
- Keep business logic changes scoped and update this file plus `DEV_LOG.md` after each task.

## Roadmap

| Order | Task | Status | Notes |
|---:|---|---|---|
| 0 | Coordination docs and manual tests | Done | Created `DEV_STATUS.md`, `DEV_LOG.md`, and `MANUAL_TESTS.md` |
| 1 | Generalize model config names | Done | Add `LLM_*`, `EMBEDDING_*`, and `TTS_*` with `QWEN_*` fallback |
| 2 | 结构与命名收口 | Done | Move/rename files, remove qwen_* naming, centralize config in llm_env.py |
| 3 | SSE streaming output | Pending | Stream answer/progress to the existing frontend |
| 4 | LangGraph orchestration | Pending | Replace the handwritten Agent loop with graph nodes |
| 5 | MCP tool-layer completion | Pending | Make tools callable through a real MCP client/server path |
| 6 | LangChain componentization | Pending | Standardize model, tool, retriever, and vector-store adapters where useful |
| 7 | Security boundary layer | Pending | Add auth, patient data isolation, tool allowlists, and log redaction |
| 8 | Docker Compose | Pending | Add local service orchestration after external services are needed |
| 9 | Milvus hybrid RAG | Pending | Replace FAISS with dense + BM25 + RRF hybrid retrieval |
| 10 | PostgreSQL migration | Pending | Move from SQLite when multi-user or long-running deployment is required |

## Active Task

(None — 结构与命名收口 is complete.)

## Completed

- `AGENTS.md` contributor guide exists at repository root.
- `DEV_STATUS.md`, `DEV_LOG.md`, and `MANUAL_TESTS.md` exist at repository root.
- Model configuration generalization: `LLM_*`, `EMBEDDING_*`, `TTS_*` env vars with `QWEN_*` / `DASHSCOPE_*` fallback.
- 结构与命名收口：文件移动/重命名、类名去 Qwen 化、集中配置、import 同步。

## Not Started

- SSE streaming.
- LangGraph migration.
- MCP client/server integration.
- Milvus, Docker Compose, and PostgreSQL infrastructure work.

## Blockers

- None.

## Next Step

人工验收通过后再讨论是否进入 SSE。

## Current Manual Acceptance Entry

Use `MANUAL_TESTS.md` to verify the existing app before and after each change.

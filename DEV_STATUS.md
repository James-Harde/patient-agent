# Development Status

## Current Goal

修复 `/chat` 清空会话后的旧 SSE 请求竞态，并支持通过清空会话主动取消当前回答。

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
| 3 | SSE streaming output | 已实现，等待人工验收 | Native LLM deltas, safe execution status events, SSE API, and collapsible per-message process UI |
| 4 | LangGraph orchestration | Pending | Replace the handwritten Agent loop with graph nodes |
| 5 | MCP tool-layer completion | Pending | Make tools callable through a real MCP client/server path |
| 6 | LangChain componentization | Pending | Standardize model, tool, retriever, and vector-store adapters where useful |
| 7 | Security boundary layer | Pending | Add auth, patient data isolation, tool allowlists, and log redaction |
| 8 | Docker Compose | Pending | Add local service orchestration after external services are needed |
| 9 | Milvus hybrid RAG | Pending | Replace FAISS with dense + BM25 + RRF hybrid retrieval |
| 10 | PostgreSQL migration | Pending | Move from SQLite when multi-user or long-running deployment is required |

## Active Task

SSE 主动取消修复已实现：清空会话会中断当前 fetch、使旧 requestId 失效并清理计时器；等待按 `MANUAL_TESTS.md` 进行人工验收。

## Completed

- `AGENTS.md` contributor guide exists at repository root.
- `DEV_STATUS.md`, `DEV_LOG.md`, and `MANUAL_TESTS.md` exist at repository root.
- Model configuration generalization: `LLM_*`, `EMBEDDING_*`, `TTS_*` env vars with `QWEN_*` / `DASHSCOPE_*` fallback.
- 结构与命名收口：文件移动/重命名、类名去 Qwen 化、集中配置、import 同步。
- SSE 流式输出已实现、待人工验收：模型原生文本流、共享 Planner/工具执行循环、`POST /api/agent/query/stream`，以及每条助手消息内可折叠的安全执行过程。
- SSE 执行过程等待体验已实现、待人工验收：进行中步骤呼吸动画、每秒等待计时、planning 固定安全说明、`done` 自动折叠、`error` 保留步骤不折叠，以及清空/下一轮/失败路径的计时器清理。
- SSE 主动取消与防竞态已实现、待人工验收：`AbortController` 中断当前流，generation/requestId 隔离旧事件，清空后保持空闲，快速重发时旧 `catch/finally` 不污染新一轮。

## Not Started

- LangGraph migration.
- MCP client/server integration.
- Milvus, Docker Compose, and PostgreSQL infrastructure work.

## Blockers

- None.

## Next Step

按 `MANUAL_TESTS.md` 完成生成期间清空、清空后立即重发、正常请求和 `/query` 回归测试；主动取消修复当前为“已实现，等待人工验收”，不得开始 LangGraph 阶段。

## Current Manual Acceptance Entry

Use `MANUAL_TESTS.md` to verify the existing app before and after each change.

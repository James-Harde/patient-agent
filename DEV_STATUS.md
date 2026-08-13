# Development Status

## Current Goal

完成 MCP 工具层一期：让 LangGraph Agent 通过真实 MCP client/server 协议调用现有四个业务工具，替换当前对 `mcp_tool_service` 的直接调用。

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
| 3 | SSE streaming output | Done | Native LLM deltas, safe execution status events, SSE API, and collapsible per-message process UI |
| 4 | LangGraph orchestration | 已实现，等待人工验收 | Replace the handwritten Agent loop with graph nodes |
| 5 | MCP tool-layer completion | 已实现，等待人工验收 | Make tools callable through a real MCP client/server path |
| 6 | LangChain componentization | Pending | Standardize model, tool, retriever, and vector-store adapters where useful |
| 7 | Security boundary layer | Pending | Add auth, patient data isolation, tool allowlists, and log redaction |
| 8 | Docker Compose | Pending | Add local service orchestration after external services are needed |
| 9 | Milvus hybrid RAG | Pending | Replace FAISS with dense + BM25 + RRF hybrid retrieval |
| 10 | PostgreSQL migration | Pending | Move from SQLite when multi-user or long-running deployment is required |

## Active Task

MCP 工具层一期已实现：新增 `Agent/app/mcp_client.py`（同步 `MCPToolClient`，封装官方 stdio client 接口），`PatientAgent` 不再直接 import 或调用 `mcp_tool_service`，改为通过 `MCPToolClient.list_tools()` 生成工具 schema、通过 MCP 适配器调用四个白名单业务工具（`verify_patient_identity` / `get_patient_profile` / `get_patient_medical_cases` / `get_patient_visit_records`）。`mcp_server.py` 保持不变，仅负责协议暴露与数据库 Session 生命周期。等待按 `MANUAL_TESTS.md` 的“MCP 工具层一期测试”进行人工验收。

## Completed

- `AGENTS.md` contributor guide exists at repository root.
- `DEV_STATUS.md`, `DEV_LOG.md`, and `MANUAL_TESTS.md` exist at repository root.
- Model configuration generalization: `LLM_*`, `EMBEDDING_*`, `TTS_*` env vars with `QWEN_*` / `DASHSCOPE_*` fallback.
- 结构与命名收口：文件移动/重命名、类名去 Qwen 化、集中配置、import 同步。
- SSE 流式输出已完成：模型原生文本流、共享 Planner/工具执行循环、`POST /api/agent/query/stream`，以及每条助手消息内可折叠的安全执行过程。
- SSE 执行过程等待体验已完成：进行中步骤呼吸动画、每秒等待计时、planning 固定安全说明、`done` 自动折叠、`error` 保留步骤不折叠，以及清空/下一轮/失败路径的计时器清理。
- SSE 主动取消与防竞态已完成：`AbortController` 中断当前流，generation/requestId 隔离旧事件，清空后保持空闲，快速重发时旧 `catch/finally` 不污染新一轮。
- LangGraph 编排迁移已实现、待人工验收：`StateGraph` 替换手写工具循环，节点 `planner` / `agent_decision` / `tools` / `finalizer`，`run()` / `run_stream()` 对外行为不变。具体单项测试结果未单独确认，见 `MANUAL_TESTS.md`。
- MCP 工具层一期已实现、待人工验收：新增同步 `MCPToolClient`（stdio transport + 官方 client 接口），`PatientAgent` 通过 MCP 发现工具 schema 并经 MCP 适配器调用四个白名单工具，移除对 `mcp_tool_service` 的直接引用。真实 MCP 往返（`list_tools` / `verify_patient_identity`）已在本机验证通过。

## Not Started

- Milvus, Docker Compose, and PostgreSQL infrastructure work.
- LangChain componentization (task 6).

## Blockers

- None.

## Next Step

按 `MANUAL_TESTS.md` 的“MCP 工具层一期测试”完成六项人工验收：MCP 工具发现、MCP 单工具调用、`/query` 回归、`/chat` 回归、主动取消、MCP 异常；MCP 阶段当前为“已实现，等待人工验收”，不得开始 LangChain 组件化或下一阶段。

## Current Manual Acceptance Entry

Use `MANUAL_TESTS.md` to verify the existing app before and after each change.

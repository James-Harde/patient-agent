# Development Status

## Current Goal

Prepare the repository for staged secondary development of the patient assistant Agent without changing application behavior yet.

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
| 2 | SSE streaming output | Pending | Stream answer/progress to the existing frontend |
| 3 | LangGraph orchestration | Pending | Replace the handwritten Agent loop with graph nodes |
| 4 | MCP tool-layer completion | Pending | Make tools callable through a real MCP client/server path |
| 5 | LangChain componentization | Pending | Standardize model, tool, retriever, and vector-store adapters where useful |
| 6 | Security boundary layer | Pending | Add auth, patient data isolation, tool allowlists, and log redaction |
| 7 | Docker Compose | Pending | Add local service orchestration after external services are needed |
| 8 | Milvus hybrid RAG | Pending | Replace FAISS with dense + BM25 + RRF hybrid retrieval |
| 9 | PostgreSQL migration | Pending | Move from SQLite when multi-user or long-running deployment is required |

## Active Task

SSE streaming output — stream answer/progress to the existing frontend.

## Completed

- `AGENTS.md` contributor guide exists at repository root.
- `DEV_STATUS.md`, `DEV_LOG.md`, and `MANUAL_TESTS.md` exist at repository root.
- Model configuration generalization: `LLM_*`, `EMBEDDING_*`, `TTS_*` env vars with `QWEN_*` / `DASHSCOPE_*` fallback.

## Not Started

- SSE streaming.
- LangGraph migration.
- MCP client/server integration.
- Milvus, Docker Compose, and PostgreSQL infrastructure work.

## Blockers

- None.

## Next Step

Start SSE streaming output task:

```text
Stream answer/progress from the Agent to the existing frontend via Server-Sent Events.
```

## Current Manual Acceptance Entry

Use `MANUAL_TESTS.md` to verify the existing app before and after each change.

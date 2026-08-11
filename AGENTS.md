# Repository Guidelines

## Project Structure & Module Organization

The application code lives in `Agent/`. Core FastAPI startup is in `Agent/app/main.py`, with routes in `Agent/app/api/routes.py`. Database setup and SQLAlchemy models are under `Agent/app/db/`; Pydantic request/response models are in `Agent/app/schemas/`; business logic belongs in `Agent/app/services/`; Qwen, speech, multimodal, and MCP agent integrations are in `Agent/app/llm/`. Static browser pages are served from `Agent/app/static/`. Runtime data, SQLite files, FAISS indexes, generated audio, and sample media live in `Agent/data/`. Project docs are in `Agent/docs/`, and helper scripts are in `Agent/scripts/`.

## Build, Test, and Development Commands

Run commands from `Agent/` unless noted.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

`uvicorn` starts the API and static pages at `http://127.0.0.1:8000`, including `/docs`, `/query`, and `/chat`. Seed local demo data with:

```powershell
sqlite3 data/patient_agent.db < scripts/seed_demo_data.sql
```

For an agent smoke test, use:

```powershell
python scripts/test_qwen_agent.py "your query"
```

## Coding Style & Naming Conventions

Use Python 3.12 style with 4-space indentation, type hints, and clear snake_case names for functions, variables, modules, and service methods. Keep FastAPI handlers thin: validate HTTP concerns in `app/api/`, place reusable business behavior in `app/services/`, and keep database models in `app/db/models.py`. Prefer Pydantic models for API payloads rather than raw dictionaries. JavaScript and CSS in `app/static/` should stay dependency-free unless a frontend build system is introduced.

## Testing Guidelines

No formal automated test suite is present yet. When changing API or agent behavior, run the app locally, check `/api/health`, inspect Swagger at `/docs`, and run the Qwen smoke script for affected flows. If adding tests, place them under `Agent/tests/`, name files `test_*.py`, and use pytest-style assertions.

## Commit & Pull Request Guidelines

This checkout does not include Git history, so no project-specific commit convention can be inferred. Use short, imperative commit subjects such as `Add memory event search validation`. Pull requests should summarize behavior changes, list local verification commands, reference related issues, and include screenshots for changes under `app/static/`.

## Security & Configuration Tips

Copy `Agent/.env.example` to `.env` and keep real Qwen/DashScope keys out of commits. Treat `Agent/data/` as runtime or sample data; avoid committing generated audio, FAISS indexes, SQLite changes, or patient-identifying records unless explicitly required.

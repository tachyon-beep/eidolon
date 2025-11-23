# Repository Guidelines

## Project Structure & Module Organization
- `src/eidolon/`: Python backend package. Notable areas: `agents/` (hierarchy), `analysis/` + `code_graph.py` (static analysis), `api/` (FastAPI routes), `planning/` (prompts/decomposition), `storage/` (SQLite layer), `cache/`, `metrics/`, `health/`, and `resilience/`. Entrypoint: `src/eidolon/main.py`.
- `frontend/`: Vue 3 + Vite UI with Pinia stores (`frontend/src/stores`), routed views (`frontend/src/views`), and shared components (`frontend/src/components`).
- `examples/`: Sample codebases for analysis demos; `docs/` and architecture notes (`HIERARCHICAL_AGENT_SYSTEM.md`, `AGENT_HIERARCHY.md`, etc.) capture design intent.
- `tests/`: New unit tests live here. Legacy scenario-style `test_*.py` at repo root are integration scripts (many async; some require LLM keys) and will be migrated over time.

## Build, Test, and Development Commands
- Sync deps with uv: `uv sync` (uses `pyproject.toml`). Activate env via `source .venv/bin/activate` or prefix commands with `uv run`.
- Run API locally: `uv run uvicorn eidolon.main:app --reload`. Export `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`/`OPENAI_BASE_URL` before exercising LLM flows.
- Frontend dev server: `cd frontend && npm install && npm run dev`; production bundle: `npm run build`.
- Quick checks: `uv run pytest tests` for new unit tests; legacy scenarios remain runnable via `uv run python test_full_pipeline.py` (LLM steps skip when keys are absent).

## Coding Style & Naming Conventions
- Python 3.10+ with 4-space indent, type hints, and async/await for I/O. Modules/files: snake_case; classes: PascalCase; functions/vars: snake_case.
- Keep FastAPI routes thin; push orchestration into `eidolon.agents` and state into Pydantic models under `eidolon.models`.
- Lint/type check with `uv run ruff check src` and `uv run mypy src` when available; reuse logging helpers from `eidolon.logging_config` (structured logs via structlog).
- Vue: Composition API with `<script setup>`; components PascalCase, stores in `frontend/src/stores`, routes in `frontend/src/router`, shared styles in `frontend/src/components`.

## Testing Guidelines
- Place new tests under `tests/` as `test_*.py`; keep them deterministic and guard LLM-dependent flows behind env checks (`OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`).
- Prefer `pytest` with `pytest.mark.asyncio` for async code; keep console output succinct and actionable.
- Add lightweight unit coverage for planners/parsers before end-to-end runs; include sample payloads and expected side effects (created files, cache writes).
- Run lint/compatibility coverage via `uv run python test_linting_agent.py`; full pipeline validation via `uv run python test_full_pipeline.py` once keys are configured.

## Commit & Pull Request Guidelines
- Use short, imperative subjects (examples from history: `Improve tool_calls dict handling 🔧`, `Force sequential tool calls for OpenRouter 🔧`); keep scope narrow.
- PRs should state intent, main directories touched, required env vars/migrations, and tests executed (`python test_linting_agent.py`, `npm run build`, etc.). Link issues/cards when present.
- Provide screenshots or GIFs for UI tweaks and sample request/response payloads for API changes. Avoid committing generated DB/cache artifacts.
- Keep secrets out of VCS; prefer `.env` or shell exports and document any new configuration keys.

## Security & Configuration Tips
- Required keys: `OPENROUTER_API_KEY` (and optional `OPENROUTER_BASE_URL`/`OPENROUTER_MODEL`) or `ANTHROPIC_API_KEY` for LLM-backed flows. Do not hardcode or log them.
- SQLite database `eidolon.db` is created at runtime in the working directory; exclude it from commits and reset it locally when schema changes.

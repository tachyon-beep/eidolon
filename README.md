# Eidolon — Hierarchical Agent System

Eidolon is a hierarchical code analysis and planning system. Agents operate at system, module, class, and function levels to review code, propose changes, and synthesize findings into actionable cards.

## What’s Inside

- **Backend (Python, FastAPI)** under `src/eidolon/`: agent orchestrators, planners, business analyst, code graph/context tools, caching, storage, resilience, metrics, API routes.
- **Frontend (Vue 3 + Vite)** under `frontend/`: UI for running analyses and viewing cards.
- **Docs** under `docs/`: architecture notes, historical test results, and archived reports (see `docs/ARCHIVE_NOTES.md`).
- **Tests** under `tests/`: extensive unit/integration coverage; LLM-gated integration tests live in `tests/integration` and skip when no API key. Legacy root `test_*.py` scripts are preserved in `legacy_tests/`.

## Getting Started (Backend)

1) Install deps with uv (Python 3.10+):

```bash
uv sync
```

2) Run API:

```bash
uv run uvicorn eidolon.main:app --reload
```

3) Env vars for LLM providers:

- `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
- `OPENAI_BASE_URL` (default `https://openrouter.ai/api/v1`)
- `OPENAI_MODEL` (default `gpt-4o-mini`)

4) Run tests:

```bash
uv run pytest tests          # unit + non-LLM integration
uv run pytest tests -m "llm" # LLM-gated integration (requires key)
```

## Getting Started (Frontend)

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Repository Layout

```
src/eidolon/
  agents/                # Agent orchestrators
  analysis/, code_graph.py, code_context_tools.py, design_context_tools.py
  planning/              # Decomposition, prompts, review loop
  business_analyst.py    # Requirements refinement
  linting_agent.py, specialist_agents.py
  test_generator.py, code_writer.py
  api/routes.py          # FastAPI routes
  storage/database.py    # SQLite persistence
  cache/cache_manager.py # Analysis result cache
  resilience/            # retry/timeout/rate limiter
  metrics/, health/      # Prometheus + health probes
frontend/                # Vue 3 UI
docs/                    # Architecture + archived reports
legacy_tests/            # Historical integration scripts (not collected)
```

## Key Features

- Hierarchical analysis (system → module → class → function) with card generation.
- Business Analyst layer for requirements refinement and subsystem targeting.
- Structured planning prompts, review loops, and specialist agents (security, testing, etc.).
- Cache, retry/timeout, circuit breaker, rate limiter, and metrics/health endpoints.
- Integration tests for API, git diff parsing, orchestrator cache/progress, BA/LLM paths.

## Integration Tests

- Standard suite: `uv run pytest tests`
- LLM-backed suite: `uv run pytest tests -m "llm"` (skips without key)
- Legacy root scripts retained in `legacy_tests/` for reference.

## Documentation Highlights

- Current docs: `docs/ARCHITECTURE.md`, `docs/MVP_SUMMARY.md`, `docs/ARCHIVE_NOTES.md`.
- Archived reports: reliability analyses, prompt engineering, phase test results, and design notes live in `docs/` (see `docs/ARCHIVE_NOTES.md` for the full list).

## Environment

- LLMs: OpenAI-compatible (`OpenAICompatibleProvider`) with OpenRouter/OpenAI; Anthropic optional if configured.
- Database: SQLite created at runtime; file caching optional.
- Metrics: Prometheus at `/metrics`; health probes at `/health`, `/health/ready`, `/health/live`.

## License

MIT

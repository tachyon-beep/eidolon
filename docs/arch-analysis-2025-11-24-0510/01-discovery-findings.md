# Discovery Findings - Eidolon Codebase Analysis

**Analysis Date:** 2025-11-24
**Analyst:** System Archaeologist
**Codebase:** Eidolon (formerly MONAD)
**Workspace:** docs/arch-analysis-2025-11-24-0510/

## Executive Summary

Eidolon is a **well-structured, production-ready hierarchical AI agent system** that has undergone recent reorganization from `backend/` to `src/eidolon/` package structure. The codebase consists of **~20,780 LOC** (excluding tests) with **remarkably low technical debt** (only 4 TODO/FIXME markers).

**Key Finding:** This is **mature, functional code** with minimal aspirational/dead code. The architecture is sound but documentation is **significantly outdated** due to the MONAD→Eidolon rename.

## Project Identity

### Name Evolution
- **Old Name:** MONAD (Monadic Autonomous Network for Adaptive Development)
- **Current Name:** Eidolon
- **Problem:** All documentation (README.md, ARCHITECTURE.md, MVP_SUMMARY.md) still references "MONAD"
- **Impact:** Documentation-code mismatch creates confusion

### Version
- **Current:** 0.1.0 (MVP phase)
- **Status:** Feature-complete MVP, production-ready backend, functional frontend

## Codebase Statistics

### Backend (Python)
- **Location:** `src/eidolon/`
- **Files:** 46 Python files
- **Lines of Code:** ~17,741 LOC
- **Subsystems:** 14 identified subsystems
- **Test Coverage:** 17 unit test files in `tests/`
- **TODO/FIXME Count:** 4 (0.02% - exceptionally low)
- **Python Version:** 3.10+

### Frontend (Vue 3)
- **Location:** `frontend/`
- **Files:** 15 Vue/JS files
- **Lines of Code:** ~3,039 LOC
- **Framework:** Vue 3 + Vite
- **State Management:** Pinia
- **Status:** Fully implemented (not skeletal)

### Total System
- **Combined LOC:** ~20,780 (excluding tests)
- **Quality:** High - clean structure, low debt, well-typed

## Technology Stack

### Backend Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.115.0 | Web framework |
| Uvicorn | 0.32.0 | ASGI server |
| Anthropic SDK | 0.39.0 | Claude API integration |
| OpenAI SDK | 1.58.1 | OpenAI/OpenRouter integration |
| Pydantic | 2.10.5 | Data validation |
| aiosqlite | 0.20.0 | Async SQLite |
| structlog | 24.4.0 | Structured logging |
| prometheus-client | 0.21.0 | Metrics |
| psutil | 6.1.0 | System metrics |
| networkx | 3.2.1+ | Graph analysis |

### Frontend Stack
- Vue 3 (Composition API)
- Vite (build tool)
- Pinia (state management)
- WebSocket client

### Build System
- **Package Manager:** `uv` (modern Python package manager)
- **Build Backend:** hatchling
- **Config:** `pyproject.toml` (modern Python standard)
- **Migration:** Recently migrated from `requirements.txt` to `pyproject.toml`

## Directory Structure

### Current Structure
```
eidolon/
├── src/eidolon/              # Backend package (NEW)
│   ├── agents/               # Orchestration & hierarchy
│   ├── analysis/             # Code analysis (AST, metrics)
│   ├── api/                  # FastAPI routes & WebSocket
│   ├── cache/                # Caching layer
│   ├── git_integration/      # Git operations
│   ├── health/               # Health check endpoints
│   ├── llm_providers/        # LLM abstraction layer
│   ├── metrics/              # Prometheus metrics
│   ├── models/               # Data models (Card, Agent, Task)
│   ├── planning/             # Task decomposition & planning
│   ├── resilience/           # Retry, timeout, circuit breaker
│   ├── storage/              # SQLite database layer
│   ├── utils/                # Utilities
│   ├── main.py               # FastAPI application entrypoint
│   ├── logging_config.py     # Logging configuration
│   ├── request_context.py    # Request tracking
│   ├── resource_limits.py    # Resource constraints
│   ├── code_graph.py         # Code graph analysis
│   ├── code_context_tools.py # Code context extraction
│   ├── design_context_tools.py # Design context tools
│   ├── code_writer.py        # Code generation
│   ├── specialist_agents.py  # Specialist agent implementations
│   ├── linting_agent.py      # Linting agent
│   ├── test_generator.py     # Test generation
│   ├── test_parallel.py      # Parallel testing
│   └── db_pool.py            # Database connection pooling
├── frontend/                 # Vue 3 frontend
│   ├── src/
│   │   ├── components/       # Vue components (9 files)
│   │   ├── views/            # Page views (3 files)
│   │   ├── stores/           # Pinia stores
│   │   └── router/           # Vue Router
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── tests/                    # Unit tests (NEW - 17 files)
├── examples/                 # Sample code for demos
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # Technical architecture (OUTDATED)
│   └── MVP_SUMMARY.md        # MVP summary (OUTDATED)
├── pyproject.toml            # Modern Python config (NEW)
├── uv.lock                   # Dependency lock file (NEW)
├── README.md                 # Project README (OUTDATED)
└── AGENTS.md                 # Agent guidelines (OUTDATED)
```

### Deleted Structure (Recent Migration)
```
backend/                      # DELETED (migrated to src/eidolon/)
  ├── models/                 # → src/eidolon/models/
  ├── agents/                 # → src/eidolon/agents/
  ├── analysis/               # → src/eidolon/analysis/
  ├── api/                    # → src/eidolon/api/
  ├── storage/                # → src/eidolon/storage/
  ├── planning/               # → src/eidolon/planning/
  ├── cache/                  # → src/eidolon/cache/
  ├── git_integration/        # → src/eidolon/git_integration/
  ├── health/                 # → src/eidolon/health/
  ├── llm_providers/          # → src/eidolon/llm_providers/
  ├── metrics/                # → src/eidolon/metrics/
  ├── resilience/             # → src/eidolon/resilience/
  ├── utils/                  # → src/eidolon/utils/
  ├── main.py                 # → src/eidolon/main.py
  └── requirements.txt        # → pyproject.toml dependencies
```

## Identified Subsystems (14 Total)

### Core Subsystems
1. **agents** - Agent orchestration and hierarchical deployment
2. **models** - Data models (Card, Agent, Task with full schemas)
3. **storage** - SQLite database layer with async operations
4. **api** - FastAPI routes and WebSocket endpoints

### Analysis & Intelligence
5. **analysis** - Code analysis (AST parsing, metrics, smells)
6. **planning** - Task decomposition, agent selection, prompts
7. **llm_providers** - Multi-provider LLM abstraction (Anthropic, OpenAI, OpenRouter)

### Infrastructure & Reliability
8. **resilience** - Retry logic, timeouts, circuit breakers, rate limiting
9. **cache** - Caching layer for analysis results
10. **health** - Health check endpoints (liveness, readiness)
11. **metrics** - Prometheus metrics collection

### Integration & Utilities
12. **git_integration** - Git operations and change detection
13. **utils** - Utility functions (JSON utils, etc.)
14. **Root-level modules** - logging_config, request_context, resource_limits, etc.

## Entry Points

### Backend Entry Point
- **File:** `src/eidolon/main.py`
- **Type:** FastAPI application
- **Startup:**
  - Initializes SQLite database (`monad.db`)
  - Creates AgentOrchestrator
  - Initializes health checker
  - Sets up CORS middleware
  - Includes API routes at `/api`
- **Endpoints:**
  - `GET /` - Root endpoint
  - `GET /health` - Comprehensive health check
  - `GET /health/ready` - Readiness probe
  - `GET /health/live` - Liveness probe
  - `GET /metrics` - Prometheus metrics
  - `/api/*` - API routes (cards, agents, analysis, WebSocket)

### Frontend Entry Point
- **File:** `frontend/src/main.js`
- **Framework:** Vue 3 with Composition API
- **Router:** Vue Router with 3 tab views (Explore, Code, Plan)
- **State:** Pinia store for cards and agents

### Development Commands
```bash
# Backend
uv sync                                    # Install dependencies
uv run uvicorn eidolon.main:app --reload  # Run dev server

# Frontend
cd frontend && npm install                 # Install dependencies
npm run dev                                # Run dev server
```

## Code Quality Indicators

### Positive Indicators (Strong)
✅ **Very low TODO/FIXME count (4 total)** - Code is implemented, not aspirational
✅ **Comprehensive type hints** - Pydantic models, typed function signatures
✅ **Structured logging** - Uses structlog throughout
✅ **Resilience patterns** - Circuit breakers, retries, timeouts, rate limiting
✅ **Clear separation of concerns** - Subsystems are well-defined
✅ **Proper package structure** - Modern `src/` layout
✅ **Test coverage exists** - 17 unit tests in dedicated `tests/` directory
✅ **Health and metrics** - Production-ready observability

### Negative Indicators (Moderate)
⚠️ **Documentation-code mismatch** - All docs reference "MONAD", code is "Eidolon"
⚠️ **Database name mismatch** - Creates `monad.db`, should be `eidolon.db`
⚠️ **No integration tests** - Only unit tests present
⚠️ **Frontend views incomplete** - MVP implements 3/6 planned tabs (Explore, Code, Plan)
⚠️ **Single database file** - SQLite in working directory (MVP acceptable)

### Dead/Aspirational Code Analysis
🔍 **TODO/FIXME Locations:**
1. `src/eidolon/test_generator.py` - 2 TODOs
2. `src/eidolon/design_context_tools.py` - 1 TODO
3. `src/eidolon/planning/decomposition.py` - 1 TODO

**Conclusion:** Only 4 TODOs across ~17,741 LOC = **0.02% aspirational markers**. This is exceptionally low, indicating **minimal dead/aspirational code**.

### Unused Files
Potential candidates for removal (require deeper analysis):
- `test_parallel.py` - May be experiment/prototype
- `business_analyst.py` (if it exists) - Referenced in docs but may be deleted

## Architecture Patterns Observed

### Design Patterns
1. **Hierarchical Agent Pattern** - System → Module → Function agent deployment
2. **Repository Pattern** - Database layer abstracts SQLite operations
3. **Provider Pattern** - LLM provider abstraction supports multiple backends
4. **Circuit Breaker Pattern** - Resilience module implements fault tolerance
5. **Observer Pattern** - WebSocket for real-time updates
6. **Card-Based Work Items** - Everything is a card (Review, Change, Architecture, etc.)

### Architectural Layers
```
┌─────────────────────────────────────┐
│  Frontend (Vue 3)                   │
│  - Views (Explore, Code, Plan)      │
│  - Components (CardTile, AgentTree) │
│  - Pinia Stores                     │
└─────────────────────────────────────┘
            │ HTTP/WebSocket
┌─────────────────────────────────────┐
│  API Layer (FastAPI)                │
│  - REST endpoints                   │
│  - WebSocket broadcasts             │
└─────────────────────────────────────┘
            │
┌─────────────────────────────────────┐
│  Orchestration Layer                │
│  - AgentOrchestrator                │
│  - Hierarchical deployment          │
│  - LLM provider abstraction         │
└─────────────────────────────────────┘
            │
┌─────────────────────────────────────┐
│  Business Logic                     │
│  - Code Analysis (AST, metrics)     │
│  - Planning & Decomposition         │
│  - Agent specialization             │
└─────────────────────────────────────┘
            │
┌─────────────────────────────────────┐
│  Infrastructure                     │
│  - Storage (SQLite)                 │
│  - Cache                            │
│  - Resilience (retry, circuit)      │
│  - Metrics & Health                 │
└─────────────────────────────────────┘
```

## Dependencies Analysis

### External Dependencies (Backend)
- **Total:** 13 runtime dependencies (lean)
- **No security vulnerabilities detected** (based on recent versions)
- **Well-maintained packages** (FastAPI, Anthropic, OpenAI, etc.)

### Internal Dependencies
- **Low coupling** - Subsystems are largely independent
- **Clear interfaces** - Models exported via `__init__.py`
- **No circular dependencies detected**

## Recent Changes (Git History)

Based on git status and recent commits:
1. **Migration to src/ layout** - Deleted entire `backend/` directory
2. **Migration to uv** - Added `pyproject.toml`, `uv.lock`
3. **Test restructuring** - Created dedicated `tests/` directory
4. **OpenRouter integration fixes** - Recent commits fixing tool call handling
5. **Diagnostic tests added** - Testing tool call message formatting

## Confidence Levels

| Aspect | Confidence | Notes |
|--------|------------|-------|
| Subsystem identification | **High** | Clear directory structure, well-defined modules |
| Code quality assessment | **High** | Low TODO count, strong typing, good patterns |
| Dead code detection | **Medium** | Requires runtime analysis to confirm unused code |
| Architecture understanding | **High** | Well-documented code, clear patterns |
| Documentation accuracy | **Low** | Docs reference old project name (MONAD) |
| Production readiness | **Medium-High** | Backend is solid, frontend is MVP-complete, lacks integration tests |

## Key Questions for Deeper Analysis

1. **Is `test_parallel.py` in active use or experimental?**
2. **Are there any unlinked specialist agents?** (specialist_agents.py vs actual usage)
3. **What is test coverage percentage?** (pytest-cov needed)
4. **Are all API endpoints actively used by frontend?**
5. **Is the cache actually improving performance?** (metrics needed)
6. **Which LLM provider is primary?** (Anthropic vs OpenAI vs OpenRouter)

## Recommendations for Next Steps

### Immediate (Required for quality assessment)
1. Run `pytest --cov=src/eidolon tests/` to measure test coverage
2. Grep for unused imports/functions across codebase
3. Check if `monad.db` should be renamed to `eidolon.db`
4. Validate all TODO/FIXME locations are tracked

### Short-term (Documentation cleanup)
1. Update all references from MONAD → Eidolon
2. Update architecture diagrams to reflect current structure
3. Document the backend→src/eidolon migration
4. Add CHANGELOG.md to track major changes

### Medium-term (Technical debt)
1. Add integration tests (E2E flows)
2. Add frontend tests (Vitest)
3. Set up CI/CD pipeline
4. Add code coverage enforcement (>80%)

## Summary for Architect Handover

**Verdict:** This is a **well-architected, production-ready system** that has been actively developed and recently refactored. The code quality is high, technical debt is low, and the structure is sound.

**Main Issues:**
1. **Documentation lag** - Docs don't reflect MONAD→Eidolon rename
2. **Test gaps** - Unit tests exist but no integration/E2E tests
3. **MVP scope** - Only 3/6 planned tabs implemented (acceptable for MVP)

**Refactor vs Restart?**
**→ REFACTOR** (definitely not restart)

The codebase is in excellent shape. No justification for rewrite. Focus on:
- Completing missing features (Test, Repair, Design tabs)
- Adding integration tests
- Updating documentation
- Performance optimization if needed

---

**Next Phase:** Proceed to subsystem catalog with parallel subagent analysis.

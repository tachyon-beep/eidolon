# Eidolon Architecture Discovery Findings

## Executive Summary

Eidolon is a **hierarchical AI agent-based code analysis and generation system** with a Python/FastAPI backend and Vue 3 frontend. The system breaks down user requests through a multi-tier hierarchy (System → Subsystem → Module → Class → Function), executes them with LLM assistance, and generates code with quality checks.

**Key Statistics:**
| Metric | Value |
|--------|-------|
| Python Files | 46 |
| Python LOC | ~18,300 |
| Frontend Files | ~12 Vue components |
| Total Subsystems | 12 identified |
| Architecture Style | Multi-tier hierarchical agent orchestration |

## Technology Stack

### Backend
- **Framework**: FastAPI (0.115.0)
- **Language**: Python 3.10+
- **Database**: SQLite with aiosqlite (async)
- **LLM Providers**: Anthropic Claude, OpenAI-compatible (OpenRouter)
- **Graph Analysis**: NetworkX
- **Validation**: Pydantic v2
- **Observability**: Prometheus metrics, structured logging (structlog)
- **Process Monitoring**: psutil

### Frontend
- **Framework**: Vue 3 + Composition API
- **Build Tool**: Vite
- **State Management**: Pinia
- **HTTP Client**: Axios
- **Real-time**: Native WebSocket API
- **Routing**: Vue Router (history mode)

### Infrastructure
- **Package Manager**: uv (Python), npm (Frontend)
- **Testing**: pytest, pytest-asyncio
- **Linting**: ruff, mypy

## Project Organization

```
eidolon/
├── src/eidolon/           # Backend Python package
│   ├── agents/            # Agent orchestration
│   ├── analysis/          # Code analysis (AST-based)
│   ├── api/               # FastAPI routes
│   ├── cache/             # Result caching
│   ├── git_integration/   # Git diff analysis
│   ├── health/            # Health probes
│   ├── llm_providers/     # LLM provider abstraction
│   ├── metrics/           # Prometheus metrics
│   ├── models/            # Pydantic domain models
│   ├── planning/          # Decomposition & review loops
│   ├── resilience/        # Retry, circuit breaker, rate limiting
│   ├── storage/           # SQLite persistence
│   ├── utils/             # Utilities
│   ├── orchestrator.py    # HierarchicalOrchestrator (code gen)
│   ├── business_analyst.py # Requirements refinement
│   ├── specialist_agents.py # Domain expert agents (12 types)
│   ├── linting_agent.py   # Code quality (ruff, mypy, LLM fixes)
│   ├── code_graph.py      # NetworkX code graph
│   ├── code_context_tools.py # LLM tool calling interface
│   ├── design_context_tools.py # Architecture exploration tools
│   ├── code_writer.py     # File writing with backups
│   └── test_generator.py  # Test generation
├── frontend/src/          # Vue 3 SPA
│   ├── components/        # 8 Vue components
│   ├── views/             # 3 views (Explore, Code, Plan)
│   ├── stores/            # Pinia state
│   └── router/            # Vue Router config
├── tests/                 # pytest test suite
│   └── integration/       # LLM-gated tests
└── docs/                  # Documentation
```

## Architectural Patterns Identified

### 1. Hierarchical Decomposition Pattern
User requests are broken down through 5 tiers:
```
User Request → System → Subsystem → Module → Class/Function → Code
```

### 2. Agent Negotiation Pattern (Review Loops)
- Primary agent generates output
- Reviewer agent critiques with score (0-100)
- Revision cycle until quality threshold met

### 3. Tool Calling Pattern
- LLMs can request code context via structured tool calls
- CodeContextToolHandler and DesignContextToolHandler provide on-demand context

### 4. Resilience Patterns (Production-Grade)
- Circuit breaker (fail-fast after threshold)
- Exponential backoff with jitter
- Rate limiting (token bucket)
- Timeout enforcement

### 5. Event-Driven UI Updates
- WebSocket broadcasts state changes
- Pinia store synchronizes client state
- Vue reactivity handles re-renders

## Identified Subsystems (12)

| # | Subsystem | Location | Primary Responsibility |
|---|-----------|----------|----------------------|
| 1 | API Layer | `api/`, `main.py` | HTTP/WebSocket endpoints |
| 2 | Agent Orchestration | `orchestrator.py`, `agents/` | Hierarchical agent coordination |
| 3 | Business Analyst | `business_analyst.py` | Requirements refinement |
| 4 | Specialist Agents | `specialist_agents.py`, `linting_agent.py` | Domain expert analysis |
| 5 | Planning System | `planning/` | Task decomposition |
| 6 | Code Analysis | `analysis/`, `code_graph.py`, `*_context_tools.py` | AST parsing, code graph |
| 7 | LLM Providers | `llm_providers/` | Multi-provider abstraction |
| 8 | Storage & Models | `storage/`, `models/` | Persistence, domain models |
| 9 | Cache System | `cache/` | Result caching |
| 10 | Resilience | `resilience/` | Fault tolerance patterns |
| 11 | Metrics & Health | `metrics/`, `health/` | Observability |
| 12 | Frontend UI | `frontend/src/` | Vue 3 SPA |

## Critical Dependencies

```
HierarchicalOrchestrator
├── BusinessAnalyst
├── SystemDecomposer → SubsystemDecomposer → ModuleDecomposer → FunctionPlanner
├── CodeGraphAnalyzer → CodeContextToolHandler
├── LintingAgent
└── LLMProvider (via resilience wrappers)

AgentOrchestrator (Analysis)
├── CodeAnalyzer
├── Database
├── CacheManager
├── LLMProvider (with circuit breaker, rate limiter)
└── SpecialistRegistry (12 specialists)
```

## Key Data Flows

### 1. Analysis Flow
```
HTTP POST /api/analyze → AgentOrchestrator.analyze_codebase()
  → CodeAnalyzer parses files
  → Build call graph
  → Deploy agents (parallel, semaphore-controlled)
  → LLM analysis per function
  → Create Cards (issues)
  → Persist to Database
  → WebSocket broadcast progress
  → Return hierarchy
```

### 2. Code Generation Flow
```
User Request → BusinessAnalyst.analyze_request()
  → DesignContextTools exploration (multi-turn)
  → RequirementsAnalysis output
  → SystemDecomposer (+ ReviewLoop)
  → ... recursive decomposition ...
  → FunctionPlanner.generate_implementation()
  → LintingAgent.lint_and_fix()
  → Write to file (with backup)
```

### 3. Frontend State Flow
```
API response / WebSocket message
  → cardStore.handleWebSocketMessage()
  → Pinia state updates
  → Vue reactivity
  → Component re-render
```

## Quality & Technical Debt Observations

### Strengths
1. **Well-structured hierarchical design** - Clear tier separation
2. **Production resilience patterns** - Circuit breaker, retries, rate limiting
3. **Comprehensive observability** - Prometheus metrics, health probes
4. **Clean LLM abstraction** - Multi-provider support with unified interface
5. **Tool calling for context** - Token-efficient on-demand context fetching

### Technical Debt & Issues

| Category | Issue | Severity | Location |
|----------|-------|----------|----------|
| **Code Duplication** | 12 specialist agents repeat JSON parsing pattern | HIGH | specialist_agents.py |
| **Code Duplication** | Decomposer classes have identical structure | MEDIUM | planning/decomposition.py |
| **Hard-coded Config** | System prompts embedded in code (1000+ lines each) | MEDIUM | specialist_agents.py |
| **Hard-coded Config** | Turn limits, timeouts, URLs hard-coded | LOW | Multiple files |
| **Thread Safety** | Progress tracking not thread-safe | MEDIUM | agents/orchestrator.py |
| **Thread Safety** | Circuit breaker state transitions unlocked | MEDIUM | resilience/ |
| **No Validation** | Cross-tier task consistency not validated | MEDIUM | planning/ |
| **No Pagination** | Database queries return all results | LOW | storage/database.py |
| **No Auth** | API endpoints unprotected | HIGH | api/routes.py |
| **WebSocket** | No reconnection logic in frontend | MEDIUM | frontend/App.vue |

## External Interface Points

### HTTP API Endpoints
- Card CRUD: `POST/GET/PUT/DELETE /api/cards`
- Analysis: `POST /api/analyze`, `POST /api/analyze/incremental`
- Agents: `GET /api/agents`, `GET /api/agents/{id}/hierarchy`
- Review: `POST /api/cards/{id}/review`
- Business Analyst: `POST /api/ba/projects`
- Cache: `GET/DELETE /api/cache`
- Health: `GET /health`, `/health/ready`, `/health/live`, `/metrics`

### WebSocket Events (broadcast)
- `card_updated`, `card_deleted`
- `analysis_started`, `analysis_progress`, `analysis_completed`, `analysis_error`
- `activity_update`
- `fix_applied`, `cache_cleared`

### LLM Provider Integration
- Anthropic API (claude-3-5-sonnet-20241022)
- OpenAI-compatible API (OpenRouter, Groq, Together.ai)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM API downtime | Medium | High | Circuit breaker + fallbacks |
| Database corruption | Low | High | WAL mode, backups |
| Token cost explosion | Medium | Medium | Rate limiting, caching |
| Security breach (no auth) | High | High | **Add authentication** |
| WebSocket disconnect | High | Low | **Add reconnection** |

## Confidence Level

**Overall Confidence: HIGH**

This analysis is based on:
- Direct code reading of all major files
- AST-based structure extraction
- Pattern recognition across codebase
- Cross-referencing imports and dependencies

**Gaps:**
- Runtime behavior not observed (no live debugging)
- Test coverage not measured
- Performance profiling not conducted

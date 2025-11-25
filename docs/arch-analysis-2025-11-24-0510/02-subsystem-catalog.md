# Eidolon Subsystem Catalog

## Overview

This document catalogs the 12 major subsystems identified in the Eidolon codebase, their responsibilities, key components, dependencies, and observed patterns.

---

## 1. API Layer

**Location:** `src/eidolon/api/`, `src/eidolon/main.py`
**Responsibility:** HTTP/WebSocket interface for all external interactions

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `main.py` | FastAPI application entry point, startup/shutdown, middleware | ~130 |
| `api/routes.py` | All endpoint handlers, WebSocket manager | ~800 |

### Entry Points
- `create_routes(db, orchestrator)` - Factory function returning router + WebSocket manager
- FastAPI app at `main.py:app`

### Dependencies (Inbound)
- Frontend (HTTP + WebSocket clients)

### Dependencies (Outbound)
- `AgentOrchestrator` - For analysis operations
- `Database` - For card/agent persistence
- `CacheManager` - For cache operations
- `HealthChecker` - For health endpoints

### Patterns Observed
- **Factory Pattern**: `create_routes()` creates router with injected dependencies
- **WebSocket Manager Pattern**: Connection tracking and broadcast
- **Pydantic Request Models**: Input validation

### Issues
- WebSocket broadcasts to ALL clients (no filtering)
- CORS origins hard-coded
- No authentication/authorization

---

## 2. Agent Orchestration

**Location:** `src/eidolon/orchestrator.py`, `src/eidolon/agents/`
**Responsibility:** Coordinates hierarchical agent execution for code generation and analysis

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `orchestrator.py` | HierarchicalOrchestrator - 6-phase code generation pipeline | ~1000 |
| `agents/orchestrator.py` | AgentOrchestrator - 5-tier analysis with parallel execution | ~1100 |

### Key Classes
```python
class HierarchicalOrchestrator:
    async def orchestrate(user_request, project_path) -> OrchestrationResult

class AgentOrchestrator:
    async def analyze_codebase(path) -> Agent
    async def analyze_incremental(path, base) -> Dict
```

### Dependencies (Inbound)
- API Layer (triggers analysis)

### Dependencies (Outbound)
- `BusinessAnalyst`, `SystemDecomposer`, `FunctionPlanner` (planning)
- `CodeGraphAnalyzer`, `CodeContextToolHandler` (context)
- `LintingAgent` (quality)
- `Database`, `CacheManager` (persistence)
- `LLMProvider` (via resilience wrappers)

### Patterns Observed
- **Hierarchical Decomposition**: Top-down task breakdown
- **Parallel Execution**: `asyncio.gather()` with semaphores
- **Graceful Degradation**: Continues on partial failures
- **Progress Tracking**: Real-time progress callbacks

### Issues
- Progress tracking dict mutations not thread-safe
- Hardcoded token estimates
- JSON extraction fallback paths

---

## 3. Business Analyst

**Location:** `src/eidolon/business_analyst.py`
**Responsibility:** Requirements refinement and change planning

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `business_analyst.py` | Multi-turn analysis with design tools | ~1200 |

### Key Classes
```python
class BusinessAnalyst:
    async def analyze_request(user_request, project_path, context) -> RequirementsAnalysis
    async def interactive_analyze(initial_request, project_path, user_callback) -> RequirementsAnalysis
```

### Dependencies (Inbound)
- `HierarchicalOrchestrator` (Phase 0.5)
- API Layer (BA endpoint)

### Dependencies (Outbound)
- `LLMProvider`
- `DesignContextToolHandler`
- `SpecialistRegistry`
- `CodeGraph` (optional)

### Patterns Observed
- **Multi-turn Conversation**: Up to 20 turns with tools
- **Tool Calling**: Design context exploration
- **Specialist Delegation**: Consults domain experts

### Issues
- Hardcoded turn limits (8, 20)
- No conversation context windowing
- Unknown tools silently handled

---

## 4. Specialist Agents

**Location:** `src/eidolon/specialist_agents.py`, `src/eidolon/linting_agent.py`
**Responsibility:** Domain-specific expert analysis

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `specialist_agents.py` | 12 domain experts (Security, Testing, Database, etc.) | ~2200 |
| `linting_agent.py` | Code quality with ruff, mypy, LLM fixes | ~500 |

### Specialist Types
1. SecurityEngineer - OWASP, vulnerabilities
2. TestEngineer - Test pyramid, TDD
3. DeploymentSpecialist - Docker, K8s, CI/CD
4. FrontendSpecialist - React/Vue, accessibility
5. DatabaseSpecialist - Schema, indexing
6. APISpecialist - REST/GraphQL design
7. DataSpecialist - Pipelines, ETL
8. IntegrationSpecialist - Third-party APIs
9. DiagnosticSpecialist - Debugging, profiling
10. PerformanceSpecialist - Optimization
11. PyTorchEngineer - ML models
12. UXSpecialist - User experience

### Dependencies (Inbound)
- `BusinessAnalyst` (specialist consultation)
- `HierarchicalOrchestrator` (quality checks)

### Dependencies (Outbound)
- `LLMProvider`
- External tools: `ruff`, `mypy`

### Patterns Observed
- **Abstract Factory**: `create_default_registry()`
- **Registry Pattern**: Domain-based specialist lookup
- **Three-Stage Fixing** (Linting): Auto-fix → Type check → LLM fix

### Issues
- **HIGH**: JSON parsing duplicated 12 times
- System prompts embedded (1000+ lines each)
- No per-specialist rate limiting

---

## 5. Planning System

**Location:** `src/eidolon/planning/`
**Responsibility:** Task decomposition with quality assurance

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `decomposition.py` | 5 decomposer classes | ~1100 |
| `review_loop.py` | Agent negotiation | ~400 |
| `prompt_templates.py` | Role-based prompts | ~560 |
| `agent_selector.py` | Intelligent routing | ~360 |
| `improved_decomposition.py` | JSON utilities | ~330 |

### Key Classes
```python
class SystemDecomposer, SubsystemDecomposer, ModuleDecomposer, ClassDecomposer
class FunctionPlanner
class ReviewLoop
class IntelligentAgentSelector
```

### Dependencies (Inbound)
- `HierarchicalOrchestrator` (phases 1-4)
- `BusinessAnalyst` (decomposition delegation)

### Dependencies (Outbound)
- `LLMProvider`
- `DesignContextToolHandler`
- `CodeContextToolHandler`

### Patterns Observed
- **Strategy Pattern**: Different decomposers per tier
- **Template Method**: Common decompose flow
- **Decorator Pattern**: Review loop wraps decomposition
- **Agent Negotiation**: Reviewer feedback cycles

### Issues
- Decomposer classes have near-identical structure (duplication)
- max_turns hardcoded at 6
- No cross-tier consistency validation

---

## 6. Code Analysis

**Location:** `src/eidolon/analysis/`, `src/eidolon/code_graph.py`, `src/eidolon/*_context_tools.py`
**Responsibility:** Static code analysis and context provision

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `analysis/code_analyzer.py` | AST-based analysis | ~510 |
| `code_graph.py` | NetworkX graph analysis | ~650 |
| `code_context_tools.py` | Code tool interface | ~440 |
| `design_context_tools.py` | Architecture tools | ~560 |

### Key Classes
```python
class CodeAnalyzer
class CodeGraphAnalyzer
class CodeGraph
class CodeContextToolHandler
class DesignContextToolHandler
```

### Tool Specifications
**Code Context Tools (6):**
- `get_function_definition`, `get_function_callers`, `get_function_callees`
- `get_class_definition`, `get_module_overview`, `search_functions`

**Design Context Tools (7):**
- `get_existing_modules`, `analyze_module_pattern`, `search_similar_modules`
- `get_subsystem_architecture`, `propose_design_option`
- `request_requirement_clarification`, `get_dependency_constraints`

### Dependencies (Inbound)
- `BusinessAnalyst`, `FunctionPlanner` (context queries)
- `AgentOrchestrator` (initial parsing)

### Dependencies (Outbound)
- `LLMProvider` (AI descriptions)
- `networkx`

### Patterns Observed
- **Graph-based Analysis**: NetworkX call/import graphs
- **Tool Calling**: On-demand context via LLM tools
- **Visitor Pattern**: AST traversal

### Issues
- Import resolution heuristic-based (may miss cross-module calls)
- Pattern detection too simple (keyword-based)
- No circular dependency detection

---

## 7. LLM Providers

**Location:** `src/eidolon/llm_providers/`
**Responsibility:** Unified LLM API abstraction

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `__init__.py` | Provider implementations | ~400 |
| `mock_provider.py` | Testing mock | ~50 |

### Key Classes
```python
class LLMProvider(ABC)
class AnthropicProvider(LLMProvider)
class OpenAICompatibleProvider(LLMProvider)
class MockProvider(LLMProvider)
```

### Supported Providers
- Anthropic (claude-3-5-sonnet-20241022)
- OpenAI-compatible (OpenRouter, Together.ai, Groq)

### Dependencies (Inbound)
- All components requiring LLM inference

### Dependencies (Outbound)
- `anthropic` library
- `openai` library

### Patterns Observed
- **Abstract Factory**: `create_provider()`
- **Adapter Pattern**: Unified interface to different APIs

### Issues
- OpenRouter special handling (sequential tool calls workaround)
- No provider health checking

---

## 8. Storage & Models

**Location:** `src/eidolon/storage/`, `src/eidolon/models/`
**Responsibility:** Data persistence and domain models

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `storage/database.py` | SQLite async operations | ~450 |
| `models/card.py` | Card, CardIssue, CardMetrics | ~200 |
| `models/__init__.py` | Agent, Task models | ~250 |
| `db_pool.py` | Connection pooling | ~200 |

### Key Classes
```python
class Database
class Card, CardType, CardStatus, CardPriority, CardIssue, CardMetrics
class Agent, AgentScope, AgentStatus
class Task, TaskType, TaskStatus, TaskPriority
```

### Dependencies (Inbound)
- API Layer (CRUD operations)
- `AgentOrchestrator` (persistence)

### Dependencies (Outbound)
- `aiosqlite`

### Patterns Observed
- **Repository Pattern**: Database class abstracts persistence
- **ID Generation**: Sequence-based unique IDs
- **Dual-locking**: Transaction + cursor locks

### Issues
- JSON serialization overhead
- Dual-locking complexity
- No pagination support
- Missing transaction management

---

## 9. Cache System

**Location:** `src/eidolon/cache/`
**Responsibility:** Analysis result caching

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `cache_manager.py` | SHA256-based content cache | ~350 |

### Key Classes
```python
class CacheManager
class CacheEntry
class CacheStats
```

### Dependencies (Inbound)
- `AgentOrchestrator` (cache lookups)
- API Layer (cache management endpoints)

### Dependencies (Outbound)
- `aiosqlite`

### Patterns Observed
- **Content Addressing**: MD5(file + hash + scope + target)
- **LRU Tracking**: Access counts for eviction

### Issues
- No size bounds (can grow unbounded)
- File hashing on every access (defeats caching for large files)
- No transaction safety

---

## 10. Resilience

**Location:** `src/eidolon/resilience/`
**Responsibility:** Fault tolerance patterns

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `__init__.py` | Circuit breaker, retry, rate limiting | ~350 |

### Key Classes/Functions
```python
class CircuitBreaker
class RateLimiter
async def retry_with_backoff(func, *args, config=None)
async def with_timeout(func, *args, timeout)

# Global instances
AI_API_BREAKER, GIT_OPERATIONS_BREAKER, DATABASE_BREAKER
AI_RATE_LIMITER
```

### Default Configuration
- AI API: 90s timeout, 3 failures → circuit open, 2min recovery
- Git: 30s timeout, 5 failures → circuit open, 1min recovery
- Database: 5s timeout, 3 failures → circuit open, 30s recovery
- Rate limit: 50 req/min, 40k tokens/min

### Dependencies (Inbound)
- All components making external calls

### Dependencies (Outbound)
- None (pure utility)

### Patterns Observed
- **Circuit Breaker**: State machine (CLOSED → OPEN → HALF_OPEN)
- **Exponential Backoff with Jitter**: Prevents thundering herd
- **Token Bucket**: Rate limiting

### Issues
- Circuit breaker not async-safe (race on failure_count)
- Rate limiter token tracking fragile
- No metrics integration

---

## 11. Metrics & Health

**Location:** `src/eidolon/metrics/`, `src/eidolon/health/`
**Responsibility:** Observability and health probes

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `metrics/__init__.py` | Prometheus metrics | ~400 |
| `health/__init__.py` | Health checker | ~200 |

### Key Metrics
- Analysis: `eidolon_analyses_total`, `eidolon_analysis_duration_seconds`
- AI API: `eidolon_ai_api_calls_total`, `eidolon_ai_api_tokens_total`, `eidolon_ai_api_latency_seconds`
- Cache: `eidolon_cache_operations_total`, `eidolon_cache_hit_rate_percent`
- Database: `eidolon_db_queries_total`, `eidolon_db_query_duration_seconds`
- HTTP: `eidolon_http_requests_total`, `eidolon_http_request_duration_seconds`
- Resources: `eidolon_process_cpu_percent`, `eidolon_process_memory_bytes`

### Health Checks
- `check_database()` - SELECT 1 with latency
- `check_cache()` - Statistics retrieval
- `check_disk_space()` - <10% free warning
- `check_memory()` - >90% used warning

### Dependencies (Inbound)
- API Layer (health/metrics endpoints)

### Dependencies (Outbound)
- `prometheus_client`
- `psutil`

### Patterns Observed
- **Prometheus Integration**: Standard metric types
- **Separated Probes**: Liveness vs Readiness
- **Context Managers**: `track_analysis()`, `MetricsContext`

### Issues
- Resource metrics sampled only at scrape time
- Label cardinality risk on HTTP endpoints
- Hardcoded health thresholds

---

## 12. Frontend UI

**Location:** `frontend/src/`
**Responsibility:** Vue 3 SPA for analysis interaction

### Key Components
| File | Purpose | LOC |
|------|---------|-----|
| `App.vue` | Root component, WebSocket setup | ~150 |
| `stores/cardStore.js` | Pinia state management | ~300 |
| `views/ExploreView.vue` | Main analysis view | ~450 |
| `views/CodeView.vue` | Code changes view | ~150 |
| `views/PlanView.vue` | Architecture planning | ~350 |
| `components/CardTile.vue` | Card display | ~200 |
| `components/RightDrawer.vue` | Card details panel | ~500 |

### State Management
```javascript
// Pinia store state
{
  cards: [],              // All cards
  agents: [],             // Agent hierarchy
  selectedCard: null,     // Current detail card
  isAnalyzing: false,     // Analysis in progress
  analysisProgress: {},   // Module/function counts
  cacheStats: {},         // Cache metrics
  recentActivities: []    // Activity log (last 20)
}
```

### Views
1. **ExploreView** - Full analysis, issue promotion, filtering
2. **CodeView** - Code changes and fix management
3. **PlanView** - Architecture planning, BA feature generation

### Dependencies (Inbound)
- User interaction

### Dependencies (Outbound)
- Backend API (HTTP + WebSocket)

### Patterns Observed
- **Composition API**: Vue 3 setup() pattern
- **Pinia State**: Centralized reactive state
- **WebSocket Sync**: Real-time state updates
- **Drag-and-Drop**: Card routing between views

### Issues
- Hard-coded WebSocket URL (localhost only)
- Issue promotion logic duplicated
- No WebSocket reconnection
- No error boundaries

---

## Dependency Matrix

```
                       │ API │ Orch │ BA │ Spec │ Plan │ Anly │ LLM │ Store │ Cache │ Resil │ Metr │ FE │
───────────────────────┼─────┼──────┼────┼──────┼──────┼──────┼─────┼───────┼───────┼───────┼──────┼────┤
1. API Layer           │  -  │  →   │ →  │      │      │      │     │   →   │   →   │       │  →   │    │
2. Agent Orchestration │  ←  │  -   │ →  │  →   │  →   │  →   │  →  │   →   │   →   │   →   │  →   │    │
3. Business Analyst    │  ←  │  ←   │ -  │  →   │      │  →   │  →  │       │       │       │      │    │
4. Specialist Agents   │     │  ←   │ ←  │  -   │      │      │  →  │       │       │       │      │    │
5. Planning System     │     │  ←   │    │      │  -   │  →   │  →  │       │       │       │      │    │
6. Code Analysis       │     │  ←   │ ←  │      │  ←   │  -   │  →  │       │       │       │      │    │
7. LLM Providers       │     │  ←   │ ←  │  ←   │  ←   │  ←   │  -  │       │       │       │      │    │
8. Storage & Models    │  ←  │  ←   │    │      │      │      │     │   -   │       │       │      │    │
9. Cache System        │  ←  │  ←   │    │      │      │      │     │       │   -   │       │      │    │
10. Resilience         │     │  ←   │    │      │      │      │     │       │       │   -   │      │    │
11. Metrics & Health   │  ←  │  ←   │    │      │      │      │     │       │       │       │  -   │    │
12. Frontend UI        │  →  │      │    │      │      │      │     │       │       │       │      │ -  │
```

Legend: `→` = depends on, `←` = depended on by, `-` = self

---

## Confidence Level: HIGH

All subsystems analyzed via direct code reading and cross-referencing. Patterns identified through structure and naming convention analysis.

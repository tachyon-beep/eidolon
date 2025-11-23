# Subsystem Catalog - Eidolon Architecture

**Analysis Date:** 2025-11-24
**Analyst:** System Archaeologist
**Total Subsystems:** 14
**Confidence:** High

---

## Subsystem 1: models

**Location:** `src/eidolon/models/`
**Primary Responsibility:** Core data models and type definitions for the entire system

**Key Components:**
- `card.py` - Card model with types (Review, Change, Architecture, Test, Defect, Requirement), statuses, priorities, metrics, and audit logging
- `agent.py` - Agent model with scopes (System, Module, Class, Function), session history, snapshots, and findings
- `task.py` - Task model with task graph, assignments, and results
- `__init__.py` - Exports all models and enums

**Dependencies:**
- **Inbound:** Used by ALL subsystems (storage, agents, api, analysis, planning, etc.)
- **Outbound:** Only Pydantic (external dependency)

**Patterns Observed:**
- Pydantic-based models for validation and serialization
- Comprehensive type system with enums for statuses, types, priorities
- Rich metadata (metrics, audit logs, links)
- Immutable data structures with validation

**Confidence:** Very High (complete, well-structured, central to architecture)

---

## Subsystem 2: agents

**Location:** `src/eidolon/agents/`
**Primary Responsibility:** Hierarchical agent orchestration and deployment

**Key Components:**
- `orchestrator.py` - Main AgentOrchestrator class with parallel execution, LLM integration, caching, resilience patterns
- `implementation_orchestrator.py` - ImplementationOrchestrator for code generation tasks
- `__init__.py` - Exports both orchestrators

**Dependencies:**
- **Inbound:** api (routes create orchestrator), main.py (startup initialization)
- **Outbound:** models (Card, Agent), storage (Database), cache (CacheManager), llm_providers (LLMProvider), resilience (retry, timeout, circuit breaker, rate limiter), analysis (CodeAnalyzer), git_integration (GitManager)

**Patterns Observed:**
- Orchestrator pattern for coordinating hierarchical agents
- Concurrency control with semaphores (max_concurrent_functions, max_concurrent_modules)
- Resilience integration (timeouts, retries, circuit breakers, rate limiting)
- Progress tracking and metrics collection
- Provider abstraction for multi-LLM support

**Confidence:** Very High (core orchestration logic, well-implemented)

---

## Subsystem 3: api

**Location:** `src/eidolon/api/`
**Primary Responsibility:** REST and WebSocket endpoints for frontend-backend communication

**Key Components:**
- `routes.py` - FastAPI router with card CRUD, agent queries, analysis triggers, WebSocket manager
- `__init__.py` - Exports create_routes, router, WebSocket manager

**Dependencies:**
- **Inbound:** main.py (includes router at /api), frontend (HTTP/WebSocket clients)
- **Outbound:** models (Card, Agent), storage (Database), agents (AgentOrchestrator), request_context (analysis_registry)

**Patterns Observed:**
- RESTful API design
- WebSocket for real-time updates and progress broadcasts
- Connection manager pattern for WebSocket clients
- Async endpoints throughout

**Confidence:** High (standard FastAPI implementation, likely complete for MVP)

---

## Subsystem 4: storage

**Location:** `src/eidolon/storage/`
**Primary Responsibility:** SQLite database layer with async operations

**Key Components:**
- `database.py` - Database class with async CRUD for cards and agents, connection management
- `__init__.py` - Exports Database class

**Dependencies:**
- **Inbound:** main.py (creates database), api (queries data), agents (persists cards/agents), health (connectivity checks)
- **Outbound:** models (Card, Agent), aiosqlite (external), logging_config

**Patterns Observed:**
- Repository pattern for data access
- Async/await for all database operations
- Connection lifecycle management (connect, close)
- Automatic table creation
- UUID-based ID generation

**Confidence:** Very High (complete CRUD implementation visible)

---

## Subsystem 5: analysis

**Location:** `src/eidolon/analysis/`
**Primary Responsibility:** Static code analysis using AST, metrics calculation, code smell detection

**Key Components:**
- `code_analyzer.py` - CodeAnalyzer class with AST parsing, complexity calculation, smell detection, subsystem identification
- Data classes: ModuleInfo, FunctionInfo, ClassInfo, SubsystemInfo
- `__init__.py` - Exports all analyzer components

**Dependencies:**
- **Inbound:** agents (orchestrator uses for code analysis)
- **Outbound:** ast (Python stdlib), models (indirectly for structure)

**Patterns Observed:**
- Visitor pattern for AST traversal
- Metric calculation (cyclomatic complexity, lines of code)
- Heuristic-based code smell detection (long functions, high complexity, missing docstrings, god classes)
- Subsystem clustering based on code organization

**Confidence:** High (AST-based analysis is standard, implementation appears complete)

---

## Subsystem 6: planning

**Location:** `src/eidolon/planning/`
**Primary Responsibility:** Task decomposition and planning through 5-tier hierarchy

**Key Components:**
- `decomposition.py` - Decomposers for each level (System, Subsystem, Module, Class, Function)
- `improved_decomposition.py` - Enhanced decomposition logic
- `agent_selector.py` - Logic for selecting appropriate specialist agents
- `prompt_templates.py` - LLM prompt templates for planning
- `review_loop.py` - Review and feedback loop for plans
- `__init__.py` - Exports all decomposers

**Dependencies:**
- **Inbound:** agents (orchestrator uses for task planning)
- **Outbound:** models (Task), llm_providers (for LLM-based planning)

**Patterns Observed:**
- Strategy pattern for different decomposition levels
- LLM-driven planning with structured prompts
- Multi-level decomposition (System → Subsystem → Module → Class → Function)
- Review loop for iterative improvement
- Agent selection logic for specialization

**Confidence:** High (comprehensive planning subsystem with clear hierarchy)

---

## Subsystem 7: llm_providers

**Location:** `src/eidolon/llm_providers/`
**Primary Responsibility:** Multi-provider LLM abstraction layer

**Key Components:**
- `__init__.py` (364 LOC!) - LLMProvider abstract base, AnthropicProvider, OpenAICompatibleProvider, create_provider factory
- `mock_provider.py` - MockLLMProvider for testing without API calls
- LLMResponse, LLMMessage data classes

**Dependencies:**
- **Inbound:** agents (orchestrator uses for AI calls)
- **Outbound:** anthropic SDK, openai SDK, os (env vars), logging_config

**Patterns Observed:**
- Abstract base class pattern for provider interface
- Factory pattern (create_provider) for instantiation
- Adapter pattern for normalizing different provider APIs
- Environment-based configuration
- Unified response format across providers
- OpenRouter-specific workarounds (sequential tool calls)

**Supported Providers:**
- Anthropic (Claude)
- OpenAI (GPT-4, GPT-4 Turbo)
- OpenRouter (any model via OpenAI-compatible API)
- Together.ai, Groq, etc. (any OpenAI-compatible endpoint)
- Mock (for testing)

**Confidence:** Very High (comprehensive, production-ready abstraction)

---

## Subsystem 8: resilience

**Location:** `src/eidolon/resilience/`
**Primary Responsibility:** Reliability patterns (timeouts, retries, circuit breakers, rate limiting)

**Key Components:**
- `__init__.py` (377 LOC!) - CircuitBreaker, retry_with_backoff, with_timeout, RateLimiter
- TimeoutConfig, RetryConfig dataclasses
- Global instances: AI_API_BREAKER, GIT_OPERATIONS_BREAKER, DATABASE_BREAKER, AI_RATE_LIMITER

**Dependencies:**
- **Inbound:** agents (uses for AI API calls), potentially git_integration, storage
- **Outbound:** asyncio, time, random (stdlib)

**Patterns Observed:**
- Circuit Breaker pattern (closed/half-open/open states)
- Exponential backoff with jitter for retries
- Token bucket rate limiting
- Timeout wrappers for all async operations
- Pre-configured global breakers for critical services
- Transient error detection

**Confidence:** Very High (production-grade reliability implementation)

---

## Subsystem 9: cache

**Location:** `src/eidolon/cache/`
**Primary Responsibility:** Caching layer for analysis results

**Key Components:**
- `cache_manager.py` - CacheManager class with get/set/invalidate, statistics, lifecycle management
- `__init__.py` - Exports CacheManager

**Dependencies:**
- **Inbound:** agents (orchestrator uses for caching analysis results), health (cache health checks)
- **Outbound:** hashlib, json, time (stdlib), likely file system for storage

**Patterns Observed:**
- Cache-aside pattern
- Statistics tracking (hits, misses, hit rate)
- TTL-based expiration (likely)
- Content-based hashing for cache keys
- Async initialization and operations

**Confidence:** High (standard caching implementation)

---

## Subsystem 10: git_integration

**Location:** `src/eidolon/git_integration/`
**Primary Responsibility:** Git operations and change detection for incremental analysis

**Key Components:**
- `__init__.py` (197 LOC) - GitManager class, GitChanges dataclass
- Operations: is_git_repo, get_changed_files, get_current_commit, get_current_branch, get_file_last_modified_commit

**Dependencies:**
- **Inbound:** agents (for incremental analysis mode)
- **Outbound:** subprocess (git CLI), pathlib (stdlib)

**Patterns Observed:**
- Wrapper pattern for git CLI commands
- Timeout protection on subprocess calls
- File extension filtering for change detection
- Categorized changes (modified, added, deleted, renamed)
- Convenience method for Python files

**Confidence:** High (complete git integration for incremental analysis)

---

## Subsystem 11: health

**Location:** `src/eidolon/health/`
**Primary Responsibility:** Health check system for all components

**Key Components:**
- `__init__.py` (278 LOC) - HealthChecker class, ComponentHealth dataclass
- Checks: database, cache, disk space, memory
- Probe types: comprehensive health, readiness (K8s), liveness (K8s)

**Dependencies:**
- **Inbound:** main.py (creates health checker, exposes /health endpoints)
- **Outbound:** storage (Database), cache (CacheManager), psutil, shutil (stdlib)

**Patterns Observed:**
- Health check pattern for distributed systems
- Kubernetes probe compatibility (liveness, readiness)
- Parallel health checks with asyncio.gather
- Latency measurement for each check
- Structured health responses with details

**Confidence:** Very High (production-ready health monitoring)

---

## Subsystem 12: metrics

**Location:** `src/eidolon/metrics/`
**Primary Responsibility:** Prometheus metrics collection

**Key Components:**
- `__init__.py` (413 LOC) - Comprehensive Prometheus metrics, update_resource_metrics, get_metrics_response, convenience functions
- Metric types: Counter, Histogram, Gauge, Info
- Categories: Analysis, AI API, Circuit Breakers, Retries, Cache, Database, WebSocket, Git, Cards, Errors, Resources, HTTP

**Dependencies:**
- **Inbound:** main.py (/metrics endpoint), agents (records AI calls), storage (DB metrics), api (HTTP metrics), cache (cache metrics)
- **Outbound:** prometheus-client, psutil

**Patterns Observed:**
- Prometheus exposition format
- Metric labels for dimensionality (operation, status, type, etc.)
- Resource usage tracking (CPU, memory, disk, file descriptors)
- Context managers for timing (MetricsContext, track_analysis)
- Convenience functions for common patterns

**Confidence:** Very High (comprehensive production-grade metrics)

---

## Subsystem 13: utils

**Location:** `src/eidolon/utils/`
**Primary Responsibility:** Utility functions

**Key Components:**
- `json_utils.py` - JSON serialization/deserialization utilities
- `__init__.py` - Exports (currently minimal/empty)

**Dependencies:**
- **Inbound:** Various subsystems for JSON handling
- **Outbound:** json (stdlib)

**Patterns Observed:**
- Utility module pattern
- Centralized JSON handling

**Confidence:** Medium (limited visibility, appears lightweight)

---

## Subsystem 14: Root-Level Modules

**Location:** `src/eidolon/*.py` (not in subdirectories)
**Primary Responsibility:** Cross-cutting concerns and specialized agents

**Key Components:**
- `main.py` - FastAPI application entrypoint, startup/shutdown lifecycle
- `logging_config.py` - Structured logging configuration with structlog
- `request_context.py` - Request tracking and analysis registry
- `resource_limits.py` - Resource constraints and limits
- `code_graph.py` - Code graph analysis and dependency tracking
- `code_context_tools.py` - Code context extraction tools
- `design_context_tools.py` - Design context tools (1 TODO)
- `code_writer.py` - Code generation utilities
- `specialist_agents.py` - Specialist agent implementations
- `linting_agent.py` - Linting agent
- `test_generator.py` - Test generation (2 TODOs)
- `test_parallel.py` - Parallel testing utilities
- `db_pool.py` - Database connection pooling

**Dependencies:**
- **Inbound:** main.py is the entrypoint; others are used by agents, api, etc.
- **Outbound:** Various (models, storage, llm_providers, etc.)

**Patterns Observed:**
- Application composition pattern (main.py)
- Cross-cutting concerns (logging, context tracking)
- Specialist agents for specific tasks
- Graph-based code analysis (networkx)
- Tool implementations for LLM agents

**Confidence:** Medium-High (visible files, but need deeper analysis for usage patterns)

---

## Frontend Subsystem (Bonus)

**Location:** `frontend/`
**Primary Responsibility:** Vue 3 user interface

**Key Components:**
- `src/main.js` - Vue app entry point
- `src/App.vue` - Root component
- `src/router/index.js` - Vue Router configuration
- `src/stores/cardStore.js` - Pinia state management for cards
- `src/views/` - ExploreView, CodeView, PlanView
- `src/components/` - CardTile, AgentTree, TreeNode, LeftDock, RightDrawer, TopNav, AgentSnoop, NotificationSystem
- `package.json` - Dependencies (Vue 3, Vite, Pinia, Axios)

**Dependencies:**
- **Inbound:** User browser
- **Outbound:** api (HTTP + WebSocket)

**Patterns Observed:**
- Vue 3 Composition API
- Component-based architecture
- Centralized state management (Pinia)
- Real-time updates via WebSocket
- SPA routing
- Card-based UI metaphor

**LOC:** ~3,039 lines (Vue + JS)

**Confidence:** High (complete MVP implementation for 3 tabs: Explore, Code, Plan)

---

## Dependency Matrix

### High-Level Dependencies (Simplified)

```
Frontend
  └─> api (REST + WebSocket)

api
  ├─> storage (Database)
  ├─> agents (AgentOrchestrator)
  └─> models (Card, Agent)

agents (AgentOrchestrator)
  ├─> models (Card, Agent)
  ├─> storage (Database)
  ├─> cache (CacheManager)
  ├─> llm_providers (LLMProvider)
  ├─> resilience (retry, timeout, circuit breaker, rate limiter)
  ├─> analysis (CodeAnalyzer)
  ├─> planning (Decomposers)
  └─> git_integration (GitManager)

analysis
  └─> ast (stdlib)

planning
  ├─> models (Task)
  └─> llm_providers (LLMProvider)

llm_providers
  ├─> anthropic SDK
  ├─> openai SDK
  └─> logging_config

resilience
  └─> asyncio, time, random (stdlib)

cache
  └─> hashlib, json, time (stdlib)

storage
  ├─> models (Card, Agent)
  ├─> aiosqlite
  └─> logging_config

git_integration
  └─> subprocess, pathlib (stdlib)

health
  ├─> storage (Database)
  ├─> cache (CacheManager)
  └─> psutil, shutil

metrics
  ├─> prometheus-client
  └─> psutil

main.py
  ├─> storage (Database)
  ├─> agents (AgentOrchestrator)
  ├─> api (create_routes)
  ├─> health (HealthChecker)
  ├─> metrics (get_metrics_response)
  ├─> logging_config
  └─> request_context
```

---

## Subsystem Coupling Analysis

### Low Coupling (Good)
- **analysis** - Only depends on stdlib (ast)
- **resilience** - Only depends on stdlib
- **cache** - Minimal dependencies
- **git_integration** - Only depends on stdlib

### Medium Coupling (Acceptable)
- **llm_providers** - 2 external SDKs + logging
- **storage** - models + aiosqlite + logging
- **health** - 2 internal + 2 external deps
- **planning** - models + llm_providers

### High Coupling (Expected for Orchestrators)
- **agents** - 8+ dependencies (orchestration hub)
- **api** - 3-4 dependencies (API gateway)
- **main.py** - 6+ dependencies (application composition)

**Overall:** Clean architecture with appropriate coupling levels. Core libraries (analysis, resilience, cache) are decoupled, while orchestrators naturally have higher coupling.

---

## Dead/Unused Code Candidates

Based on file names and TODO markers:

1. **test_parallel.py** - May be experimental/prototype (requires validation)
2. **design_context_tools.py** - Has 1 TODO (incomplete?)
3. **test_generator.py** - Has 2 TODOs (incomplete?)

**Note:** Actual usage requires runtime analysis or dependency graph tool.

---

## Architectural Observations

### Strengths
✅ **Clear separation of concerns** - Each subsystem has well-defined responsibility
✅ **Layered architecture** - Frontend → API → Orchestration → Business Logic → Infrastructure
✅ **Provider abstractions** - LLM providers are swappable
✅ **Production-ready patterns** - Resilience, health checks, metrics
✅ **Async throughout** - Proper async/await usage
✅ **Type safety** - Pydantic models everywhere
✅ **Observability** - Comprehensive logging, metrics, health checks

### Potential Improvements
⚠️ **Documentation mismatch** - Code references Eidolon, docs reference MONAD
⚠️ **Test coverage unknown** - Need pytest-cov to measure
⚠️ **Integration tests missing** - Only unit tests exist
⚠️ **Frontend incomplete** - 3/6 planned tabs (MVP acceptable)

---

## Summary

**Total Subsystems Analyzed:** 14 backend + 1 frontend = 15 total

**Architecture Quality:** High - Well-organized, low coupling, clear responsibilities

**Code Maturity:** Production-ready backend, MVP-complete frontend

**Refactor vs Restart Decision:** **REFACTOR** - Code quality is excellent, architecture is sound. No justification for rewrite. Focus on completing features, adding tests, and updating documentation.

---

**Confidence in Analysis:** Very High
**Next Steps:** Code quality assessment → Architecture diagrams → Final report → Architect handover

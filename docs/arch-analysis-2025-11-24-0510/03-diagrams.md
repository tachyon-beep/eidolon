# Eidolon Architecture Diagrams (C4 Model)

## C4 Model Overview

The C4 model provides four levels of abstraction:
1. **Context** - System and its external actors
2. **Container** - High-level technology choices
3. **Component** - Logical components within containers
4. **Code** - Class/module level (omitted for brevity)

---

## Level 1: System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL CONTEXT                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              ┌─────────────┐                                │
│                              │  Developer  │                                │
│                              │   (User)    │                                │
│                              └──────┬──────┘                                │
│                                     │                                       │
│                      Uses web UI to analyze code,                           │
│                      review findings, apply fixes                           │
│                                     │                                       │
│                                     ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │                     ╔═══════════════════════════╗                     │  │
│  │                     ║       EIDOLON            ║                      │  │
│  │                     ║  Hierarchical Agent       ║                     │  │
│  │                     ║  Code Analysis System     ║                     │  │
│  │                     ╚═══════════════════════════╝                     │  │
│  │                                                                       │  │
│  │  Analyzes codebases using AI agents, generates review cards,          │  │
│  │  proposes fixes, and orchestrates multi-tier decomposition.           │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                          │                     │                            │
│              ┌───────────┴──────────┐    ┌─────┴──────────┐                 │
│              │                      │    │                │                 │
│              ▼                      ▼    ▼                ▼                 │
│    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐     │
│    │   Anthropic API   │  │  OpenAI/OpenRouter │  │  Local Codebase  │     │
│    │   (Claude LLM)    │  │   (GPT-4, etc.)   │  │  (File System)   │     │
│    └───────────────────┘  └───────────────────┘  └───────────────────┘     │
│         LLM inference          LLM inference          Code analysis         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### System Context Description

| Element | Type | Description |
|---------|------|-------------|
| Developer | Person | Software developer using Eidolon to analyze and improve code |
| Eidolon | System | AI-powered code analysis and generation system |
| Anthropic API | External System | Claude LLM API for AI-powered analysis |
| OpenAI/OpenRouter | External System | Alternative LLM providers |
| Local Codebase | External System | The code repository being analyzed |

---

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  EIDOLON SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────────┐                                                             │
│    │   Developer  │                                                             │
│    └───────┬──────┘                                                             │
│            │ HTTPS / WebSocket                                                  │
│            ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         FRONTEND CONTAINER                              │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │   │
│  │  │                    Vue 3 SPA (Vite)                                │  │   │
│  │  │                                                                    │  │   │
│  │  │   ┌─────────┐   ┌──────────┐   ┌──────────┐                       │  │   │
│  │  │   │ Explore │   │   Code   │   │   Plan   │                       │  │   │
│  │  │   │  View   │   │   View   │   │   View   │                       │  │   │
│  │  │   └─────────┘   └──────────┘   └──────────┘                       │  │   │
│  │  │         │              │              │                            │  │   │
│  │  │         └──────────────┼──────────────┘                            │  │   │
│  │  │                        ▼                                           │  │   │
│  │  │              ┌────────────────────┐                                │  │   │
│  │  │              │  Pinia cardStore   │                                │  │   │
│  │  │              │  (State Management)│                                │  │   │
│  │  │              └────────────────────┘                                │  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│            │ HTTP API + WebSocket                                               │
│            ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         BACKEND CONTAINER                               │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │   │
│  │  │                   FastAPI Application                              │  │   │
│  │  │                                                                    │  │   │
│  │  │   ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐ │  │   │
│  │  │   │  API Routes  │   │ AgentOrchestrator│   │ HierarchicalOrch │ │  │   │
│  │  │   │  (REST + WS) │   │   (Analysis)     │   │  (Generation)    │ │  │   │
│  │  │   └──────────────┘   └──────────────────┘   └──────────────────┘ │  │   │
│  │  │          │                    │                      │           │  │   │
│  │  │          │    ┌───────────────┴───────────────┐      │           │  │   │
│  │  │          │    ▼                               ▼      │           │  │   │
│  │  │   ┌─────────────────┐           ┌─────────────────┐  │           │  │   │
│  │  │   │  Planning &     │           │  Code Analysis  │  │           │  │   │
│  │  │   │  Decomposition  │           │  & Code Graph   │  │           │  │   │
│  │  │   └─────────────────┘           └─────────────────┘  │           │  │   │
│  │  │          │                               │           │           │  │   │
│  │  │          └───────────────┬───────────────┘           │           │  │   │
│  │  │                          ▼                           │           │  │   │
│  │  │               ┌─────────────────────┐                │           │  │   │
│  │  │               │    LLM Providers    │◄───────────────┘           │  │   │
│  │  │               │ (Anthropic/OpenAI)  │                            │  │   │
│  │  │               └─────────────────────┘                            │  │   │
│  │  │                          │                                       │  │   │
│  │  │          ┌───────────────┼───────────────┐                       │  │   │
│  │  │          ▼               ▼               ▼                       │  │   │
│  │  │   ┌───────────┐   ┌───────────┐   ┌───────────┐                 │  │   │
│  │  │   │ Resilience│   │  Metrics  │   │  Health   │                 │  │   │
│  │  │   │(CB/Retry) │   │(Prometheus)│  │ (Probes)  │                 │  │   │
│  │  │   └───────────┘   └───────────┘   └───────────┘                 │  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│            │                                                                    │
│            ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        DATABASE CONTAINER                               │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │   │
│  │  │                      SQLite (aiosqlite)                            │  │   │
│  │  │                                                                    │  │   │
│  │  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐│  │   │
│  │  │   │    Cards    │   │   Agents    │   │  Analysis Cache         ││  │   │
│  │  │   │   Table     │   │   Table     │   │  (content-addressed)    ││  │   │
│  │  │   └─────────────┘   └─────────────┘   └─────────────────────────┘│  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                     │                              │
                     ▼                              ▼
          ┌───────────────────┐          ┌───────────────────┐
          │   Anthropic API   │          │  Local Filesystem │
          │     (Claude)      │          │    (Codebase)     │
          └───────────────────┘          └───────────────────┘
```

### Container Descriptions

| Container | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Vue 3, Vite, Pinia | Single-page application for user interaction |
| Backend | FastAPI, Python 3.10+ | REST API, WebSocket, orchestration logic |
| Database | SQLite (aiosqlite) | Persistent storage for cards, agents, cache |

---

## Level 3: Component Diagram (Backend)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND CONTAINER (FastAPI)                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           API LAYER                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │   │
│  │  │  Card Routes   │  │ Analysis Routes│  │ WebSocket Mgr  │                 │   │
│  │  │ (CRUD + review)│  │ (full/incremental│ │ (broadcast)    │                 │   │
│  │  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                 │   │
│  └──────────┼───────────────────┼───────────────────┼───────────────────────────┘   │
│             │                   │                   │                               │
│             ▼                   ▼                   ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        ORCHESTRATION LAYER                                   │   │
│  │                                                                              │   │
│  │  ┌──────────────────────────┐        ┌──────────────────────────┐           │   │
│  │  │   AgentOrchestrator      │        │ HierarchicalOrchestrator │           │   │
│  │  │                          │        │                          │           │   │
│  │  │  • 5-tier analysis       │        │  • 6-phase pipeline      │           │   │
│  │  │  • Parallel execution    │        │  • Code generation       │           │   │
│  │  │  • Card creation         │        │  • Review loops          │           │   │
│  │  │  • Cache integration     │        │  • Linting integration   │           │   │
│  │  └────────────┬─────────────┘        └────────────┬─────────────┘           │   │
│  │               │                                   │                          │   │
│  └───────────────┼───────────────────────────────────┼──────────────────────────┘   │
│                  │                                   │                               │
│                  ▼                                   ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          DOMAIN LAYER                                        │   │
│  │                                                                              │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │   │
│  │  │ Business Analyst│  │ Specialist Agent│  │  Linting Agent  │              │   │
│  │  │                 │  │    Registry     │  │                 │              │   │
│  │  │ • Requirement   │  │                 │  │ • ruff + mypy   │              │   │
│  │  │   refinement    │  │ • 12 specialists│  │ • LLM fixes     │              │   │
│  │  │ • Design tools  │  │ • Domain experts│  │ • 3-stage fix   │              │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │   │
│  │           │                    │                    │                        │   │
│  │  ┌────────┴─────────────┬──────┴──────────┬─────────┴───────────┐           │   │
│  │  │                      │                 │                     │           │   │
│  │  ▼                      ▼                 ▼                     ▼           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │   │
│  │  │ Planning System │  │  Code Analysis  │  │   Code Graph    │             │   │
│  │  │                 │  │                 │  │                 │             │   │
│  │  │ • Decomposers   │  │ • AST parsing   │  │ • NetworkX      │             │   │
│  │  │   (5 tiers)     │  │ • Code smells   │  │ • Call graph    │             │   │
│  │  │ • Review loop   │  │ • Module info   │  │ • Import graph  │             │   │
│  │  │ • Agent selector│  │                 │  │                 │             │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │   │
│  │           │                    │                    │                       │   │
│  │           └────────────────────┼────────────────────┘                       │   │
│  │                                ▼                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                      TOOL CALLING LAYER                             │   │   │
│  │  │  ┌──────────────────────┐       ┌──────────────────────┐           │   │   │
│  │  │  │ CodeContextToolHandler│      │ DesignContextToolHandler│        │   │   │
│  │  │  │ (6 tools)            │       │ (7 tools)              │         │   │   │
│  │  │  └──────────────────────┘       └──────────────────────┘           │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                          │
│                                          ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          INFRASTRUCTURE LAYER                                │   │
│  │                                                                              │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐ │   │
│  │  │ LLM Providers │  │   Database    │  │ Cache Manager │  │  Resilience   │ │   │
│  │  │               │  │               │  │               │  │               │ │   │
│  │  │ • Anthropic   │  │ • Cards       │  │ • SHA256 hash │  │ • Circuit     │ │   │
│  │  │ • OpenAI      │  │ • Agents      │  │ • Content addr│  │   breaker     │ │   │
│  │  │ • MockProvider│  │ • Sequences   │  │ • TTL eviction│  │ • Retry       │ │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘  │ • Rate limit  │ │   │
│  │                                                           └───────────────┘ │   │
│  │  ┌───────────────┐  ┌───────────────┐                                       │   │
│  │  │    Metrics    │  │    Health     │                                       │   │
│  │  │               │  │               │                                       │   │
│  │  │ • Prometheus  │  │ • Liveness    │                                       │   │
│  │  │ • Counters    │  │ • Readiness   │                                       │   │
│  │  │ • Histograms  │  │ • Components  │                                       │   │
│  │  └───────────────┘  └───────────────┘                                       │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Level 3: Component Diagram (Frontend)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND CONTAINER (Vue 3)                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              APP ROOT (App.vue)                              │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │   │
│  │  │     TopNav      │  │    LeftDock     │  │   NotificationSystem        │  │   │
│  │  │ (Tab navigation)│  │ (Drag-drop zone)│  │   (Toast messages)          │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                          │
│                          ┌───────────────┼───────────────┐                          │
│                          ▼               ▼               ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              VIEW LAYER                                      │   │
│  │                                                                              │   │
│  │  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐    │   │
│  │  │    ExploreView      │ │     CodeView        │ │     PlanView        │    │   │
│  │  │                     │ │                     │ │                     │    │   │
│  │  │ • Analysis input    │ │ • Change cards      │ │ • BA panel          │    │   │
│  │  │ • Progress tracking │ │ • Fix status        │ │ • Feature generation│    │   │
│  │  │ • Card grid         │ │ • Card grid         │ │ • Arch cards        │    │   │
│  │  │ • Issue promotion   │ │                     │ │                     │    │   │
│  │  │ • Agent tree        │ │                     │ │                     │    │   │
│  │  └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘    │   │
│  └─────────────┼────────────────────────┼────────────────────────┼──────────────┘   │
│                │                        │                        │                  │
│                └────────────────────────┼────────────────────────┘                  │
│                                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           COMPONENT LAYER                                    │   │
│  │                                                                              │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │   │
│  │  │    CardTile     │  │   RightDrawer   │  │   AgentTree     │              │   │
│  │  │                 │  │                 │  │                 │              │   │
│  │  │ • Card display  │  │ • Card details  │  │ • Hierarchy     │              │   │
│  │  │ • Drag source   │  │ • Fix preview   │  │   visualization │              │   │
│  │  │ • Type styling  │  │ • LLM review    │  │ • Recursive     │              │   │
│  │  │                 │  │ • Issue promote │  │   TreeNode      │              │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘              │   │
│  │                                                                              │   │
│  │  ┌─────────────────┐                                                        │   │
│  │  │   AgentSnoop    │                                                        │   │
│  │  │                 │                                                        │   │
│  │  │ • Agent details │                                                        │   │
│  │  │ • Hierarchy load│                                                        │   │
│  │  └─────────────────┘                                                        │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                           │
│                                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                            STATE LAYER                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                       cardStore (Pinia)                                │  │   │
│  │  │                                                                        │  │   │
│  │  │  State:                        Actions:                                │  │   │
│  │  │  • cards[]                     • fetchCards()                          │  │   │
│  │  │  • agents[]                    • createCard()                          │  │   │
│  │  │  • selectedCard                • updateCard()                          │  │   │
│  │  │  • isAnalyzing                 • analyzeCodebase()                     │  │   │
│  │  │  • analysisProgress            • reviewCard()                          │  │   │
│  │  │  • recentActivities            • applyFix()                            │  │   │
│  │  │  • cacheStats                  • handleWebSocketMessage()              │  │   │
│  │  └───────────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                           │
│                              ┌──────────┴──────────┐                                │
│                              ▼                     ▼                                │
│                    ┌─────────────────┐    ┌─────────────────┐                      │
│                    │   Axios HTTP    │    │    WebSocket    │                      │
│                    │     Client      │    │   Connection    │                      │
│                    └─────────────────┘    └─────────────────┘                      │
│                              │                     │                                │
└──────────────────────────────┼─────────────────────┼────────────────────────────────┘
                               │                     │
                               ▼                     ▼
                        ┌────────────────────────────────┐
                        │       Backend API Server       │
                        │        (FastAPI)               │
                        └────────────────────────────────┘
```

---

## Data Flow Diagrams

### Analysis Request Flow

```
┌─────────┐     POST /api/analyze      ┌─────────────────┐
│ Frontend│ ──────────────────────────▶│    API Routes   │
│   UI    │                            │                 │
└─────────┘                            └────────┬────────┘
     ▲                                          │
     │                                          ▼
     │ WebSocket                       ┌─────────────────┐
     │ Updates                         │AgentOrchestrator│
     │                                 │                 │
     │                                 │  • Parse files  │
     │                                 │  • Build graph  │
     │                                 │  • Deploy agents│
     │                                 └────────┬────────┘
     │                                          │
     │                                          ▼
     │                                 ┌─────────────────┐
     │                                 │  Code Analyzer  │──────┐
     │                                 │                 │      │
     │                                 │  • AST parsing  │      │
     │                                 │  • Code smells  │      │ Parallel
     │                                 └─────────────────┘      │ Execution
     │                                          │               │
     │                                          ▼               │
     │                                 ┌─────────────────┐      │
     │                                 │  LLM Provider   │◀─────┘
     │                                 │  (+ Resilience) │
     │                                 │                 │
     │                                 │  • Analysis     │
     │                                 │  • Card creation│
     │                                 └────────┬────────┘
     │                                          │
     │                                          ▼
     │                                 ┌─────────────────┐
     │                                 │    Database     │
     │                                 │                 │
     │                                 │  • Save cards   │
     │                                 │  • Save agents  │
     │                                 └────────┬────────┘
     │                                          │
     └──────────────────────────────────────────┘
                    card_updated, analysis_progress
```

### Card Review Flow

```
┌─────────┐  POST /api/cards/{id}/review   ┌─────────────────┐
│ Frontend│ ──────────────────────────────▶│    API Routes   │
│   UI    │                                │                 │
└─────────┘                                └────────┬────────┘
     ▲                                              │
     │                                              ▼
     │                                     ┌─────────────────┐
     │                                     │  Card Lookup    │
     │                                     │  (Database)     │
     │                                     └────────┬────────┘
     │                                              │
     │                                              ▼
     │                                     ┌─────────────────┐
     │                                     │ Context Builder │
     │                                     │                 │
     │                                     │ • Get code graph│
     │                                     │ • Find callers  │
     │                                     │ • Find callees  │
     │                                     │ • Build prompt  │
     │                                     └────────┬────────┘
     │                                              │
     │                                              ▼
     │                                     ┌─────────────────┐
     │                                     │  LLM Provider   │
     │                                     │                 │
     │                                     │ • Review code   │
     │                                     │ • Generate grade│
     │                                     │ • Suggest fixes │
     │                                     └────────┬────────┘
     │                                              │
     │                                              ▼
     │                                     ┌─────────────────┐
     │  HTTP Response (markdown review)    │  Response       │
     └─────────────────────────────────────│  Formatting     │
                                           └─────────────────┘
```

---

## Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPLOYMENT VIEW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                      User Machine / Server                         │    │
│   │                                                                    │    │
│   │  ┌─────────────────────────────────────────────────────────────┐  │    │
│   │  │                    Docker / Process                          │  │    │
│   │  │                                                              │  │    │
│   │  │   ┌─────────────────────┐   ┌─────────────────────┐        │  │    │
│   │  │   │   Frontend (Vite)   │   │   Backend (uvicorn) │        │  │    │
│   │  │   │                     │   │                     │        │  │    │
│   │  │   │ Port: 5173          │   │ Port: 8000          │        │  │    │
│   │  │   │ Static files + SPA  │   │ FastAPI + WebSocket │        │  │    │
│   │  │   └─────────────────────┘   └──────────┬──────────┘        │  │    │
│   │  │                                        │                    │  │    │
│   │  │                             ┌──────────┴──────────┐        │  │    │
│   │  │                             │                     │        │  │    │
│   │  │                             ▼                     ▼        │  │    │
│   │  │                 ┌─────────────────┐   ┌─────────────────┐ │  │    │
│   │  │                 │   eidolon.db    │   │  Project Files  │ │  │    │
│   │  │                 │   (SQLite)      │   │  (Codebase)     │ │  │    │
│   │  │                 └─────────────────┘   └─────────────────┘ │  │    │
│   │  └──────────────────────────────────────────────────────────────┘  │    │
│   │                                                                    │    │
│   │   Environment Variables:                                           │    │
│   │   • ANTHROPIC_API_KEY          • OPENAI_API_KEY                   │    │
│   │   • OPENAI_BASE_URL            • OPENAI_MODEL                     │    │
│   │   • LLM_PROVIDER               (anthropic|openai)                 │    │
│   │                                                                    │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                        External Services                           │    │
│   │                                                                    │    │
│   │   ┌─────────────────────┐       ┌─────────────────────┐          │    │
│   │   │   Anthropic API     │       │  OpenRouter / OpenAI │          │    │
│   │   │   (api.anthropic.com)│      │                      │          │    │
│   │   └─────────────────────┘       └─────────────────────┘          │    │
│   │                                                                    │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   Monitoring (Optional):                                                    │
│   • /metrics → Prometheus scrape                                           │
│   • /health, /health/ready, /health/live → Kubernetes probes              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **SQLite for storage** | Simple, file-based, no separate DB server | Limited concurrent writes, no horizontal scaling |
| **WebSocket for real-time** | Push updates vs polling | Connection management complexity |
| **Pinia for state** | Vue 3 native, reactive, simple | Frontend-only state (no server sync) |
| **LLM abstraction layer** | Multi-provider flexibility | Additional abstraction overhead |
| **Circuit breaker pattern** | Fail-fast on API issues | Adds complexity, needs tuning |
| **Content-addressed cache** | Automatic invalidation on file change | File hashing on every lookup |
| **Hierarchical decomposition** | Granular task breakdown | Deep call stacks, potential complexity |

---

## Diagram Confidence: HIGH

All diagrams derived from direct code analysis and verified against actual file structure and imports.

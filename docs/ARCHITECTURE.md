# MONAD Architecture

## Overview

MONAD implements a hierarchical agent system where AI agents analyze code at multiple abstraction levels, with findings flowing upward to create a unified system-level perspective.

## Core Principles

### 1. Recursive Hierarchy

```
System Agent
  ├─> Module Agent (file 1)
  │     ├─> Function Agent
  │     └─> Function Agent
  └─> Module Agent (file 2)
        └─> Function Agent
```

Each level:
- Analyzes its specific scope
- Deploys child agents for sub-components
- Synthesizes child findings into higher-level insights
- Creates cards representing actionable items

### 2. Card-Based Work Items

Everything is a card. Cards represent:
- Review findings from Explore
- Code changes from Code
- Architecture decisions from Plan
- Test requirements from Test
- Bug reports from Repair
- Requirements from Design

Cards can be:
- **Broken down** → spawn child cards
- **Routed** → moved between tabs
- **Linked** → to code, tests, docs
- **Tracked** → full audit log

### 3. Agent Transparency

Every agent exposes:
- **Messages** → Full conversation with Claude API
- **Tokens** → Usage and cost tracking
- **Snapshots** → Code and data analyzed
- **Findings** → Structured results
- **Graph** → Parent/child relationships

## System Architecture

### Backend (Python/FastAPI)

#### Components

**1. Data Models** (`backend/models/`)
- `Card`: Work item with metadata, links, metrics, audit log
- `Agent`: AI agent with session history and findings

**2. Storage Layer** (`backend/storage/`)
- SQLite database for MVP
- Async operations with aiosqlite
- Automatic ID generation
- Full CRUD for cards and agents

**3. Code Analysis** (`backend/analysis/`)
- AST parsing for Python files
- Complexity calculation
- Code smell detection
- Module/function extraction

**4. Agent Orchestration** (`backend/agents/`)
- Hierarchical deployment (System → Module → Function)
- Claude API integration
- Parallel analysis where possible
- Finding aggregation and synthesis

**5. API Layer** (`backend/api/`)
- REST endpoints for cards and agents
- WebSocket for real-time updates
- Analysis triggering
- Hierarchy visualization

#### Flow: Analysis

```
1. User requests analysis for path
2. Create System agent
3. Scan directory for Python files
4. For each file:
   a. Create Module agent
   b. Extract functions/classes via AST
   c. For each function:
      - Create Function agent
      - Analyze with Claude API
      - Generate findings and cards
   d. Synthesize module-level insights
   e. Create module card
5. Synthesize system-level insights
6. Create system architecture card
7. Broadcast completion via WebSocket
```

### Frontend (Vue 3)

#### Components

**1. Layout**
- `TopNav`: Tab navigation
- `LeftDock`: Drag targets for routing
- `RightDrawer`: Card details and agent snoop

**2. Views**
- `ExploreView`: Analysis triggering and review cards
- `CodeView`: Code change proposals
- `PlanView`: Architecture decisions

**3. Components**
- `CardTile`: Card visualization with drag support
- `AgentSnoop`: Agent session inspector
- `AgentTree`: Hierarchical visualization
- `TreeNode`: Recursive tree rendering

**4. State Management (Pinia)**
- Cards collection
- Agents collection
- Selected card/agent
- WebSocket message handling

#### Flow: Card Interaction

```
1. User clicks card
2. selectedCard state updates
3. RightDrawer opens
4. User switches to "Agent Snoop" tab
5. Load agent data from API
6. Display messages, findings, snapshots
7. User clicks "Route Card"
8. API call to update routing
9. WebSocket broadcasts update
10. All clients receive and update UI
```

## Data Model

### Card Schema

```json
{
  "id": "MONAD-2024-REV-0001",
  "type": "Review|Change|Architecture|Test|Defect|Requirement",
  "title": "string",
  "summary": "markdown",
  "status": "New|Queued|In-Analysis|Proposed|In-Review|Approved|Blocked|Done",
  "priority": "P0|P1|P2|P3",
  "owner_agent": "AGN-MOD-0001",
  "parent": "card-id|null",
  "children": ["card-id", ...],
  "links": {
    "code": ["path:line", ...],
    "tests": ["suite::case", ...],
    "docs": ["doc-id", ...]
  },
  "metrics": {
    "risk": 0.0-1.0,
    "confidence": 0.0-1.0,
    "coverage_impact": 0.0
  },
  "log": [
    {
      "timestamp": "ISO8601",
      "actor": "user|agent-id",
      "event": "description",
      "diff": {}
    }
  ],
  "routing": {
    "from_tab": "Explore",
    "to_tab": "Code"
  }
}
```

### Agent Schema

```json
{
  "id": "AGN-FUN-0042",
  "scope": "System|Module|Class|Function",
  "target": "path::function_name",
  "status": "Idle|Analyzing|Reporting|Completed|Error",
  "parent_id": "agent-id|null",
  "children_ids": ["agent-id", ...],
  "session_id": "session-uuid",
  "messages": [
    {
      "timestamp": "ISO8601",
      "role": "user|assistant|system",
      "content": "text",
      "tokens_in": 1234,
      "tokens_out": 567,
      "tool_calls": ["tool_name", ...],
      "latency_ms": 1234.56
    }
  ],
  "snapshots": [
    {
      "timestamp": "ISO8601",
      "type": "file_diff|ast_extract|test_run",
      "data": {}
    }
  ],
  "findings": ["finding 1", "finding 2"],
  "cards_created": ["card-id", ...],
  "total_tokens": 12345,
  "total_cost": 0.15
}
```

## API Endpoints

### Cards

- `GET /api/cards` → List all cards with filters
- `GET /api/cards/{id}` → Get card details
- `PUT /api/cards/{id}` → Update card
- `DELETE /api/cards/{id}` → Delete card

### Agents

- `GET /api/agents` → List all agents
- `GET /api/agents/{id}` → Get agent details (snoop)
- `GET /api/agents/{id}/hierarchy` → Get hierarchy tree

### Analysis

- `POST /api/analyze` → Start codebase analysis
  ```json
  { "path": "/path/to/code" }
  ```

### WebSocket

- `WS /api/ws` → Real-time updates

Messages:
- `card_updated` → Card changed
- `card_deleted` → Card removed
- `analysis_started` → Analysis began
- `analysis_completed` → Analysis finished
- `analysis_error` → Analysis failed

## Extensibility

### Adding New Agent Scopes

1. Add scope to `AgentScope` enum
2. Implement deployment logic in `AgentOrchestrator`
3. Update hierarchy visualization in frontend

### Adding New Card Types

1. Add type to `CardType` enum
2. Create corresponding view tab
3. Add routing logic
4. Update card tile styling

### Adding Language Support

1. Create analyzer for language in `backend/analysis/`
2. Update `analyze_directory` to detect file types
3. Deploy appropriate agents based on language

### Adding AI Capabilities

1. Extend agent prompts in orchestrator
2. Add new tool use if needed
3. Update card schema for new metrics
4. Visualize in frontend

## Performance Considerations

### MVP Scale

- Up to 100 files
- Up to 1000 functions
- Parallel function analysis
- Sequential module synthesis

### Future Optimizations

- Agent pooling and reuse
- Incremental analysis (only changed files)
- Caching of AST and metrics
- Background processing queue
- Result streaming for large codebases

## Security

### MVP Considerations

- API key stored in environment
- No authentication (local use only)
- No input sanitization (trusted code only)
- No rate limiting

### Production Requirements

- Multi-user authentication
- Role-based access control
- Input validation and sanitization
- Rate limiting on API calls
- Secret management (vault integration)
- Audit logging for compliance

## Testing Strategy

### Unit Tests

- Card and Agent model validation
- Code analyzer correctness
- API endpoint responses

### Integration Tests

- Full analysis flow
- WebSocket communication
- Card routing and updates

### E2E Tests

- Frontend interactions
- Complete user workflows
- Error handling

## Deployment

### Development

- Backend: `uvicorn` with reload
- Frontend: `vite` dev server
- SQLite file database

### Production (Future)

- Backend: Docker container with gunicorn
- Frontend: Static build served via CDN
- Database: PostgreSQL
- Message queue: Redis for WebSocket scaling
- Reverse proxy: Nginx
- Monitoring: Prometheus + Grafana

# Eidolon Orchestration UI Architecture

## Overview

Real-time web UI for monitoring agent orchestration, showing:
- Agent spawning and lifecycle
- Message flow between agents
- Analysis results with severity color coding
- File upload and analysis triggering
- Workspace inspection

## Stack

- **Frontend**: Vue 3 + Vite + TailwindCSS
- **Backend**: FastAPI with WebSockets
- **Real-time**: Server-Sent Events (SSE) for updates
- **Visualization**: D3.js for agent graph

## Architecture

```
┌─────────────────────────────────────┐
│         Vue Frontend                │
│  ┌──────────┐  ┌─────────────────┐ │
│  │  Agent   │  │  Message Feed   │ │
│  │  Graph   │  │  (Real-time)    │ │
│  └──────────┘  └─────────────────┘ │
│  ┌──────────┐  ┌─────────────────┐ │
│  │  File    │  │  Findings       │ │
│  │  Upload  │  │  (Color-coded)  │ │
│  └──────────┘  └─────────────────┘ │
└──────────┬──────────────────────────┘
           │ WebSocket/SSE
           │
┌──────────▼──────────────────────────┐
│      FastAPI Backend                │
│  ┌──────────────────────────────┐  │
│  │  Orchestrator Wrapper        │  │
│  │  - Spawns agents             │  │
│  │  - Streams events            │  │
│  │  - Manages sessions          │  │
│  └──────────────────────────────┘  │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│   Agent Orchestrator (Python)       │
│  - AgentOrchestrator                │
│  - Message logging                  │
│  - Workspace management             │
└─────────────────────────────────────┘
```

## Features

### 1. Agent Visualization
- **Node graph** showing all active agents
- **Edges** showing message flow
- **Status indicators**: spawning, active, completed, failed
- **Agent details** on hover/click

### 2. Message Feed
- **Real-time stream** of all messages
- **Collapsible** message content
- **Searchable** and filterable
- **Timestamp** and agent names

### 3. Findings Panel
- **Color-coded by severity**:
  - 🔴 Critical (red)
  - 🟡 High (yellow)
  - 🟢 Medium (green)
  - 🔵 Low (blue)
- **Expandable details**
- **Link to code location**
- **Suggested fixes**

### 4. File Upload
- **Drag & drop** interface
- **Multiple file support**
- **Progress indicator**
- **Auto-trigger analysis**

### 5. Controls
- **Start/Pause/Stop** orchestration
- **Configuration** (agent count, complexity threshold)
- **Export** results as JSON
- **Download** refactored code

## API Endpoints

```
GET  /api/status                 - Orchestrator status
POST /api/analyze                - Start analysis
GET  /api/agents                 - List active agents
GET  /api/messages               - Get message history
GET  /api/findings               - Get analysis findings
GET  /api/workspace/{agent_id}   - Agent workspace files
WS   /ws/events                  - Real-time event stream
```

## Event Types

```typescript
type Event =
  | { type: "agent_spawned", agent_id: string, role: string }
  | { type: "message_sent", from: string, to: string, content: string }
  | { type: "finding_detected", severity: Severity, details: Finding }
  | { type: "agent_completed", agent_id: string, result: any }
  | { type: "analysis_complete", summary: Summary }
```

## UI Layout

```
┌────────────────────────────────────────────────────────┐
│  Eidolon Orchestrator                    [Settings] ⚙️  │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────┐│
│  │   Agent Graph       │  │   Message Feed           ││
│  │                     │  │                          ││
│  │  ●──→ ● ──→ ●      │  │  [analyzer-1 → orchestr] ││
│  │  ↓     ↓     ↓     │  │   "Analyzing function..." ││
│  │  ● ←── ● ←── ●     │  │                          ││
│  │                     │  │  [orchestr → refactor-1] ││
│  │  6 agents active    │  │   "Refactor process_ord" ││
│  └─────────────────────┘  │                          ││
│                            │  🔍 Search messages...    ││
│  ┌─────────────────────┐  └──────────────────────────┘│
│  │   Findings          │                              │
│  │                     │  ┌──────────────────────────┐│
│  │  🔴 Critical (2)    │  │   File Upload            ││
│  │  🟡 High (5)        │  │                          ││
│  │  🟢 Medium (8)      │  │   [Drag & Drop Zone]     ││
│  │  🔵 Low (12)        │  │   or click to browse     ││
│  │                     │  │                          ││
│  │  Details ▼          │  │  [Start Analysis] 🚀     ││
│  └─────────────────────┘  └──────────────────────────┘│
│                                                         │
└────────────────────────────────────────────────────────┘
```

## Color Coding

```css
/* Severity colors */
.critical {
  background: #fee2e2;
  border-left: 4px solid #dc2626;
}

.high {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
}

.medium {
  background: #d1fae5;
  border-left: 4px solid #10b981;
}

.low {
  background: #dbeafe;
  border-left: 4px solid #3b82f6;
}

/* Agent status */
.agent-spawning { fill: #f59e0b; }
.agent-active { fill: #10b981; }
.agent-completed { fill: #6b7280; }
.agent-failed { fill: #dc2626; }
```

## Data Models

```typescript
interface Agent {
  id: string;
  role: string;
  status: 'spawning' | 'active' | 'completed' | 'failed';
  workspace: string;
  message_count: number;
  created_at: string;
}

interface Message {
  id: string;
  timestamp: string;
  from_agent: string;
  to_agent: string;
  content: string;
  type: 'task' | 'result' | 'error';
}

interface Finding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  type: 'bug' | 'security' | 'performance' | 'style';
  description: string;
  file_path: string;
  line_number: number;
  suggested_fix?: string;
  agent_id: string;
}

interface AnalysisSession {
  id: string;
  file_path: string;
  started_at: string;
  status: 'running' | 'completed' | 'failed';
  agents: Agent[];
  messages: Message[];
  findings: Finding[];
}
```

## Implementation Steps

1. ✅ Design architecture
2. Create FastAPI backend with WebSocket support
3. Build Vue frontend with Vite
4. Implement agent graph visualization
5. Add message feed with real-time updates
6. Create findings panel with color coding
7. Add file upload functionality
8. Connect to orchestrator
9. Add export/download features
10. Polish UX and add animations

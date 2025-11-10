# Component Architecture Diagram

Visual representation of the Eidolon Orchestrator UI component structure.

## Component Tree

```
┌─────────────────────────────────────────────────────────────────────┐
│                            App.vue                                  │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Header                                                        │ │
│  │  - Title: "Eidolon Orchestrator"                             │ │
│  │  - Connection status (WebSocket)                             │ │
│  │  - Actions: Clear All, Upload File                           │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────┬──────────────────────────────────────────────┐   │
│  │              │                                               │   │
│  │  FileQueue   │     OrchestrationView                        │   │
│  │  (Sidebar)   │     (Main Panel)                             │   │
│  │              │                                               │   │
│  │  ┌────────┐  │  ┌──────────────────────────────────────┐   │   │
│  │  │ File 1 │  │  │  Session Header                      │   │   │
│  │  │ ●●●●●░░│  │  │  - Filename, Started time            │   │   │
│  │  │ 🟡 5   │  │  │  - Status, Agent count, Msgs         │   │   │
│  │  └────────┘  │  └──────────────────────────────────────┘   │   │
│  │              │                                               │   │
│  │  ┌────────┐  │  ┌──────────────────────────────────────┐   │   │
│  │  │ File 2 │  │  │  Module Override Alert               │   │   │
│  │  │ ●●●●●●●│  │  │  ⚠️  Module overrides functions      │   │   │
│  │  │ ✓ Done │  │  └──────────────────────────────────────┘   │   │
│  │  └────────┘  │                                               │   │
│  │              │  ┌───────────────┬──────────────────────┐   │   │
│  │  [Filters]   │  │ Agent Flow    │  Message Feed        │   │   │
│  │  All  Active │  │               │                      │   │   │
│  │  Complete    │  │ ┌──────────┐  │  [analyzer-1 →]     │   │   │
│  │  Failed      │  │ │🤖 Agent 1│  │   "Analyzing..."    │   │   │
│  │              │  │ │ Active   │  │                      │   │   │
│  │              │  │ └──────────┘  │  [orchestrator →]    │   │   │
│  │              │  │               │   "Processing..."    │   │   │
│  │              │  │ ┌──────────┐  │                      │   │   │
│  │              │  │ │🤖 Agent 2│  │  [refactor-1 →]     │   │   │
│  │              │  │ │ Complete │  │   "Refactored"      │   │   │
│  │              │  │ └──────────┘  │                      │   │   │
│  │              │  └───────────────┴──────────────────────┘   │   │
│  └──────────────┴──────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FindingsPanel (Bottom Panel - Collapsible)                 │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │ Header: Findings (27) 🔴 2  🟡 8  🟢 12  🔵 5          │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │ 🔴 CRITICAL (2) ▼                                      │ │   │
│  │  │ ├─ SQL Injection risk in query_builder (line 45)      │ │   │
│  │  │ │  💡 Use parameterized queries                        │ │   │
│  │  │ └─ Unhandled exception in process_data (line 102)     │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │ 🟡 HIGH (8) ▼                                          │ │   │
│  │  │ ├─ High complexity (18) in process_order              │ │   │
│  │  │ │  💡 Refactor suggested                               │ │   │
│  │  │ └─ ...                                                 │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  FileUploadModal (Overlay - Conditional)                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Upload File for Analysis                              [X]   │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  ┌───────────────────────────────────────────────────────┐ │   │
│  │  │           📤                                          │ │   │
│  │  │   Drag and drop your Python file here                │ │   │
│  │  │              or                                       │ │   │
│  │  │        [Browse Files]                                 │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  │                                                              │   │
│  │  Selected: example.py (15.2 KB)                             │   │
│  │                                                              │   │
│  │  Complexity Threshold: [====●====] 10                       │   │
│  │  Max Parallel Agents:  [5 agents ▼]                         │   │
│  │                                                              │   │
│  │                          [Cancel] [Start Analysis]           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        State Management (Pinia)                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  orchestration.ts                                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │   State     │  │  Computed   │  │   Actions   │         │   │
│  │  │             │  │             │  │             │         │   │
│  │  │ - files     │  │ - current   │  │ - connect   │         │   │
│  │  │ - agents    │  │   Session   │  │   WebSocket │         │   │
│  │  │ - messages  │  │ - findings  │  │ - selectFile│         │   │
│  │  │ - findings  │  │   BySeverity│  │ - addFile   │         │   │
│  │  │ - sessions  │  │ - active    │  │ - clearAll  │         │   │
│  │  │ - wsStatus  │  │   Files     │  │             │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────────────┐
│                          Backend APIs                               │
│  ┌──────────────────────┐         ┌──────────────────────┐         │
│  │   HTTP (Axios)       │         │   WebSocket          │         │
│  │                      │         │                      │         │
│  │ GET  /api/status     │         │ ws://localhost:8000  │         │
│  │ POST /api/analyze    │         │      /ws/events      │         │
│  │ POST /api/upload     │         │                      │         │
│  │ GET  /api/agents     │         │ Events:              │         │
│  │ GET  /api/messages   │         │ - agent_spawned      │         │
│  │ GET  /api/findings   │         │ - message_sent       │         │
│  │                      │         │ - finding_detected   │         │
│  │                      │         │ - analysis_complete  │         │
│  └──────────────────────┘         └──────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Communication

```
┌──────────────────┐
│     App.vue      │
│  (Root Component)│
└────────┬─────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
         ▼                                 ▼
┌──────────────────┐           ┌──────────────────────┐
│  FileQueue.vue   │           │ OrchestrationView.vue│
│                  │           │                      │
│  Props: none     │           │  Props:              │
│                  │           │  - sessionId         │
│  Emits:          │           │                      │
│  - selectFile    │           │  Emits: none         │
└──────────────────┘           └──────────────────────┘

         │                                 │
         └─────────────────┬───────────────┘
                           ▼
                 ┌──────────────────┐
                 │ FindingsPanel.vue│
                 │                  │
                 │  Props:          │
                 │  - expanded      │
                 │                  │
                 │  Emits:          │
                 │  - toggle        │
                 └──────────────────┘

┌──────────────────────┐
│ FileUploadModal.vue  │
│  (Conditional)       │
│                      │
│  Props: none         │
│                      │
│  Emits:              │
│  - close             │
│  - upload            │
└──────────────────────┘
```

## Store Integration

```
┌───────────────────────────────────────────────────────────────┐
│                    Components                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │FileQueue │  │Orchestr. │  │Findings  │  │Upload    │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │              │             │           │
│       └─────────────┴──────────────┴─────────────┘           │
│                          │                                    │
└──────────────────────────┼────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│              useOrchestrationStore()                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  State (Reactive)                                       │  │
│  │  - files: FileAnalysis[]                               │  │
│  │  - agents: Agent[]                                     │  │
│  │  - messages: Message[]                                 │  │
│  │  - findings: Finding[]                                 │  │
│  │  - sessions: Map<string, AnalysisSession>              │  │
│  │  - currentSessionId: string | null                     │  │
│  │  - orchestratorStatus: OrchestratorStatus              │  │
│  │  - wsConnected: boolean                                │  │
│  │  - wsError: string | null                              │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Computed                                               │  │
│  │  - currentSession                                       │  │
│  │  - findingsBySeverity                                   │  │
│  │  - activeFiles                                          │  │
│  │  - completedFiles                                       │  │
│  │  - failedFiles                                          │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Actions                                                │  │
│  │  - connectWebSocket()                                   │  │
│  │  - disconnectWebSocket()                                │  │
│  │  - handleWebSocketEvent(event)                          │  │
│  │  - selectFile(id)                                       │  │
│  │  - addFile(file)                                        │  │
│  │  - updateFileProgress(id, progress)                     │  │
│  │  - clearAll()                                           │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Event Flow

```
Backend Event → WebSocket → Store Handler → State Update → Component Re-render

Example: Finding Detected

1. Backend: Finding detected
   ↓
2. WebSocket: { type: "finding_detected", sessionId, finding }
   ↓
3. Store: handleFindingDetected(sessionId, finding)
   ↓
4. Store: findings.value.push(finding)
   ↓
5. FindingsPanel: Reactively updates with new finding
   ↓
6. FileQueue: Badge count updates
   ↓
7. User: Sees new finding appear in real-time
```

## Lifecycle

```
Application Startup:
1. main.ts creates app
2. App.vue mounts
3. onMounted() → store.connectWebSocket()
4. WebSocket connects
5. Initial API calls (status, agents, etc.)
6. Components render with empty state

File Upload:
1. User clicks "Upload File"
2. FileUploadModal opens
3. User selects file and configures
4. POST /api/upload (file)
5. POST /api/analyze (config)
6. Backend returns session_id
7. analysis_started event received
8. FileQueue updates with new file
9. Real-time events stream in
10. UI updates automatically

Analysis Complete:
1. analysis_complete event received
2. Store updates file status
3. FileQueue shows green check
4. FindingsPanel populated
5. User reviews findings
```

## Styling Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Styling Layers                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  TailwindCSS (Base)                                    │ │
│  │  - Utility classes                                     │ │
│  │  - Responsive breakpoints                              │ │
│  │  - Custom theme (tailwind.config.js)                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Global Styles (style.css)                             │ │
│  │  - @layer base (resets)                                │ │
│  │  - @layer components (reusable)                        │ │
│  │    • .severity-dot, .status-dot                        │ │
│  │    • .card, .btn, .badge                               │ │
│  │  - Custom animations                                   │ │
│  │  - Scrollbar styling                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Component Styles (scoped)                             │ │
│  │  - Component-specific overrides                        │ │
│  │  - Dynamic class bindings                              │ │
│  │  - Computed style objects                              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
ui/
├── Configuration & Build
│   ├── package.json          (Dependencies)
│   ├── vite.config.ts        (Build config)
│   ├── tailwind.config.js    (Styles)
│   ├── postcss.config.js     (CSS processing)
│   ├── tsconfig.json         (TypeScript)
│   └── index.html            (Entry point)
│
├── Source Code
│   ├── main.ts               (Bootstrap)
│   ├── App.vue               (Root)
│   ├── style.css             (Global styles)
│   │
│   ├── components/
│   │   ├── FileQueue.vue
│   │   ├── OrchestrationView.vue
│   │   ├── FindingsPanel.vue
│   │   └── FileUploadModal.vue
│   │
│   ├── stores/
│   │   └── orchestration.ts
│   │
│   ├── services/
│   │   └── api.ts
│   │
│   └── types/
│       └── index.ts
│
└── Documentation
    ├── README.md             (Main docs)
    ├── QUICKSTART.md         (Getting started)
    ├── INSTALLATION.md       (Setup)
    ├── TESTING.md            (Test guide)
    ├── DEVELOPMENT.md        (Dev notes)
    ├── ARCHITECTURE.md       (System design)
    ├── UX_DESIGN.md          (UX specs)
    ├── PROJECT_SUMMARY.md    (Overview)
    └── COMPONENT_DIAGRAM.md  (This file)
```

## Key Interactions

### 1. File Selection
```
User clicks file card in FileQueue
  ↓
FileQueue emits 'selectFile' event
  ↓
App.vue calls handleSelectFile(fileId)
  ↓
Store updates currentSessionId
  ↓
OrchestrationView receives new sessionId prop
  ↓
OrchestrationView renders session details
```

### 2. Real-time Finding
```
Backend detects finding
  ↓
WebSocket sends finding_detected event
  ↓
Store handleFindingDetected()
  ↓
findings array updated (reactive)
  ↓
FindingsPanel re-renders
  ↓
FileQueue badge updates
  ↓
User sees new finding instantly
```

### 3. File Upload
```
User drags file to modal
  ↓
FileUploadModal handles drop
  ↓
User clicks "Start Analysis"
  ↓
Modal uploads file via API
  ↓
Modal starts analysis via API
  ↓
analysis_started event received
  ↓
Store adds file to queue
  ↓
FileQueue displays new file
  ↓
Modal closes
```

This diagram represents the complete component architecture and data flow of the Eidolon Orchestrator UI.

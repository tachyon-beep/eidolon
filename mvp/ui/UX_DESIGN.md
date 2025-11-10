# Eidolon Orchestrator - UX Design

## Design Philosophy

**"At-a-glance understanding, drill-down for details"**

Users should instantly see:
1. Which files are being analyzed
2. Overall health status (color-coded)
3. Which agents are working on what
4. Hierarchical assessment flow (function → module → system)

## Layout: Three-Panel Master-Detail

```
┌────────────────────────────────────────────────────────────────────┐
│  Eidolon Orchestrator                    [⚙️ Settings] [📤 Export] │
├──────────┬─────────────────────────────────────────────────────────┤
│          │                                                          │
│  FILES   │             ORCHESTRATION VIEW                          │
│  QUEUE   │                                                          │
│          │     ┌──────────────────────────────────────┐            │
│ ┌──────┐ │     │  Module Assessment: networks.py      │            │
│ │●  🔴 │ │     │  Status: ⚠️  Needs Refactoring      │            │
│ │net...│ │     └──────────────────────────────────────┘            │
│ └──────┘ │                                                          │
│          │     ┌───────────┐    ┌───────────┐   ┌──────────┐      │
│ ┌──────┐ │     │  Func 1   │───▶│  Analyze  │──▶│ Function │      │
│ │   🟡 │ │     │  ✅ Green  │    │  Agent    │   │ Agent    │      │
│ │ord...│ │     └───────────┘    └───────────┘   └──────────┘      │
│ └──────┘ │            │                                             │
│          │            ▼                                             │
│ ┌──────┐ │     ┌───────────┐    ┌───────────┐                    │
│ │   🟢 │ │     │  Func 2   │───▶│  Analyze  │                    │
│ │uti...│ │     │  🟡 Yellow │    │  Agent    │                    │
│ └──────┘ │     └───────────┘    └───────────┘                    │
│          │            │                                             │
│  [+Add]  │            ▼                                             │
│          │     ┌─────────────────────────────────┐                │
│          │     │  Module Agent Assessment        │                │
│          │     │  ⚠️  "Func2 high complexity"    │                │
│          │     │  💡 Suggests refactoring        │                │
│          │     └─────────────────────────────────┘                │
│          │                                                          │
│          │     FINDINGS  [27] ──────────────────────────────────  │
│          │     🔴 Critical (2)  🟡 High (8)  🟢 Medium (12)        │
│          │                                                          │
└──────────┴─────────────────────────────────────────────────────────┘
```

## Key UX Decisions

### 1. File Queue (Left Sidebar)

**Visual Language:**
- **Circle status indicator** (colored dot)
- **Filename** (truncated if needed)
- **Real-time progress bar** during analysis
- **Assessment badge** when complete

**Color System:**
- 🔴 **Red**: Critical issues, needs immediate attention
- 🟡 **Yellow**: Moderate issues, should refactor
- 🟢 **Green**: Good quality, minor or no issues
- ⚫ **Gray**: Queued, not yet analyzed
- 🔵 **Blue**: Currently analyzing

**Interaction:**
- Click to view details in main panel
- Hover shows quick summary tooltip
- Drag to reorder queue
- Right-click for context menu (re-analyze, remove, export)

### 2. Orchestration View (Main Panel)

**Hierarchical Flow Visualization:**

```
FUNCTION LEVEL           ANALYSIS         MODULE LEVEL
┌─────────────┐        ┌──────────┐     ┌──────────────┐
│ Function 1  │───────▶│ Analyzer │────▶│              │
│ Complexity:8│        │ Agent-1  │     │   Module     │
│ ✅ PASS     │        └──────────┘     │  Assessment  │
└─────────────┘                         │              │
                                        │ ⚠️  REFACTOR │
┌─────────────┐        ┌──────────┐     │              │
│ Function 2  │───────▶│ Analyzer │────▶│  (Overrides  │
│ Complex: 15 │        │ Agent-2  │     │   func1-3)   │
│ ⚠️  WARN    │        └──────────┘     │              │
└─────────────┘                         └──────────────┘
       │
       ├──▶ SUGGESTS REFACTOR
       └──▶ Shows sub-function plan
```

**Key Features:**
- **Animated message flow** (arrows show data flow)
- **Agent cards** show what they're thinking
- **Hierarchical override** visualization
  - Function says Green ✅
  - Module says Yellow ⚠️
  - Module wins → Overall Yellow ⚠️
  - Show reason for override

### 3. Findings Panel (Bottom)

**Grouped by Severity:**
```
┌──────────────────────────────────────────────────────────┐
│ FINDINGS (27)                                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 🔴 CRITICAL (2) ▼                                        │
│ ├─ SQL Injection risk in query_builder (line 45)       │
│ │  Agent: security-auditor-1                           │
│ │  💡 Use parameterized queries                         │
│ │                                                        │
│ └─ Unhandled exception in process_data (line 102)      │
│    Agent: analyzer-2                                    │
│    💡 Add try-except block                               │
│                                                          │
│ 🟡 HIGH (8) ▼                                            │
│ ├─ High complexity (18) in process_order               │
│ │  Agent: complexity-analyzer                          │
│ │  💡 Refactor suggested [View Plan]                    │
│ ...                                                      │
└──────────────────────────────────────────────────────────┘
```

## Interaction Patterns

### Pattern 1: Quick Scan
1. User uploads files
2. File cards appear in queue
3. Progress bars show analysis
4. Color-coded dots update in real-time
5. User scans sidebar for red/yellow
6. Clicks concerning files for details

### Pattern 2: Deep Dive
1. Click file card → Orchestration view loads
2. See agent flow diagram
3. Click agent card → See its specific analysis
4. Click function → See code snippet
5. See module-level override reasoning
6. View suggested fixes

### Pattern 3: Bulk Review
1. Filter sidebar: "Show only red/yellow"
2. Click through each file
3. Mark findings as "Will fix" / "Won't fix"
4. Export report with decisions
5. Download refactored code

## Visual Components

### File Card
```
┌─────────────────────┐
│ ●  networks.py      │ ← Status dot
│ ▓▓▓▓▓▓░░░░ 60%     │ ← Progress bar
│ 🟡 12 findings      │ ← Badge
│ ↻ 2m ago           │ ← Timestamp
└─────────────────────┘
```

### Agent Card
```
┌─────────────────────────────┐
│ 🤖 Analyzer-1               │
│ Status: ✅ Complete         │
│ ───────────────────────────│
│ Analyzed: process_order()  │
│ Complexity: 18             │
│ Assessment: ⚠️  High       │
│ Suggestion: Refactor       │
└─────────────────────────────┘
```

### Hierarchical Override Indicator
```
┌────────────────────────────────────┐
│ ⚠️  MODULE OVERRIDE                │
├────────────────────────────────────┤
│ Function Level:                    │
│  • func1(): ✅ Green               │
│  • func2(): ✅ Green               │
│  • func3(): 🟡 Yellow              │
│                                    │
│ Module Level: ⚠️  Yellow           │
│                                    │
│ Reason: "High coupling between    │
│ functions creates maintenance      │
│ burden even though individual      │
│ functions are simple."             │
│                                    │
│ [View Details] [Accept] [Dismiss] │
└────────────────────────────────────┘
```

## Color Palette

```css
/* Status Colors */
--critical: #DC2626;     /* Red */
--high: #F59E0B;         /* Amber */
--medium: #10B981;       /* Green */
--low: #3B82F6;          /* Blue */
--analyzing: #6366F1;    /* Indigo */
--queued: #6B7280;       /* Gray */

/* Backgrounds */
--bg-critical: #FEE2E2;
--bg-high: #FEF3C7;
--bg-medium: #D1FAE5;
--bg-low: #DBEAFE;

/* UI */
--primary: #7C3AED;      /* Purple */
--secondary: #EC4899;    /* Pink */
--success: #10B981;
--warning: #F59E0B;
--error: #EF4444;
```

## Animations

1. **Message Flow**: Animated arrows show data flowing between agents
2. **Status Updates**: Smooth color transitions as assessment changes
3. **Card Appearance**: Slide-in animation when file added to queue
4. **Finding Reveal**: Expand/collapse with smooth height transition
5. **Agent Activity**: Pulse effect on active agent cards

## Accessibility

- **Keyboard Navigation**: Tab through file cards, agents, findings
- **Screen Reader**: All status indicators have text labels
- **High Contrast Mode**: Supports OS high contrast settings
- **Focus Indicators**: Clear focus rings on all interactive elements

## Mobile Responsive

- **< 768px**: Single column, collapsible sidebar
- **768-1024px**: Side-by-side with narrower sidebar
- **> 1024px**: Full three-panel layout

## Implementation Priority

1. ✅ File queue sidebar with status dots
2. ✅ Basic orchestration view (agent cards)
3. ✅ Message flow visualization
4. ✅ Hierarchical override display
5. ✅ Findings panel with grouping
6. WebSocket real-time updates
7. Drag-and-drop file upload
8. Export functionality
9. Animations and polish
10. Mobile responsive layout

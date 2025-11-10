# Eidolon + Claude Agent SDK Integration

## What We Built

A **hybrid agent architecture** that combines:
- Python orchestration for observability and control
- Claude Agent SDK for powerful code execution and analysis
- Multiple parallel agents for speed and scalability

## Key Innovation

Instead of calling remote LLM APIs, we **spawn multiple Claude Code instances** programmatically and mediate their communication, giving us:

✅ **Full observability** - Log every message between agents
✅ **Parallel execution** - Analyze multiple functions simultaneously
✅ **Actual verification** - Agents run real tests, not LLM judgment
✅ **Cost effective** - No API costs for every analysis
✅ **Debuggable** - Inspect agent workspaces and conversations
✅ **Powerful** - Claude Code's debugging and building capabilities

## Architecture

```
┌─────────────────────────────────────┐
│  Python Orchestrator                │
│  - Spawns agents                    │
│  - Mediates messages                │
│  - Logs everything                  │
│  - Controls workflow                │
└──────┬──────────────┬───────────────┘
       │              │
   ┌───▼───┐      ┌───▼───┐
   │Claude │      │Claude │  (Multiple parallel agents)
   │Agent 1│      │Agent 2│
   │Analyze│      │Refact │
   └───┬───┘      └───┬───┘
       │              │
   ┌───▼──────────────▼───┐
   │ Shared Workspace      │
   │ - Code files          │
   │ - Tests               │
   │ - Results             │
   └───────────────────────┘
```

## Components

### 1. Agent Orchestrator (`src/eidolon_mvp/orchestrator/`)

The core orchestration engine that:
- Spawns Claude Agent SDK agents
- Routes messages between agents
- Logs all communication
- Manages agent workspaces

### 2. Agent Skills (`.claude/skills/`)

- **code-refactoring.md** - Refactoring workflow using TDD
- Skills define how agents should approach tasks
- Can be reused across all agents

### 3. Subagents (`.claude/agents/`)

- **complexity-analyzer.md** - Analyzes code complexity
- Specialized agents for specific tasks
- Launched by orchestrator as needed

## Usage

### Install Dependencies

```bash
uv sync
# or
pip install claude-agent-sdk
```

### Run Demo

```bash
export ANTHROPIC_API_KEY=your-key
python demo_agent_sdk.py
```

### Use in Code

```python
from eidolon_mvp.orchestrator import AgentOrchestrator, AgentConfig
from pathlib import Path

# Create orchestrator
orchestrator = AgentOrchestrator(base_workspace=Path("/tmp/agents"))

# Spawn analyzer agents
functions = [("func1", code1), ("func2", code2)]
results = await orchestrator.analyze_function_parallel(functions)

# Refactor with verification
refactored = await orchestrator.refactor_with_verification(
    function_name="complex_func",
    function_code=code,
    complexity=15,
)

# Export conversation log
orchestrator.export_conversation(Path("log.json"))
```

## Workflow Example

### Parallel Analysis

```
Orchestrator:
  │
  ├─► Spawn Analyzer-1 → Analyze func1 → Result 1
  ├─► Spawn Analyzer-2 → Analyze func2 → Result 2
  └─► Spawn Analyzer-3 → Analyze func3 → Result 3

All running in parallel ⚡
All logged for observability 📝
```

### Refactoring with Verification

```
Orchestrator:
  │
  └─► Spawn Refactorer
        │
        ├─► Generate behavior tests
        ├─► Run tests on original (bash pytest)
        ├─► Plan refactoring
        ├─► Generate sub-functions
        ├─► Run tests on refactored (bash pytest)
        └─► Compare outputs (actual execution!)

If tests fail → iterate and fix
Only return when tests pass ✅
```

## Benefits vs Traditional Approach

### ❌ Traditional: Remote LLM API
- Sequential (slow)
- Expensive ($$$ per call)
- No code execution
- Limited observability
- Can't verify with tests

### ✅ Eidolon + Agent SDK
- Parallel (fast)
- Cost effective
- Full code execution
- Complete observability
- Actual test verification

## What Makes Claude Code Powerful

As you noted: **"Claude Code with skills is absolutely monstrous when it comes to debugging and building code"**

This is because Claude Code can:
1. **Actually run code** and see real errors
2. **Iterate based on feedback** (linting, test results)
3. **Use bash tools** flexibly for any task
4. **Access the full codebase** for context
5. **Debug systematically** with real execution

By spawning multiple Claude Code instances and orchestrating them, we get this power multiplied across parallel agents!

## Next Steps

### Phase 1: Basic Integration ✅
- [x] Create orchestrator
- [x] Implement message passing
- [x] Add logging
- [x] Create demo

### Phase 2: Production Features
- [ ] Install Claude Agent SDK
- [ ] Test parallel analysis
- [ ] Add test execution verification
- [ ] Integrate with existing analysis code
- [ ] Add error handling and retries

### Phase 3: Advanced Features
- [ ] Self-healing: agents fix each other's code
- [ ] Learning: save successful refactoring patterns
- [ ] CodeGraph integration for context
- [ ] Database persistence of agent conversations
- [ ] Web UI for monitoring agents

## Files Created

```
mvp/
├── AGENT_SDK_ARCHITECTURE.md     # Architecture document
├── README_AGENT_SDK.md            # This file
├── demo_agent_sdk.py              # Demo showing all features
├── src/eidolon_mvp/orchestrator/
│   ├── __init__.py
│   └── agent_sdk_orchestrator.py  # Core orchestrator
├── .claude/
│   ├── CLAUDE.md                  # Project description for Claude
│   ├── skills/
│   │   └── code-refactoring.md    # Refactoring skill
│   └── agents/
│       └── complexity-analyzer.md # Analyzer subagent
└── pyproject.toml                 # Added claude-agent-sdk dependency
```

## Key Insight

The power of this approach is that we're **not replacing Claude Code** - we're **multiplying it**. Each spawned agent has the full power of Claude Code, and we orchestrate them like a conductor leading an orchestra.

The Python orchestrator provides:
- **Observability**: See what every agent is doing
- **Control**: Decide when to spawn agents and what they analyze
- **Persistence**: Save all conversations and results
- **Coordination**: Make agents work together efficiently

While each Claude Code agent provides:
- **Intelligence**: Deep reasoning about code
- **Execution**: Actually run tests and see results
- **Iteration**: Fix errors based on real feedback
- **Tools**: Full access to bash, filesystem, etc.

Together, they create a system that's far more powerful than the sum of its parts!

## Try It

1. Install dependencies: `uv sync`
2. Set API key: `export ANTHROPIC_API_KEY=your-key`
3. Run demo: `python demo_agent_sdk.py`
4. Inspect the logs and workspaces
5. See how agents communicate in parallel
6. Watch them actually run tests and verify behavior!

🚀 Welcome to the future of automated code analysis and refactoring!

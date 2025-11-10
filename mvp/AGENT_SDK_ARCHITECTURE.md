# Eidolon + Claude Agent SDK Architecture

## Overview

We use the **Claude Agent SDK** programmatically from Python to spin up multiple Claude Code instances, with our Python application mediating communication for full observability.

## Why This Approach?

### ❌ Pure Claude Code Subagents
- No observability of agent-to-agent communication
- Can't inspect intermediate results
- Hard to debug failures
- Can't persist agent conversations

### ❌ Pure Remote LLM API
- Expensive (API costs)
- Sequential processing (slow)
- No code execution capability
- Manual tool management

### ✅ Hybrid: Python + Claude Agent SDK
- **Full observability**: Log all agent communication
- **Mediated messages**: Control what each agent sees
- **Code execution**: Agents can run tests and verify
- **Parallel processing**: Spin up multiple agents
- **Cost effective**: Use Claude Code SDK (lower cost than API)
- **Debuggable**: Inspect agent reasoning and results

## Architecture

```
┌─────────────────────────────────────────┐
│   Eidolon Orchestrator (Python)         │
│   - Reads codebase                      │
│   - Identifies complex functions        │
│   - Spawns Claude agents                │
│   - Mediates communication              │
│   - Logs everything                     │
│   - Persists to database                │
└──────────┬────────────────┬─────────────┘
           │                │
    ┌──────▼─────┐   ┌─────▼──────┐
    │ Claude     │   │ Claude     │
    │ Agent 1    │   │ Agent 2    │
    │ (Analyzer) │   │ (Refactor) │
    └──────┬─────┘   └─────┬──────┘
           │                │
    ┌──────▼────────────────▼──────┐
    │  Shared Workspace             │
    │  - Code files                 │
    │  - Test files                 │
    │  - Analysis results           │
    └───────────────────────────────┘
```

## Implementation

### Using Claude Agent SDK from Python

```python
from claude_agent_sdk import Agent

# Spawn a Claude agent for analysis
analyzer = Agent(
    name="complexity-analyzer",
    system_prompt=COMPLEXITY_ANALYSIS_PROMPT,
    working_directory="/tmp/eidolon/agent-1",
    allowed_tools=["read", "write", "bash"],
)

# Send task and get result
result = await analyzer.run(
    message=f"Analyze this function:\n\n{function_code}"
)

# Log the interaction
logger.info(f"Agent response: {result}")

# Parse result and pass to next agent
if result.complexity > 10:
    refactorer = Agent(
        name="refactoring-agent",
        system_prompt=REFACTORING_PROMPT,
        working_directory="/tmp/eidolon/agent-2",
    )

    refactored = await refactorer.run(
        message=f"Refactor this function:\n\n{function_code}\n\nComplexity: {result.complexity}"
    )
```

### Agent Communication Protocol

```python
class AgentOrchestrator:
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.message_log: list[Message] = []

    async def spawn_agent(self, role: str, config: AgentConfig) -> Agent:
        """Spawn a new Claude Code agent."""
        agent = Agent(
            name=f"{role}-{uuid4()}",
            system_prompt=config.prompt,
            working_directory=config.workspace,
            allowed_tools=config.tools,
        )
        self.agents[agent.name] = agent
        return agent

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: str
    ) -> str:
        """Send message between agents with logging."""
        # Log the message
        self.message_log.append(Message(
            timestamp=datetime.now(),
            from_agent=from_agent,
            to_agent=to_agent,
            content=message,
        ))

        # Send to target agent
        agent = self.agents[to_agent]
        response = await agent.run(message=message)

        # Log response
        self.message_log.append(Message(
            timestamp=datetime.now(),
            from_agent=to_agent,
            to_agent=from_agent,
            content=response,
        ))

        return response

    async def analyze_module(self, file_path: str) -> ModuleAnalysis:
        """Orchestrate multi-agent analysis of a module."""

        # 1. Spawn analyzer agents (parallel)
        functions = extract_functions(file_path)
        agents = [
            await self.spawn_agent("analyzer", AnalyzerConfig())
            for _ in functions
        ]

        # 2. Analyze in parallel
        analyses = await asyncio.gather(*[
            agent.run(f"Analyze: {func}")
            for agent, func in zip(agents, functions)
        ])

        # 3. For complex functions, spawn refactoring agents
        refactoring_tasks = []
        for analysis, func in zip(analyses, functions):
            if analysis.complexity > 10:
                refactorer = await self.spawn_agent("refactorer", RefactorerConfig())
                task = refactorer.run(f"Refactor: {func}")
                refactoring_tasks.append(task)

        # 4. Execute refactorings in parallel
        refactored = await asyncio.gather(*refactoring_tasks)

        # 5. Spawn verifier agents
        verifiers = [
            await self.spawn_agent("verifier", VerifierConfig())
            for _ in refactored
        ]

        # 6. Verify in parallel with actual test execution
        verified = await asyncio.gather(*[
            verifier.run(f"Verify: {original} vs {refactored}")
            for verifier, original, refactored in zip(verifiers, functions, refactored)
        ])

        return ModuleAnalysis(
            analyses=analyses,
            refactorings=refactored,
            verifications=verified,
            message_log=self.message_log,
        )
```

## Benefits

### 1. **Full Observability**
Every agent interaction is logged:
```python
# View agent conversation
for msg in orchestrator.message_log:
    print(f"{msg.from_agent} → {msg.to_agent}: {msg.content[:100]}...")
```

### 2. **Parallelization**
Spawn multiple agents for independent tasks:
```python
# Analyze 10 functions in parallel with 10 agents
agents = [spawn_agent("analyzer") for _ in range(10)]
results = await asyncio.gather(*[agent.run(func) for agent, func in zip(agents, functions)])
```

### 3. **Test Execution**
Agents can run actual tests:
```python
# Agent receives task
agent.run("""
Refactor this function and verify:
1. Generate pytest tests
2. Run tests on original (should pass)
3. Generate refactored version
4. Run tests on refactored (should pass)
5. Compare outputs (should match)
""")
```

### 4. **Workspace Isolation**
Each agent has its own workspace:
```
/tmp/eidolon/
  agent-1/  # Analyzer workspace
    input.py
    analysis.json
  agent-2/  # Refactorer workspace
    input.py
    refactored.py
    tests.py
    test_results.txt
  agent-3/  # Verifier workspace
    original.py
    refactored.py
    comparison.json
```

### 5. **State Management**
Orchestrator manages state:
```python
# Save state to database
await db.save_analysis(
    file_path=file_path,
    analyses=analyses,
    refactorings=refactorings,
    agent_log=orchestrator.message_log,
    timestamp=datetime.now(),
)

# Resume from saved state
state = await db.load_analysis(file_path)
orchestrator.restore_state(state)
```

## Implementation Plan

### Phase 1: Basic Integration
1. Install Claude Agent SDK: `pip install claude-agent-sdk`
2. Create wrapper for spawning agents
3. Implement message passing with logging
4. Test with simple analysis task

### Phase 2: Parallel Analysis
1. Spawn multiple analyzer agents
2. Distribute functions across agents
3. Collect and aggregate results
4. Add performance monitoring

### Phase 3: Refactoring Pipeline
1. Analyzer → Refactorer → Verifier pipeline
2. Actual test execution in verifier
3. Iteration loop for failed tests
4. Result persistence

### Phase 4: Advanced Features
1. Agent specialization (security, performance, style)
2. CodeGraph integration for context
3. Self-healing: agents fix each other's mistakes
4. Learning: save successful patterns

## Configuration

```python
# config.py
AGENT_CONFIG = {
    "analyzer": {
        "system_prompt": COMPLEXITY_ANALYSIS_PROMPT,
        "tools": ["read", "bash"],
        "max_agents": 10,  # Parallel limit
    },
    "refactorer": {
        "system_prompt": REFACTORING_PROMPT,
        "tools": ["read", "write", "bash"],
        "max_agents": 5,
    },
    "verifier": {
        "system_prompt": VERIFICATION_PROMPT,
        "tools": ["read", "bash"],
        "max_agents": 5,
    },
}
```

## Monitoring & Debugging

### View Agent Activity
```python
# Real-time monitoring
orchestrator.on_message(lambda msg: print(f"{msg.from_agent}: {msg.content}"))

# Post-analysis debugging
for agent_name, agent in orchestrator.agents.items():
    print(f"\n{agent_name} activity:")
    print(f"  Messages sent: {agent.message_count}")
    print(f"  Tools used: {agent.tool_usage}")
    print(f"  Errors: {agent.error_count}")
```

### Export Conversation
```python
# Export to JSON for analysis
orchestrator.export_conversation("analysis_log.json")

# View in web UI
orchestrator.start_debug_server(port=8000)
# → http://localhost:8000/agents/analyzer-123/conversation
```

## Summary

This hybrid approach gives us:
- ✅ **Observability**: Full visibility into agent communication
- ✅ **Power**: Claude Code's execution and tool capabilities
- ✅ **Control**: Python orchestration and mediation
- ✅ **Parallelization**: Multiple concurrent agents
- ✅ **Cost Effective**: Claude Agent SDK pricing
- ✅ **Debuggable**: Log everything, replay conversations
- ✅ **Persistent**: Save state to database
- ✅ **Testable**: Unit test the orchestrator

Next step: Implement the `AgentOrchestrator` class using the Claude Agent SDK!

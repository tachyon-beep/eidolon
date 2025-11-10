# Eidolon MVP: Hierarchical Agent System with Persistent Memory

## Vision

A hierarchical multi-agent system where agents at different abstraction levels (Module → Function) work together to analyze code, find bugs, and maintain architectural understanding. Each agent has **persistent memory** and can be questioned about its reasoning, creating a conversational, self-correcting code intelligence system.

## Core Innovation

**Agents with Memory**: Unlike stateless LLM interactions, each agent stores its analyses, reasoning, and decisions. When challenged or when new information emerges, agents can:
- Recall their previous reasoning
- Re-analyze with new context
- Correct their mistakes
- Learn from past errors
- Answer questions about their conclusions

## The Problem We Solve

Traditional code review is stateless:
```
Developer: "Is this function safe?"
LLM: "Yes, looks fine"

[2 weeks later, bug found]

Developer: "Why did you say it was safe?"
LLM: "I don't remember that interaction"
```

Our hierarchical agent system with memory:
```
Developer: "Is this function safe?"
FunctionAgent(validate_token):
  *analyzes, stores reasoning*
  "Yes, checked all edge cases. See analysis #123"

[2 weeks later]

DataAgent: "Getting invalid tokens from validate_token"
ModuleAgent: "Let me ask the function agent..."

FunctionAgent(validate_token):
  *loads previous analysis*
  "I said it was safe in analysis #123, but let me re-check...
   AH! I missed UTC+12 timezone bug. Here's my correction..."
```

## Architecture

### Two-Level Hierarchy (MVP)

```
ModuleAgent (Coordinator)
    ↓ delegates
FunctionAgent (Worker)
    ↓ stores
AgentMemory (Persistent)
```

**ModuleAgent**:
- Responsible for a Python module (file)
- Spawns FunctionAgent for each function
- Coordinates analysis
- Checks module-level architecture (imports, boundaries)

**FunctionAgent**:
- Responsible for a single function
- Deep bug analysis using LLM
- Stores all reasoning in memory
- Can be questioned later

**AgentMemory**:
- Stores all analyses with timestamps
- Records all agent conversations
- Tracks decisions and corrections
- Enables cross-examination

### What We Already Have

- ✅ **CodeGraph**: Scans code, builds AST graph (349 files/sec, validated on 10.6M SLOC)
- ✅ **Rulepack DSL**: Architectural rules that compile to SQL
- ✅ **Orchestrator Core**: Task scheduling and coordination
- ✅ **Database**: Postgres with scan results

### What We're Building

- ❌ **Agent Framework**: Base agent classes with memory
- ❌ **FunctionAgent**: Analyzes functions, stores reasoning
- ❌ **ModuleAgent**: Coordinates function agents
- ❌ **Memory System**: Persistent storage for agent analyses
- ❌ **LLM Integration**: Anthropic/OpenAI for deep reasoning
- ❌ **CLI**: Run audits, query agent memory
- ❌ **Web UI**: Browse findings, interrogate agents

## Key Features

### 1. Persistent Memory
Every analysis is stored with full context:
```json
{
  "agent_id": "function:auth.login.validate_token",
  "timestamp": "2025-11-10T15:30:00Z",
  "commit_sha": "abc123",
  "findings": [...],
  "reasoning": "I checked null handling, timezone logic...",
  "confidence": 0.85
}
```

### 2. Cross-Examination
Agents can be questioned about their conclusions:
```python
response = agent.handle_question(
    "Why did you say timezone handling was correct?"
)
# Agent loads previous analysis and responds
```

### 3. Self-Correction
When proven wrong, agents record corrections:
```python
correction = agent.correct_analysis(
    original_analysis_id=123,
    new_evidence="UTC+12 timezone bug found",
    new_conclusion="I missed this edge case"
)
```

### 4. Cross-Agent Learning
Agents reference each other's conclusions:
```python
# FunctionAgent asks ModuleAgent
answer = module_agent.ask("What does save_user() return?")

# Uses that info in its own analysis
if "returns None" in answer:
    self.check_null_handling()
```

### 5. Architectural Memory
System-level decisions persist:
```python
system_agent.record_decision(
    decision="UI cannot import Data directly",
    reasoning="Multi-tenancy isolation requirement",
    adr_link="ADR-042"
)

# Later, when violation detected
drift = system_agent.explain_violation(
    "ui.dashboard imports data.users"
)
# Returns original reasoning + options to fix
```

## The 6-Week Plan

### Week 1: Agent Framework + Memory
- Base Agent class with memory interface
- AgentMemory data model
- Postgres schema for agent memories
- Basic LLM client (Anthropic/OpenAI)

**Deliverable**: Can create an agent, run analysis, store in memory

### Week 2: FunctionAgent Implementation
- FunctionAgent analyzes single function
- Static checks (complexity, patterns)
- LLM-based deep analysis
- Store all reasoning in memory

**Deliverable**: Can analyze a function and recall reasoning later

### Week 3: ModuleAgent + Parallel Execution
- ModuleAgent spawns function agents
- Parallel execution of multiple agents
- Cross-agent messaging
- Module-level architecture checks (rulepacks)

**Deliverable**: Can analyze entire module via coordinated agents

### Week 4: Memory Queries & Cross-Examination
- Query agent memory by ID
- Question agents about conclusions
- Agent correction mechanism
- Agent conversation history

**Deliverable**: Can interrogate agents and get historical context

### Week 5: CLI & Integration
- Command-line interface for audits
- Integration with existing CodeGraph
- Results storage and reporting
- Basic output formatting

**Deliverable**: Working CLI that produces useful output

### Week 6: Web UI
- Simple Flask app
- Browse audit runs
- View agent analyses
- Ask agents questions via UI

**Deliverable**: Web interface to explore agent findings and memory

## Success Metrics

After 6 weeks, we should be able to:

1. **Run an audit**: `eidolon audit --repo /path/to/code`
2. **Get findings**: See bugs found by function agents
3. **Question agents**: `eidolon ask function:X "Why did you say Y?"`
4. **See corrections**: When agents are proven wrong
5. **Browse in UI**: View all analyses and agent reasoning

## Beyond MVP

After proving the concept, we can add:

- **ClassAgent**: Coordinates functions within a class
- **SubsystemAgent**: Coordinates modules in a subsystem
- **SystemAgent**: Top-level orchestration
- **Agent-proposed fixes**: Agents suggest code changes
- **Test generation**: Agents create regression tests
- **Multi-repo analysis**: Cross-repository insights
- **Real-time drift detection**: Continuous monitoring

## Philosophy

We're not building "better linting" - we're building **persistent code intelligence**:

- Agents are experts on their domain
- Analyses are preserved with reasoning
- Agents can be held accountable
- Knowledge compounds over time
- Architecture is self-documenting

This creates a system where your codebase has a **memory** and can **explain itself**.

# Eidolon MVP - Getting Started

This is the simplified MVP implementation isolated from the main codebase complexity.

## Setup

### 1. Database Setup

```bash
# Create database
createdb eidolon_mvp

# Apply schema
psql eidolon_mvp < SCHEMA.sql

# For testing
createdb eidolon_mvp_test
psql eidolon_mvp_test < SCHEMA.sql
```

### 2. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
# DATABASE_URL=postgresql://localhost/eidolon_mvp
# ANTHROPIC_API_KEY=your_key_here
```

### 3. Install Dependencies

```bash
# From the mvp/ directory
cd mvp/
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=eidolon_mvp

# Run specific test
pytest tests/agents/test_models.py -v
```

## Project Structure

```
mvp/
├── src/eidolon_mvp/
│   ├── agents/           # Agent framework
│   │   ├── base.py       # Base Agent class
│   │   ├── models.py     # Data models (Finding, Analysis, etc.)
│   │   ├── function_agent.py  # [Week 2]
│   │   └── module_agent.py    # [Week 3]
│   ├── memory/           # Persistent memory
│   │   ├── store.py      # Postgres storage
│   │   └── agent_memory.py  # Per-agent interface
│   ├── llm/              # LLM integration
│   │   ├── client.py     # LLM client (Anthropic/OpenAI)
│   │   └── cache.py      # Response cache
│   └── cli/              # [Week 5] Command-line interface
├── tests/                # Tests
├── SCHEMA.sql            # Database schema
├── pyproject.toml        # Dependencies
└── MVP_README.md         # This file
```

## Week 1 Status ✅

- [x] Base agent framework
- [x] Agent data models (Finding, Analysis, Report, etc.)
- [x] Memory store (Postgres integration)
- [x] AgentMemory interface
- [x] LLM client (Anthropic/OpenAI)
- [x] Basic tests

## Next Steps (Week 2)

- [ ] Implement FunctionAgent
- [ ] Static analysis checks (complexity, null safety, etc.)
- [ ] LLM-based deep analysis
- [ ] Integration with CodeGraph

## Usage Example (Week 1)

```python
from datetime import datetime
from eidolon_mvp.agents.base import Agent, Scope
from eidolon_mvp.agents.models import Analysis, Finding
from eidolon_mvp.memory import MemoryStore

# Connect to database
store = MemoryStore("postgresql://localhost/eidolon_mvp")
await store.connect()

# Create a simple test agent
class MyAgent(Agent):
    async def analyze(self):
        findings = [
            Finding(
                location="test.py:42",
                severity="high",
                type="bug",
                description="Potential null pointer",
            )
        ]

        # Store analysis in memory
        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha="abc123",
            trigger="manual",
            findings=findings,
            reasoning="Found risky code pattern",
            confidence=0.85,
        )

        await self.memory.record_analysis(analysis)
        self.findings = findings
        return findings

# Use the agent
scope = Scope(type="function", id="test.validate")
agent = MyAgent("function:test.validate", scope, store)
findings = await agent.analyze()

print(f"Found {len(findings)} issues")
print(agent.report().summary)

# Later, query memory
analyses = await agent.memory.get_analyses()
print(f"Agent has {len(analyses)} stored analyses")

await store.close()
```

## Philosophy

This MVP is intentionally kept simple and isolated:

- **No dependencies on the complex codebase** in `src/eidolon/`
- **Clean slate** implementation of the core vision
- **Incremental** - build one week at a time
- **Test-driven** - tests guide development
- **Focused** - just the hierarchical agent system with memory

The "monument to complexity" stays in `src/eidolon/`, while we prove the concept here in `mvp/`.

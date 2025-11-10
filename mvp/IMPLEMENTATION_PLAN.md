# MVP Implementation Plan - 6 Weeks

## Overview

Build a 2-level hierarchical agent system (Module → Function) with persistent memory that can analyze code, find bugs, and be interrogated about its reasoning.

**Goal**: By Week 6, run `eidolon audit --repo /path/to/code` and get useful bug findings, with the ability to question agents about their conclusions.

---

## Week 1: Agent Framework + Memory Foundation

### Objectives
- Create base agent infrastructure
- Implement memory storage system
- Basic LLM integration
- Foundation for all future work

### Tasks

#### Day 1-2: Project Setup
- [ ] Create `src/eidolon/agents/` directory structure
- [ ] Create `src/eidolon/memory/` directory structure
- [ ] Create `src/eidolon/llm/` directory structure
- [ ] Set up development dependencies in `pyproject.toml`:
  - `anthropic` or `openai` for LLM
  - `psycopg[binary]>=3.2` (already have)
  - `asyncio` support
- [ ] Create database schema from `mvp/SCHEMA.sql`
- [ ] Set up test database

#### Day 3-4: Base Agent Classes
```python
# Files to create:
src/eidolon/agents/
├── __init__.py
├── base.py           # Agent, Scope classes
├── models.py         # Finding, Analysis, Report classes
└── exceptions.py     # AgentError, AnalysisError, etc.
```

**base.py**:
- [ ] `Agent` abstract base class
- [ ] `Scope` dataclass (type, id/path)
- [ ] `async analyze()` abstract method
- [ ] `report()` method
- [ ] `handle_question()` method (stub for now)

**models.py**:
- [ ] `Finding` dataclass (location, severity, type, description)
- [ ] `Analysis` dataclass (timestamp, commit_sha, findings, reasoning, confidence)
- [ ] `Report` dataclass (agent_id, scope, findings, summary)
- [ ] `Question` dataclass (from_agent, text, context)
- [ ] `Answer` dataclass (text, supporting_analyses)
- [ ] `Correction` dataclass (original_analysis_id, new_findings, reasoning)

#### Day 5-6: Memory System
```python
# Files to create:
src/eidolon/memory/
├── __init__.py
├── store.py          # MemoryStore class (Postgres)
├── agent_memory.py   # AgentMemory class (per-agent interface)
└── models.py         # Conversation, Decision classes
```

**store.py**:
- [ ] `MemoryStore` class with async Postgres connection pool
- [ ] `save_analysis(agent_id, analysis)` method
- [ ] `get_analyses(agent_id, filters)` method
- [ ] `save_conversation(agent_id, conversation)` method
- [ ] `mark_incorrect(analysis_id)` method
- [ ] `save_correction(agent_id, correction)` method

**agent_memory.py**:
- [ ] `AgentMemory` class wrapping MemoryStore
- [ ] `record_analysis()` method
- [ ] `get_analyses()` method with filters
- [ ] `record_conversation()` method
- [ ] `record_correction()` method

#### Day 7: LLM Integration
```python
# Files to create:
src/eidolon/llm/
├── __init__.py
├── client.py         # LLMClient class
├── cache.py          # Simple in-memory cache
└── prompts.py        # Prompt templates
```

**client.py**:
- [ ] `LLMClient` class
- [ ] Support for Anthropic (primary) and OpenAI (optional)
- [ ] `async complete(prompt, json_mode, cache_key)` method
- [ ] Caching by content hash
- [ ] Retry logic with exponential backoff
- [ ] Error handling

**prompts.py**:
- [ ] `FUNCTION_ANALYSIS_PROMPT` template
- [ ] `QUESTION_ANSWER_PROMPT` template
- [ ] Prompt formatting helpers

### Deliverables
- [ ] Base agent framework compiles
- [ ] Can create agent and store analysis in DB
- [ ] Can query agent memory
- [ ] LLM integration works (test with simple prompt)
- [ ] Unit tests for core classes

### Success Criteria
```python
# Should be able to do this:
store = MemoryStore(dsn="postgresql://localhost/eidolon")
memory = AgentMemory("test_agent", store)

analysis = Analysis(
    timestamp=datetime.now(),
    commit_sha="abc123",
    trigger="test",
    findings=[],
    reasoning="test reasoning",
    confidence=0.9
)

await memory.record_analysis(analysis)
analyses = await memory.get_analyses()
assert len(analyses) == 1
```

---

## Week 2: FunctionAgent Implementation

### Objectives
- Implement FunctionAgent that analyzes single functions
- Integrate with CodeGraph
- Perform static analysis + LLM analysis
- Store all reasoning in memory

### Tasks

#### Day 1-2: FunctionAgent Core
```python
# Files to create:
src/eidolon/agents/
├── function_agent.py     # FunctionAgent class
└── static_checks.py      # Static analysis helpers
```

**function_agent.py**:
- [ ] `FunctionAgent(Agent)` class
- [ ] Constructor takes function_id, codegraph, llm, memory_store
- [ ] `async analyze()` implementation:
  - [ ] Get function from CodeGraph
  - [ ] Run static checks
  - [ ] Run LLM analysis
  - [ ] Store in memory
  - [ ] Return findings

**static_checks.py**:
- [ ] `check_complexity(function_ast)` - McCabe complexity
- [ ] `check_unclosed_resources(function_ast)` - File handles
- [ ] `check_null_safety(function_ast)` - None checks
- [ ] `check_exception_handling(function_ast)` - Bare except

#### Day 3-4: LLM Analysis
- [ ] Build context-aware prompts for function analysis
- [ ] Include: function code, callers, callees, module context
- [ ] Parse LLM JSON responses into Finding objects
- [ ] Handle LLM errors gracefully
- [ ] Add confidence scoring

#### Day 5-6: Testing & Integration
- [ ] Unit tests for FunctionAgent
- [ ] Integration test with real function
- [ ] Test memory storage
- [ ] Test LLM caching
- [ ] Test error handling

#### Day 7: Polish
- [ ] Add logging
- [ ] Optimize prompts based on testing
- [ ] Handle edge cases (empty functions, generated code)
- [ ] Documentation

### Deliverables
- [ ] FunctionAgent can analyze a function
- [ ] Finds at least 3 types of bugs (complexity, null safety, resources)
- [ ] LLM analysis works and finds additional issues
- [ ] All analyses stored in memory
- [ ] Comprehensive tests

### Success Criteria
```python
# Should be able to do this:
agent = FunctionAgent(
    function_id="auth.login.validate_token",
    codegraph=codegraph,
    llm=llm_client,
    memory_store=store
)

findings = await agent.analyze()
print(f"Found {len(findings)} issues")

# Later, retrieve from memory
analyses = await agent.memory.get_analyses()
assert len(analyses) > 0
assert analyses[0].reasoning != ""
```

---

## Week 3: ModuleAgent + Parallel Execution

### Objectives
- Implement ModuleAgent that coordinates FunctionAgents
- Parallel execution of multiple function agents
- Module-level architecture checks
- Agent hierarchy tracking

### Tasks

#### Day 1-2: ModuleAgent Core
```python
# Files to create:
src/eidolon/agents/
└── module_agent.py       # ModuleAgent class
```

**module_agent.py**:
- [ ] `ModuleAgent(Agent)` class
- [ ] Constructor takes module_path, codegraph, llm, memory_store
- [ ] `async analyze()` implementation:
  - [ ] Get all functions in module
  - [ ] Spawn FunctionAgent for each
  - [ ] Run agents in parallel
  - [ ] Aggregate findings
  - [ ] Module-level checks
  - [ ] Store in memory

#### Day 3: Parallel Execution
```python
# Files to create:
src/eidolon/agents/
└── parallel.py           # ParallelExecutor class
```

- [ ] `ParallelExecutor` class using `asyncio.gather`
- [ ] Rate limiting to avoid overwhelming LLM API
- [ ] Progress tracking
- [ ] Error isolation (one agent failure doesn't stop others)

#### Day 4-5: Architecture Checks
- [ ] Integrate with existing Rulepack system
- [ ] Check import violations
- [ ] Check boundary violations
- [ ] Generate architecture findings
- [ ] Store module-level analysis

#### Day 6: Agent Hierarchy
- [ ] Record parent-child relationships in DB
- [ ] ModuleAgent tracks spawned FunctionAgents
- [ ] Hierarchical reporting (module → functions)
- [ ] Agent dependency tracking

#### Day 7: Testing
- [ ] Unit tests for ModuleAgent
- [ ] Integration test analyzing full module
- [ ] Test parallel execution
- [ ] Test architecture checks
- [ ] Performance testing

### Deliverables
- [ ] ModuleAgent coordinates function agents
- [ ] Parallel execution works (10+ functions)
- [ ] Module reports include all function findings
- [ ] Architecture violations detected
- [ ] Hierarchy tracked in database

### Success Criteria
```python
# Should be able to do this:
agent = ModuleAgent(
    module_path="src/auth/login.py",
    codegraph=codegraph,
    llm=llm_client,
    memory_store=store
)

findings = await agent.analyze()
report = agent.report()

print(f"Module: {report.scope.path}")
print(f"Functions analyzed: {len(agent.function_agents)}")
print(f"Total findings: {len(findings)}")
print(f"Children: {len(report.children)}")
```

---

## Week 4: Memory Queries & Cross-Examination

### Objectives
- Implement agent questioning system
- Enable cross-examination of previous analyses
- Agent correction mechanism
- Conversation tracking

### Tasks

#### Day 1-2: Question Handling
```python
# Update in:
src/eidolon/agents/base.py
```

- [ ] Implement `handle_question()` in Agent base class
- [ ] Load relevant analyses from memory
- [ ] Use LLM to answer based on history
- [ ] Store conversation in memory
- [ ] Return Answer with supporting evidence

#### Day 3: Cross-Agent Communication
```python
# Files to create:
src/eidolon/agents/
└── messaging.py          # AgentMessenger class
```

- [ ] `AgentMessenger` for agent-to-agent questions
- [ ] Message queue or direct async calls
- [ ] Track conversation threads
- [ ] Support question types: "why", "what", "how"

#### Day 4-5: Correction Mechanism
```python
# Add to:
src/eidolon/agents/base.py
```

- [ ] `async correct_analysis()` method
- [ ] Compare old vs new analysis
- [ ] Generate correction record
- [ ] Mark original analysis as incorrect
- [ ] Store learned lessons
- [ ] Update agent's "accuracy" metric

#### Day 6: Query API
```python
# Files to create:
src/eidolon/memory/
└── queries.py            # Memory query helpers
```

- [ ] `find_agent_by_scope()` - Get agent for code location
- [ ] `get_agent_history()` - Full analysis history
- [ ] `get_agent_conversations()` - Q&A history
- [ ] `get_agent_corrections()` - Mistakes and fixes
- [ ] `search_analyses()` - Find analyses by keyword

#### Day 7: Testing
- [ ] Test question handling
- [ ] Test cross-agent communication
- [ ] Test correction mechanism
- [ ] Integration test: agent corrects itself

### Deliverables
- [ ] Can ask agent questions via API
- [ ] Agent answers using memory
- [ ] Can challenge agent's conclusion
- [ ] Agent can correct itself
- [ ] All conversations stored

### Success Criteria
```python
# Should be able to do this:
function_agent = FunctionAgent(...)
await function_agent.analyze()

# Later, question it
question = Question(
    from_agent="human:developer",
    text="Why did you say null handling was correct?",
    context={}
)

answer = await function_agent.handle_question(question)
print(answer.text)
print(f"Based on analyses: {answer.supporting_analyses}")

# Challenge it
correction = Correction(
    original_analysis_id=123,
    trigger="Bug found in production",
    new_findings=[...],
    reasoning="I missed the UTC+12 timezone edge case"
)

await function_agent.correct_analysis(correction)
```

---

## Week 5: CLI & Integration

### Objectives
- Build command-line interface
- Integrate all components
- End-to-end audit workflow
- Results formatting and storage

### Tasks

#### Day 1-2: CLI Framework
```python
# Files to create:
src/eidolon/cli/
├── __init__.py
├── main.py           # Entry point
├── audit.py          # Audit command
├── query.py          # Query command
└── ask.py            # Ask command
```

**audit.py**:
- [ ] `audit` command with click
- [ ] `--repo` parameter
- [ ] `--module` parameter (optional)
- [ ] `--llm / --no-llm` flag
- [ ] `--parallel` parameter
- [ ] Progress display
- [ ] Results summary

**query.py**:
- [ ] `query` command for memory queries
- [ ] `--agent` parameter
- [ ] `--history` flag
- [ ] `--corrections` flag
- [ ] Format output nicely

**ask.py**:
- [ ] `ask` command to question agents
- [ ] `agent-id` argument
- [ ] `question` argument
- [ ] Display answer with context

#### Day 3-4: Orchestration
```python
# Files to create:
src/eidolon/orchestrator/
└── audit_runner.py   # AuditRunner class
```

- [ ] `AuditRunner` class
- [ ] Scan repo with CodeGraph
- [ ] Spawn ModuleAgents for each module
- [ ] Run agents with rate limiting
- [ ] Collect results
- [ ] Generate summary
- [ ] Store audit run in DB

#### Day 5: Output Formatting
```python
# Files to create:
src/eidolon/cli/
└── formatters.py     # Output formatters
```

- [ ] Text formatter (console output)
- [ ] JSON formatter (for tooling)
- [ ] Markdown formatter (for reports)
- [ ] Summary statistics
- [ ] Grouped by module/severity

#### Day 6-7: Integration Testing
- [ ] End-to-end test: audit small repo
- [ ] Verify all agents run
- [ ] Verify memory storage
- [ ] Verify output formatting
- [ ] Performance testing

### Deliverables
- [ ] Working `eidolon audit` command
- [ ] Working `eidolon query` command
- [ ] Working `eidolon ask` command
- [ ] All integrated with CodeGraph
- [ ] Results stored in database
- [ ] Nice console output

### Success Criteria
```bash
# Should be able to do this:
$ eidolon audit --repo /path/to/code

🔍 Scanning /path/to/code...
✓ Scanned 234 files

📦 Analyzing 45 modules...
✓ module:src/auth/login.py: 8 findings
✓ module:src/auth/session.py: 3 findings
✓ module:src/data/users.py: 12 findings
... (progress)

============================================================
✓ Analysis Complete!
  Modules: 45
  Functions: 234
  Findings: 156
    - Critical: 3
    - High: 23
    - Medium: 89
    - Low: 41
============================================================

$ eidolon query --agent "function:auth.login.validate_token" --history

Agent: function:auth.login.validate_token
Analyses: 2

[2025-11-10 15:30] Initial audit
  - 3 findings (1 high, 2 medium)
  - Confidence: 0.85
  - Status: ✓ Correct

[2025-11-12 09:15] Re-analysis after code change
  - 1 finding (1 high)
  - Confidence: 0.90
  - Status: ✓ Correct

$ eidolon ask "function:auth.login.validate_token" \
    "Why did you flag line 42?"

FunctionAgent(validate_token):
In my analysis on 2025-11-10, I found that line 42 accesses
user.id without checking if user is None first. This could
raise AttributeError in production.

See full analysis: eidolon query --agent ... --analysis 123
```

---

## Week 6: Web UI

### Objectives
- Simple web interface to browse findings
- View agent analyses and memory
- Ask agents questions via UI
- Polish and demo preparation

### Tasks

#### Day 1-2: Flask App Setup
```python
# Files to create:
src/eidolon/web/
├── __init__.py
├── app.py            # Flask application
├── routes.py         # Route handlers
├── templates/        # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── run_detail.html
│   ├── agent_detail.html
│   └── ask.html
└── static/           # CSS/JS
    └── style.css
```

- [ ] Flask app setup
- [ ] Route for index (list of runs)
- [ ] Route for run detail
- [ ] Route for agent detail
- [ ] Route for asking questions
- [ ] Basic CSS styling

#### Day 3: Run List & Detail
- [ ] Index page listing all audit runs
- [ ] Sortable/filterable table
- [ ] Run detail page with findings
- [ ] Group findings by module
- [ ] Filter by severity/type/status
- [ ] Click to see agent that found it

#### Day 4: Agent Detail View
- [ ] Agent info page
- [ ] Show agent scope
- [ ] List all analyses
- [ ] Show conversation history
- [ ] Show corrections (if any)
- [ ] "Ask this agent" button

#### Day 5: Interactive Q&A
- [ ] Form to ask agent questions
- [ ] Display answer with supporting analyses
- [ ] Show reasoning and confidence
- [ ] Link to related findings
- [ ] Conversation thread view

#### Day 6: Polish
- [ ] Improve styling
- [ ] Add charts (findings by severity, etc.)
- [ ] Responsive design
- [ ] Loading indicators
- [ ] Error handling

#### Day 7: Demo Preparation
- [ ] Run on sample codebase
- [ ] Generate demo data
- [ ] Screenshot workflow
- [ ] Write demo script
- [ ] Test presentation

### Deliverables
- [ ] Working web UI at localhost:8000
- [ ] Can browse all audit runs
- [ ] Can view agent analyses
- [ ] Can ask agents questions via UI
- [ ] Ready for demo

### Success Criteria
- Open http://localhost:8000
- See list of audit runs
- Click a run, see all findings
- Click an agent, see its history
- Ask agent a question, get answer
- UI is usable (doesn't need to be pretty)

---

## Post-MVP: Future Work

After 6 weeks, if successful, consider:

### Phase 2 (Weeks 7-12)
- [ ] **ClassAgent**: Coordinate functions within class
- [ ] **SubsystemAgent**: Coordinate modules in subsystem
- [ ] **SystemAgent**: Top-level orchestration
- [ ] **Agent-proposed fixes**: Agents generate code patches
- [ ] **Test generation**: Agents create test cases
- [ ] **CI/CD integration**: GitHub Action
- [ ] **Improved UI**: Vue.js rewrite

### Phase 3 (Months 4-6)
- [ ] **Multi-repo analysis**: Cross-repository insights
- [ ] **Real-time monitoring**: Continuous drift detection
- [ ] **Agent learning**: Fine-tune on corrections
- [ ] **Custom rules**: User-defined bug patterns
- [ ] **Integration**: Jira, Slack, etc.
- [ ] **Enterprise features**: RBAC, audit logs, SSO

---

## Risk Mitigation

### If LLM Findings Are Noisy
- Focus on static analysis
- Use LLM only for complex cases
- Add confidence thresholds
- Enable user feedback to improve prompts

### If Performance Is Poor
- Add more aggressive caching
- Reduce LLM calls (batch prompts)
- Use smaller model for simple cases
- Add option to analyze subset of functions

### If Memory System Is Complex
- Simplify schema (fewer tables)
- Skip conversation tracking initially
- Focus on analysis storage only
- Add features incrementally

### If Integration Is Hard
- Start with standalone tool (no CodeGraph)
- Manual file input instead of scanning
- Hardcode test data initially
- Integrate CodeGraph once working

---

## Success Metrics

By end of Week 6, we should have:

1. **Working system**: Can audit a codebase and get results
2. **Persistent memory**: Agents store and recall analyses
3. **Interrogation**: Can question agents about conclusions
4. **Corrections**: Agents can fix mistakes
5. **UI**: Can browse results in browser
6. **Demo-ready**: Can show to others

**Measures of success**:
- Find at least 10 real bugs in sample codebase
- False positive rate < 50%
- Can explain every finding's reasoning
- Can question and get useful answers
- Agents correct at least 1 mistake during testing

---

## Getting Started

### Prerequisites
- Python 3.13+
- Postgres database
- Anthropic or OpenAI API key
- UV package manager

### Setup
```bash
# Create database
createdb eidolon_mvp

# Apply schema
psql eidolon_mvp < mvp/SCHEMA.sql

# Install dependencies
uv sync

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Start coding!
# Begin with Week 1, Day 1 tasks
```

### Development Workflow
1. Create feature branch for each week
2. Write tests first (TDD where practical)
3. Commit frequently with descriptive messages
4. Test against real code regularly
5. Document as you go

---

**Let's build this!** 🚀

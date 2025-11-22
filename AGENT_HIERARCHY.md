# MONAD 5-Tier Agent Hierarchy

## Overview

MONAD uses a sophisticated 5-tier hierarchical agent system for comprehensive code analysis. Each tier provides a different level of coordination, analysis, and control, creating a multi-dimensional view of code quality.

## Hierarchy Structure

```
SYSTEM (mandatory)
  ├── SUBSYSTEM (optional - directory/package)
  │     ├── SUBSYSTEM (nested, optional)
  │     └── MODULE (mandatory - Python file)
  │           ├── CLASS (optional - defined classes)
  │           │     └── FUNCTION (mandatory - methods)
  │           └── FUNCTION (mandatory - standalone functions)
  └── MODULE (when no subsystems)
        ├── CLASS (optional)
        │     └── FUNCTION
        └── FUNCTION
```

## Tier Responsibilities

### 1. SYSTEM (Entire Codebase)
**Scope**: All code in the project
**Responsibilities**:
- Overall architecture quality assessment
- Critical cross-cutting concerns
- Strategic refactoring recommendations
- Code health score (0-100)
- System-level patterns and anti-patterns

**Analysis Focus**:
- Architecture patterns
- Major technical debt
- Security vulnerabilities at system level
- Performance bottlenecks
- Maintainability trends

**Example Target**: `/path/to/project`

---

### 2. SUBSYSTEM (Optional - Directory/Package)
**Scope**: Logical grouping of modules by directory structure
**Responsibilities**:
- Package cohesion and organization
- Inter-module dependencies and coupling
- Subsystem-level architectural patterns
- API design and boundaries
- Cross-cutting concerns within the subsystem

**Analysis Focus**:
- Package structure and naming
- Internal vs external APIs
- Dependency inversion
- Module coupling
- Subsystem-specific patterns

**Example Target**: `/path/to/project/backend/agents`

**When Created**: Automatically when the codebase has subdirectories. Can be nested for deep directory structures.

---

### 3. MODULE (Mandatory - Python File)
**Scope**: Single Python file
**Responsibilities**:
- Coordinates all classes and functions in the file
- Overall module code quality
- Architectural concerns within the module
- Integration issues between classes/functions
- Module-level variables and constants

**Analysis Focus**:
- Code smells (detected automatically)
- Module organization
- Import dependencies
- Global state management
- Module complexity

**Example Target**: `/path/to/project/backend/agents/orchestrator.py`

**Variables**: Module-level variables are part of the module's "plumbing" - analyzed as part of module assessment, not separate cards (unless they represent significant issues like security concerns or global state problems).

---

### 4. CLASS (Optional - Defined Classes)
**Scope**: Single class definition
**Responsibilities**:
- Coordinates analysis of all methods
- Class-level design patterns
- SOLID principles compliance
- Class cohesion and coupling
- Encapsulation and information hiding

**Analysis Focus**:
- **Single Responsibility Principle**: Does the class have one clear purpose?
- **Open/Closed Principle**: Can it be extended without modification?
- **Liskov Substitution**: Are inheritance relationships sound?
- **Interface Segregation**: Are interfaces lean and focused?
- **Dependency Inversion**: Does it depend on abstractions?
- Design patterns (Strategy, Factory, Observer, etc.)
- Class size and complexity
- Method cohesion

**Example Target**: `/path/to/project/backend/agents/orchestrator.py::AgentOrchestrator`

**When Created**: Automatically for every class definition in the codebase.

---

### 5. FUNCTION (Mandatory - Functions and Methods)
**Scope**: Individual function or method
**Responsibilities**:
- Detailed code-level analysis
- Potential bugs and errors
- Security vulnerabilities
- Code quality issues
- Automated fix generation

**Analysis Focus**:
- Logic errors and edge cases
- Input validation
- Error handling
- Security concerns (injection, XSS, etc.)
- Performance issues
- Code clarity and readability
- Cross-file context (callers/callees)

**Example Target**:
- Standalone function: `/path/to/project/backend/utils.py::validate_input`
- Class method: `/path/to/project/backend/agents/orchestrator.py::AgentOrchestrator._deploy_module_agent`

**Special Features**:
- Cross-file context analysis using call graph
- Shows callers and callees
- Includes code from related functions for context
- Proposes automated fixes with validation

---

## Analysis Flow

### Full Analysis (`analyze_codebase`)

1. **SYSTEM** agent created
2. **Directory analysis**: Modules grouped into subsystems by directory structure
3. **Parallel deployment**:
   - If subsystems exist → Deploy **SUBSYSTEM** agents
   - If no subsystems → Deploy **MODULE** agents directly
4. **SUBSYSTEM** agents (if present):
   - Deploy nested **SUBSYSTEM** agents for subdirectories
   - Deploy **MODULE** agents for files in this directory
5. **MODULE** agents:
   - Deploy **CLASS** agents for each class
   - Deploy **FUNCTION** agents for standalone functions
6. **CLASS** agents:
   - Deploy **FUNCTION** agents for all methods
7. **Analysis runs bottom-up**:
   - FUNCTION → CLASS → MODULE → SUBSYSTEM → SYSTEM
   - Each tier aggregates findings from children

### Incremental Analysis (`analyze_incremental`)

For changed files only:
1. **SYSTEM** agent created
2. Git detects changed Python files
3. **MODULE** agents deployed directly (no subsystems for simplicity)
4. **MODULE** → **CLASS** → **FUNCTION** hierarchy as normal
5. Only changed files analyzed, using cache for unchanged code

---

## Coordination and Control

Each tier coordinates its children:

### SYSTEM Coordinates:
- All SUBSYSTEM agents (if present)
- All MODULE agents (if no subsystems)
- Aggregates system-wide findings
- Identifies critical issues
- Provides strategic recommendations

### SUBSYSTEM Coordinates:
- Nested SUBSYSTEM agents
- MODULE agents in this directory
- Manages package-level concerns
- Tracks inter-module dependencies
- Ensures cohesive package design

### MODULE Coordinates:
- All CLASS agents in the file
- All standalone FUNCTION agents
- Manages module-level organization
- Tracks internal dependencies
- Detects code smells

### CLASS Coordinates:
- All FUNCTION agents (methods)
- Ensures SOLID principles
- Validates design patterns
- Checks class cohesion
- Identifies refactoring opportunities

### FUNCTION (Leaf):
- Performs detailed code analysis
- No children to coordinate
- Generates automated fixes
- Reports specific issues

---

## Concurrency and Performance

### Parallel Execution
- **Subsystems**: All deployed in parallel
- **Modules**: All deployed in parallel (configurable limit: default 3)
- **Classes**: All deployed in parallel within a module
- **Functions**: All deployed in parallel within a class (configurable limit: default 10)

### Rate Limiting
- Module-level semaphore: Max 3 concurrent modules
- Function-level semaphore: Max 10 concurrent functions
- AI API rate limiting: 50 requests/min, 40k tokens/min
- Circuit breaker for AI API failures

### Caching
- Function-level results cached by file + scope + name
- Cache invalidation on file changes (git integration)
- Significant performance improvement on re-analysis

---

## Agent Metadata

Each agent tracks:
- **Scope**: SYSTEM, SUBSYSTEM, MODULE, CLASS, or FUNCTION
- **Target**: What it's analyzing (path, class name, function name)
- **Status**: IDLE, ANALYZING, REPORTING, COMPLETED, ERROR
- **Parent ID**: Link to parent agent
- **Children IDs**: Links to child agents
- **Findings**: List of issues discovered
- **Cards Created**: Cards generated for this scope
- **Messages**: AI conversation history
- **Tokens/Cost**: Token usage and cost tracking
- **Timestamps**: Created, started, completed

---

## Cards Generated

### SYSTEM Cards
- **Type**: ARCHITECTURE
- **Priority**: P1
- **Content**: System-level assessment, critical issues, strategic recommendations

### SUBSYSTEM Cards
- **Type**: ARCHITECTURE
- **Content**: Package organization, API boundaries, coupling issues

### MODULE Cards
- **Type**: REVIEW
- **Content**: Module quality, code smells, refactoring opportunities

### CLASS Cards
- **Type**: REVIEW
- **Content**: SOLID principles, design patterns, cohesion issues

### FUNCTION Cards
- **Type**: REVIEW
- **Status**: PROPOSED (if fix available) or NEW
- **Content**: Specific bugs, security issues, automated fixes

---

## Example Analysis Output

```
SYSTEM: /path/to/project
  ├─ SUBSYSTEM: backend
  │    ├─ SUBSYSTEM: backend/agents
  │    │    ├─ MODULE: backend/agents/orchestrator.py
  │    │    │    ├─ CLASS: AgentOrchestrator
  │    │    │    │    ├─ FUNCTION: __init__
  │    │    │    │    ├─ FUNCTION: _deploy_module_agent
  │    │    │    │    └─ FUNCTION: _run_module_analysis
  │    │    │    └─ FUNCTION: standalone_helper
  │    │    └─ MODULE: backend/agents/__init__.py
  │    │         └─ (no classes, only module-level code)
  │    └─ SUBSYSTEM: backend/api
  │         └─ MODULE: backend/api/routes.py
  │              └─ FUNCTION: analyze_endpoint
  └─ SUBSYSTEM: frontend
       └─ (frontend has no Python files - empty)
```

---

## Benefits of 5-Tier Hierarchy

1. **Granular Analysis**: Each level provides appropriate level of detail
2. **Coordinated Reviews**: Parent agents aggregate and synthesize child findings
3. **Scalability**: Parallel execution at each tier enables analysis of large codebases
4. **Flexibility**: Optional tiers (SUBSYSTEM, CLASS) only created when needed
5. **Context**: Each tier has full context from children plus tier-specific concerns
6. **Actionable**: Function-level fixes, class-level patterns, module-level smells, subsystem-level architecture
7. **Progressive**: Can drill down from system → subsystem → module → class → function

---

## Configuration

### Environment Variables
- `MAX_CONCURRENT_MODULES`: Max parallel module agents (default: 3)
- `MAX_CONCURRENT_FUNCTIONS`: Max parallel function agents (default: 10)
- `ENABLE_CACHE`: Enable result caching (default: true)

### Programmatic Configuration
```python
orchestrator = AgentOrchestrator(
    db=database,
    llm_provider=llm_provider,  # Supports Anthropic, OpenAI, OpenRouter, etc.
    max_concurrent_modules=3,
    max_concurrent_functions=10,
    enable_cache=True
)

# Full analysis with 5-tier hierarchy
system_agent = await orchestrator.analyze_codebase("/path/to/project")

# Incremental analysis (changed files only)
result = await orchestrator.analyze_incremental("/path/to/project", base="HEAD~1")
```

---

## Future Enhancements

Potential additions to the hierarchy:
- **PACKAGE**: Explicit package tier (currently handled by SUBSYSTEM)
- **VARIABLE**: Module-level variable agents (currently in module "plumbing")
- **TEST**: Dedicated test analysis tier
- **DEPENDENCY**: Third-party dependency analysis tier
- **SECURITY**: Dedicated security scanning tier

---

## See Also

- `LLM_CONNECTION_ARCHITECTURE.md` - How agents connect to LLMs
- `MULTI_PROVIDER_GUIDE.md` - LLM provider configuration
- `RELIABILITY_IMPLEMENTATION_PLAN.md` - System reliability features
- `backend/agents/orchestrator.py` - Implementation

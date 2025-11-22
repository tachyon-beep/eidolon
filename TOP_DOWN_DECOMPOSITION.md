# Top-Down Task Decomposition System

## Overview

Complementary mode to the bottom-up analysis system. Instead of analyzing existing code, this mode takes high-level feature requests and autonomously decomposes them through the hierarchy for implementation.

## Architecture: Command & Decomposition Pattern

### Flow Direction

**Phase 1: Top-Down Decomposition (Planning)**
```
User Request
    ↓
SYSTEM Agent (Strategic Planning)
    ↓ (decomposes into subsystem tasks)
SUBSYSTEM Agents (Architectural Planning)
    ↓ (decomposes into module tasks)
MODULE Agents (Design Planning)
    ↓ (decomposes into class/function tasks)
CLASS Agents (Implementation Planning)
    ↓ (decomposes into method changes)
FUNCTION Agents (Code Generation)
```

**Phase 2: Bottom-Up Integration (Execution & Verification)**
```
FUNCTION Agents (write code, run tests)
    ↑ (report completion/issues)
CLASS Agents (integrate methods, verify cohesion)
    ↑ (report completion/issues)
MODULE Agents (integrate classes, verify module)
    ↑ (report completion/issues)
SUBSYSTEM Agents (integrate modules, verify subsystem)
    ↑ (report completion/issues)
SYSTEM Agent (final integration, system tests)
    ↑
Result to User
```

---

## Agent Responsibilities by Tier

### SYSTEM Agent (Commander)
**Receives**: High-level user request (e.g., "Add user authentication with JWT")

**Responsibilities**:
1. Understand the strategic intent
2. Identify affected subsystems
3. Decompose into subsystem-level tasks
4. Create task DAG (dependency graph)
5. Delegate to SUBSYSTEM agents
6. Coordinate integration
7. Run system-level tests
8. Report final result to user

**Output**: List of subsystem tasks with dependencies
```json
{
  "task": "Add user authentication with JWT",
  "subsystem_tasks": [
    {
      "subsystem": "api",
      "task": "Add authentication endpoints (/login, /verify)",
      "depends_on": ["services.auth_service"]
    },
    {
      "subsystem": "services",
      "task": "Implement JWT authentication service",
      "depends_on": []
    },
    {
      "subsystem": "models",
      "task": "Add User model with password hashing",
      "depends_on": []
    }
  ]
}
```

---

### SUBSYSTEM Agent (Lieutenant)
**Receives**: Subsystem-level task from SYSTEM agent

**Responsibilities**:
1. Understand architectural requirements
2. Identify affected modules
3. Decompose into module-level tasks
4. Manage module dependencies
5. Delegate to MODULE agents
6. Coordinate module integration
7. Run subsystem-level tests

**Output**: List of module tasks with dependencies
```json
{
  "subsystem": "services",
  "task": "Implement JWT authentication service",
  "module_tasks": [
    {
      "module": "services/auth_service.py",
      "task": "Create AuthService class with login/verify methods",
      "depends_on": ["services/token_service.py"]
    },
    {
      "module": "services/token_service.py",
      "task": "Create TokenService class for JWT generation/validation",
      "depends_on": []
    }
  ]
}
```

---

### MODULE Agent (Sergeant)
**Receives**: Module-level task from SUBSYSTEM agent

**Responsibilities**:
1. Understand design requirements
2. Identify which classes need changes (new/modify)
3. Decompose into class-level tasks
4. Manage class dependencies
5. Delegate to CLASS agents (or FUNCTION agents for new standalone functions)
6. Integrate class changes
7. Run module-level tests

**Output**: List of class/function tasks
```json
{
  "module": "services/auth_service.py",
  "task": "Create AuthService class",
  "class_tasks": [
    {
      "class": "AuthService",
      "action": "create_new",
      "methods": ["__init__", "login", "verify_token", "_hash_password"]
    }
  ],
  "function_tasks": []
}
```

---

### CLASS Agent (Squad Leader)
**Receives**: Class-level task from MODULE agent

**Responsibilities**:
1. Understand class design requirements
2. Identify which methods need changes (new/modify/delete)
3. Decompose into method-level tasks
4. Ensure SOLID principles
5. Delegate to FUNCTION agents (one per method)
6. Integrate methods into cohesive class
7. Verify class cohesion

**Output**: List of method tasks
```json
{
  "class": "AuthService",
  "task": "Create authentication service class",
  "method_tasks": [
    {
      "method": "__init__",
      "signature": "def __init__(self, token_service: TokenService, user_repo: UserRepository)",
      "task": "Initialize dependencies"
    },
    {
      "method": "login",
      "signature": "def login(self, username: str, password: str) -> dict",
      "task": "Authenticate user and return JWT token"
    },
    {
      "method": "verify_token",
      "signature": "def verify_token(self, token: str) -> dict",
      "task": "Verify JWT token and return user data"
    }
  ]
}
```

---

### FUNCTION Agent (Soldier)
**Receives**: Function/method-level task from CLASS or MODULE agent

**Responsibilities**:
1. Understand specific implementation requirements
2. Generate actual code
3. Write unit tests
4. Run tests
5. Fix issues if tests fail
6. Report completion

**Output**: Actual code
```python
def login(self, username: str, password: str) -> dict:
    """
    Authenticate user and return JWT token

    Args:
        username: User's username
        password: User's password (plaintext)

    Returns:
        dict with token and user info

    Raises:
        AuthenticationError: If credentials are invalid
    """
    # Get user from repository
    user = self.user_repo.get_by_username(username)
    if not user:
        raise AuthenticationError("Invalid credentials")

    # Verify password
    if not self._verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid credentials")

    # Generate JWT token
    token = self.token_service.generate_token({
        "user_id": user.id,
        "username": user.username
    })

    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username
        }
    }
```

---

## Implementation Phases

### Phase 1: Planning (Top-Down)
Each agent receives a task and decomposes it into subtasks for children.

**Key Features**:
- No code written yet - pure planning
- Create dependency graph
- Identify potential conflicts
- Estimate complexity
- Get user approval before execution

### Phase 2: Execution (Bottom-Up)
Each agent executes its part and reports up.

**Key Features**:
- FUNCTION agents write code first
- CLASS agents integrate methods
- MODULE agents integrate classes
- SUBSYSTEM agents integrate modules
- SYSTEM agent runs final integration tests

### Phase 3: Verification (Bottom-Up)
Each agent verifies its changes work correctly.

**Key Features**:
- Unit tests at FUNCTION level
- Integration tests at CLASS/MODULE level
- System tests at SYSTEM level
- Rollback on failure

---

## Task Types

### 1. Create New
- Add new function/class/module/subsystem
- No existing code to modify
- Straightforward delegation

### 2. Modify Existing
- Change existing function/class/module
- Need to understand current implementation
- May affect callers/callees

### 3. Refactor
- Improve existing code without changing behavior
- Preserve tests
- Ensure backward compatibility

### 4. Delete
- Remove unused code
- Check for remaining references
- Update callers

---

## Dependency Management

### Task DAG (Directed Acyclic Graph)
```
UserModel ───┐
             ├──→ AuthService ──→ LoginEndpoint
TokenService ┘
```

**Execution Order**:
1. UserModel (no dependencies)
2. TokenService (no dependencies)
3. AuthService (depends on both above)
4. LoginEndpoint (depends on AuthService)

### Parallel Execution
- Tasks with no dependencies run in parallel
- Tasks wait for dependencies to complete
- Agents coordinate through shared state

---

## Communication Protocol

### Task Assignment (Parent → Child)
```json
{
  "task_id": "T-001",
  "parent_task_id": "T-ROOT",
  "agent_scope": "SUBSYSTEM",
  "target": "services",
  "instruction": "Implement JWT authentication service",
  "context": {
    "user_request": "Add user authentication",
    "dependencies": ["models.User"],
    "constraints": ["Use PyJWT library", "Store tokens in Redis"]
  },
  "deadline": "2024-01-01T12:00:00Z"
}
```

### Task Completion (Child → Parent)
```json
{
  "task_id": "T-001",
  "status": "completed",
  "result": {
    "files_created": ["services/auth_service.py", "services/token_service.py"],
    "files_modified": [],
    "tests_passed": 15,
    "tests_failed": 0,
    "coverage": 95.2
  },
  "subtasks_completed": ["T-002", "T-003"],
  "issues": []
}
```

### Task Failure (Child → Parent)
```json
{
  "task_id": "T-001",
  "status": "failed",
  "error": "Cannot implement: Missing dependency 'redis' not in requirements.txt",
  "suggestion": "Add redis to requirements.txt or use alternative storage",
  "partial_completion": {
    "completed_subtasks": ["T-002"],
    "failed_subtasks": ["T-003"]
  }
}
```

---

## Conflict Resolution

### Scenario: Multiple agents want to modify same file

**Example**:
- SUBSYSTEM-A agent: "Add logging to utils.py"
- SUBSYSTEM-B agent: "Add validation to utils.py"

**Resolution Strategy**:
1. **Optimistic Locking**: First agent to complete wins, second agent must rebase
2. **Pessimistic Locking**: Agents request file locks from SYSTEM agent
3. **Merge Strategy**: Agents coordinate through SYSTEM agent to merge changes
4. **Split File**: SYSTEM agent recognizes conflict, suggests splitting utils.py

---

## Example: Full Flow

### User Request
```
"Add user authentication with JWT tokens to the API"
```

### SYSTEM Agent Planning
```json
{
  "understanding": "User wants secure authentication using JWT. Need to add login/logout endpoints, token generation/validation, user model with password hashing.",
  "affected_subsystems": ["api", "services", "models"],
  "tasks": [
    {
      "id": "T-001",
      "subsystem": "models",
      "task": "Create User model with password field",
      "priority": 1
    },
    {
      "id": "T-002",
      "subsystem": "services",
      "task": "Create authentication service with JWT",
      "priority": 2,
      "depends_on": ["T-001"]
    },
    {
      "id": "T-003",
      "subsystem": "api",
      "task": "Add /login and /logout endpoints",
      "priority": 3,
      "depends_on": ["T-002"]
    }
  ],
  "estimated_complexity": "medium",
  "estimated_time": "2-3 hours"
}
```

### Execution
1. **T-001** starts (models subsystem)
   - MODULE agent: "Add User class to models.py"
   - CLASS agent: "Create User class with username, email, password_hash fields"
   - FUNCTION agents: Create `__init__`, `set_password`, `check_password` methods
   - ✅ Complete: User model created with tests

2. **T-002** starts (services subsystem)
   - MODULE agent: "Create auth_service.py"
   - CLASS agent: "Create AuthService class"
   - FUNCTION agents: Create `generate_token`, `verify_token`, `login`, `logout` methods
   - ✅ Complete: Auth service created with tests

3. **T-003** starts (api subsystem)
   - MODULE agent: "Add endpoints to routes.py"
   - FUNCTION agents: Create `login_endpoint`, `logout_endpoint` functions
   - ✅ Complete: Endpoints created with tests

### Integration
- MODULE agents verify their modules work
- SUBSYSTEM agents verify subsystems integrate
- SYSTEM agent runs full integration test
- ✅ All tests pass

### Result to User
```
✅ Authentication system implemented successfully!

Changes made:
- Created User model (models/user.py)
  - Password hashing with bcrypt
  - Username and email fields

- Created AuthService (services/auth_service.py)
  - JWT token generation (exp: 24h)
  - Token validation
  - Login/logout logic

- Added API endpoints (api/routes.py)
  - POST /api/login (username, password)
  - POST /api/logout (requires token)

Tests: 28 passed, 0 failed
Coverage: 94%

Ready to deploy!
```

---

## Advantages

1. **Autonomous Decomposition**: System breaks down complex tasks automatically
2. **Parallel Execution**: Independent tasks run concurrently
3. **Clear Responsibility**: Each tier has specific role
4. **Testable**: Each level can be tested independently
5. **Scalable**: Can handle arbitrarily complex requests
6. **Traceable**: Clear audit trail of decisions
7. **Recoverable**: Failed subtasks can be retried without restarting

---

## Challenges

1. **Task Decomposition Quality**: Need smart planning at each level
2. **Context Propagation**: Each agent needs sufficient context
3. **Dependency Management**: Must track and respect dependencies
4. **Conflict Resolution**: Multiple agents may modify same code
5. **Testing Overhead**: Each level needs tests
6. **Cost**: Many LLM calls for planning + execution
7. **Correctness**: Ensuring generated code meets requirements

---

## Integration with Current System

### Mode 1: Analysis (Current - Bottom-Up)
```python
orchestrator.analyze_codebase("/path/to/project")
```

### Mode 2: Implementation (New - Top-Down)
```python
orchestrator.implement_feature(
    request="Add user authentication with JWT",
    project_path="/path/to/project",
    constraints={
        "test_coverage_min": 80,
        "max_complexity": 10,
        "follow_existing_patterns": True
    }
)
```

### Mode 3: Hybrid (Analysis → Implementation)
```python
# Analyze existing code
system_agent = await orchestrator.analyze_codebase("/path/to/project")

# Get improvement suggestions
suggestions = system_agent.get_improvement_suggestions()

# Implement top suggestion
await orchestrator.implement_improvement(
    suggestion=suggestions[0],
    project_path="/path/to/project"
)
```

---

## Next Steps

1. **Design Task Protocol**: Define task assignment/completion messages
2. **Implement Planning Phase**: Top-down decomposition without execution
3. **Add Task DAG**: Dependency graph management
4. **Implement Execution Phase**: Bottom-up code generation
5. **Add Conflict Resolution**: Handle concurrent modifications
6. **Create Verification Phase**: Test generation and execution
7. **Build Rollback System**: Undo changes on failure

---

## See Also

- `AGENT_HIERARCHY.md` - Current bottom-up analysis system
- `LLM_CONNECTION_ARCHITECTURE.md` - How agents use LLMs
- `MULTI_PROVIDER_GUIDE.md` - LLM provider configuration

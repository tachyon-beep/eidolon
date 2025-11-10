# Specialized Agent Swarms

## The Concept

Instead of one-size-fits-all agents, spawn **specialists** with domain-specific skill packs:

```
Python Orchestrator
    │
    ├─► PyTorch Expert (with pytorch-engineering skills)
    ├─► Test Engineer (with test-driven-development skills)
    ├─► Security Auditor (with security-review skills)
    ├─► DRL Specialist (with deep-rl skills)
    └─► Performance Optimizer (with profiling skills)
```

Each agent is a **full Claude Code instance** with specialized skills loaded.

## Use Cases

### 1. PyTorch/DL Model Debugging

```python
# Orchestrator detects PyTorch code
if "import torch" in code:
    # Spawn PyTorch expert with specialized skills
    pytorch_agent = await orchestrator.spawn_agent(
        AgentConfig(
            role="pytorch-expert",
            system_prompt="You are a PyTorch debugging expert.",
            workspace=workspace / "pytorch-expert",
            skills=["pytorch-engineering:tensor-operations-and-memory",
                    "pytorch-engineering:debugging-techniques",
                    "pytorch-engineering:performance-profiling"],
        )
    )

    # Agent has full PyTorch debugging powers
    result = await pytorch_agent.analyze(code)
    # → Can detect: memory leaks, device placement issues,
    #              gradient problems, tensor shape mismatches
```

**Why this is powerful:**
- Agent knows PyTorch-specific debugging patterns
- Can run profiling tools (torch.profiler)
- Understands tensor operations deeply
- Can test on GPU/CPU automatically

### 2. Test Engineering

```python
# Need comprehensive test suite
test_engineer = await orchestrator.spawn_agent(
    AgentConfig(
        role="test-engineer",
        system_prompt="You are a test engineering expert using TDD.",
        workspace=workspace / "test-engineer",
        skills=["superpowers:test-driven-development",
                "superpowers:condition-based-waiting",
                "superpowers:testing-anti-patterns"],
    )
)

# Agent generates production-quality tests
tests = await test_engineer.generate_test_suite(
    code=module_code,
    coverage_target=90,
)
# → Edge cases, property tests, integration tests
# → Proper mocking, fixtures
# → Avoids anti-patterns
```

**Why this is powerful:**
- Follows TDD best practices
- Knows testing anti-patterns to avoid
- Can handle async/race conditions properly
- Writes maintainable, clear tests

### 3. Security Auditing

```python
# Security-focused code review
security_auditor = await orchestrator.spawn_agent(
    AgentConfig(
        role="security-auditor",
        system_prompt="You are a security auditing expert.",
        workspace=workspace / "security",
        skills=["security:owasp-top-10",
                "security:crypto-review",
                "security:injection-detection"],
    )
)

# Deep security analysis
vulnerabilities = await security_auditor.audit(code)
# → SQL injection, XSS, CSRF
# → Crypto misuse
# → Authentication flaws
# → Suggests fixes with examples
```

### 4. DRL/Reinforcement Learning

```python
# Debugging DRL training issues
drl_agent = await orchestrator.spawn_agent(
    AgentConfig(
        role="drl-specialist",
        system_prompt="You are a deep RL debugging expert.",
        workspace=workspace / "drl-debug",
        skills=["drl:reward-shaping",
                "drl:exploration-exploitation",
                "drl:stability-debugging"],
    )
)

# Diagnose training failures
diagnosis = await drl_agent.debug_training(
    training_code=code,
    tensorboard_logs=logs,
)
# → Reward sparsity issues
# → Exploration problems
# → Network instability
# → Suggests architecture changes
```

## Architecture

### Agent Pool Management

```python
class SpecializedAgentPool:
    """Manages a pool of specialized agents."""

    def __init__(self):
        self.agent_templates = {
            "pytorch-expert": AgentTemplate(
                skills=["pytorch-engineering:*"],
                system_prompt=PYTORCH_EXPERT_PROMPT,
            ),
            "test-engineer": AgentTemplate(
                skills=["superpowers:test-driven-development",
                        "superpowers:testing-anti-patterns"],
                system_prompt=TEST_ENGINEER_PROMPT,
            ),
            "security-auditor": AgentTemplate(
                skills=["security:*"],
                system_prompt=SECURITY_AUDITOR_PROMPT,
            ),
            "drl-specialist": AgentTemplate(
                skills=["drl:*"],
                system_prompt=DRL_SPECIALIST_PROMPT,
            ),
        }

    async def get_specialist(
        self,
        code: str,
        context: str,
    ) -> str:
        """Auto-detect which specialist is needed."""

        # Analyze code to determine specialist
        if "import torch" in code or "import tensorflow" in code:
            return "pytorch-expert"
        elif "test_" in code or "pytest" in code:
            return "test-engineer"
        elif "sql" in code.lower() or "password" in code:
            return "security-auditor"
        elif "gym" in code or "stable_baselines" in code:
            return "drl-specialist"

        # Default to general agent
        return "general"

    async def spawn_specialist(
        self,
        specialist_type: str,
        workspace: Path,
    ) -> Agent:
        """Spawn a specialist agent."""

        template = self.agent_templates[specialist_type]

        return Agent(
            name=f"{specialist_type}-{uuid4()}",
            system_prompt=template.system_prompt,
            working_directory=str(workspace),
            skills=template.skills,  # Load skill packs
        )
```

### Workflow: Automatic Specialist Selection

```python
async def analyze_with_specialists(code: str):
    """Automatically route to appropriate specialists."""

    pool = SpecializedAgentPool()

    # Detect what kind of code this is
    specialist_type = await pool.get_specialist(code)

    # Spawn appropriate specialist
    agent = await pool.spawn_specialist(
        specialist_type=specialist_type,
        workspace=Path(f"/tmp/eidolon/{specialist_type}"),
    )

    # Agent has domain-specific knowledge
    result = await agent.analyze(code)

    return result
```

## Multi-Specialist Collaboration

For complex issues, multiple specialists work together:

```python
async def deep_analysis(code: str):
    """Multi-specialist collaborative analysis."""

    # Spawn multiple specialists
    pytorch_expert = await spawn_specialist("pytorch-expert")
    test_engineer = await spawn_specialist("test-engineer")
    security_auditor = await spawn_specialist("security-auditor")

    # Each analyzes in parallel
    pytorch_issues, test_coverage, security_vulns = await asyncio.gather(
        pytorch_expert.analyze(code),
        test_engineer.assess_coverage(code),
        security_auditor.audit(code),
    )

    # Orchestrator synthesizes results
    return {
        "pytorch": pytorch_issues,
        "testing": test_coverage,
        "security": security_vulns,
        "priority": prioritize_issues([pytorch_issues, test_coverage, security_vulns]),
    }
```

## Example: PyTorch Model Debugging

```
User: "Debug this PyTorch model - training is unstable"

Orchestrator:
  1. Detect: PyTorch code (import torch)
  2. Spawn PyTorch expert with skills:
     - tensor-operations-and-memory
     - debugging-techniques
     - performance-profiling
     - mixed-precision-and-optimization

PyTorch Expert Agent:
  1. Read model code
  2. Run torch.profiler to check memory usage
  3. Detect: "Large tensor allocated on CPU, moved to GPU repeatedly"
  4. Add instrumentation: print(tensor.device) at key points
  5. Run training for 10 steps
  6. Analyze output: "Confirmed - data on CPU, model on GPU"
  7. Suggest fix:
     ```python
     # Move data to GPU before training
     data = data.to(device)
     ```
  8. Verify fix by running again
  9. Memory usage reduced by 80%
  10. Training stable

Result: Fixed with actual profiling and iteration, not guesswork.
```

## Skill Pack Catalog

### Core Skills
- `superpowers:test-driven-development`
- `superpowers:systematic-debugging`
- `superpowers:code-reviewer`

### Domain-Specific
- `pytorch-engineering:*` - Deep learning debugging
- `axiom-python-engineering:*` - Python best practices
- `security:*` - Security auditing
- `performance:*` - Performance optimization
- `drl:*` - Reinforcement learning

### Language-Specific
- `rust:memory-safety` - Rust borrow checker help
- `typescript:type-safety` - TypeScript debugging
- `go:concurrency` - Go goroutine debugging

## Configuration

```python
# config/specialists.yaml
specialists:
  pytorch-expert:
    skills:
      - pytorch-engineering:tensor-operations-and-memory
      - pytorch-engineering:debugging-techniques
      - pytorch-engineering:performance-profiling
    system_prompt: |
      You are a PyTorch expert specializing in debugging
      deep learning models. Use profiling tools, check tensor
      devices, identify memory issues, and verify fixes with
      actual execution.

  test-engineer:
    skills:
      - superpowers:test-driven-development
      - superpowers:testing-anti-patterns
      - superpowers:condition-based-waiting
    system_prompt: |
      You are a test engineering expert. Write comprehensive
      test suites using TDD principles. Avoid anti-patterns.
      Handle async and race conditions properly.

  security-auditor:
    skills:
      - security:owasp-top-10
      - security:injection-detection
      - security:crypto-review
    system_prompt: |
      You are a security auditing expert. Review code for
      OWASP Top 10 vulnerabilities. Identify injection flaws,
      crypto misuse, and authentication issues.
```

## Benefits

### 1. **Deep Expertise**
Each specialist knows their domain deeply - not shallow knowledge across everything.

### 2. **Better Results**
PyTorch expert catches issues that general agent misses.

### 3. **Efficient**
Don't load all skills for every task - only what's needed.

### 4. **Scalable**
Add new specialists by adding skill packs - no code changes.

### 5. **Collaborative**
Multiple specialists work together on complex problems.

## Implementation

### Phase 1: Basic Specialization
```python
# Simple specialist selection
specialist = detect_specialist_needed(code)
agent = spawn_agent_with_skills(specialist, skills[specialist])
result = await agent.analyze(code)
```

### Phase 2: Skill Pack Loading
```python
# Load skill packs dynamically
agent = Agent(
    name="pytorch-expert",
    skills=load_skill_pack("pytorch-engineering"),
    workspace=workspace,
)
```

### Phase 3: Multi-Specialist Collaboration
```python
# Orchestrate multiple specialists
results = await orchestrate_specialists(
    code=code,
    specialists=["pytorch-expert", "test-engineer"],
    collaboration_mode="parallel",
)
```

## The Vision

Imagine a world where:
- **PyTorch issues are debugged by PyTorch experts**
- **Tests are written by test engineers**
- **Security is audited by security specialists**
- **DRL problems are solved by DRL experts**

All working **in parallel**, **in isolated workspaces**, with **full observability**.

And all of this is **orchestrated automatically** based on the code being analyzed.

This is what specialized agent swarms enable!

## Next Steps

1. **Catalog skill packs**: Document all available skills
2. **Define specialist templates**: Create configurations for each type
3. **Build auto-detection**: Automatically route to right specialist
4. **Enable collaboration**: Let specialists work together
5. **Add more domains**: Expand to new areas (Rust, frontend, databases, etc.)

---

**The key insight**: One generalist LLM trying to do everything = mediocre results

**Multiple specialist Claude Code instances with domain skills = expert results**

This is the power of specialized agent swarms! 🚀

# Eidolon MVP - Agent-Based Code Analysis & Refactoring

## Project Overview

Eidolon is a hierarchical agent system that analyzes Python codebases, identifies issues, and refactors complex code using Test-Driven Development.

## Architecture

### Hierarchical Agents
- **ModuleAgent**: Analyzes entire Python files/modules
- **FunctionAgent**: Analyzes individual functions
- Uses "One Agent Type + Many Prompts" philosophy instead of many agent classes

### Key Philosophy

**Prompt Engineering > Code Complexity**: We use specialized prompts with a single agent type rather than creating many agent classes.

## Features

### Analysis
- Static analysis (AST-based): complexity, null safety, resource leaks
- LLM-enhanced analysis: logic errors, security issues
- CodeGraph integration: caller/callee relationships

### Refactoring
- TDD-based refactoring workflow:
  1. Capture behavior with tests
  2. Plan sub-functions
  3. Generate implementations
  4. **Verify with actual test execution**
  5. Iterate until tests pass

### LLM Integration
- Structured outputs using Pydantic models
- Supports OpenAI, OpenRouter, Anthropic
- Content-addressed caching (SHA256)

## Directory Structure

```
mvp/
├── src/eidolon_mvp/
│   ├── agents/
│   │   ├── tasks.py          # Task orchestration with Pydantic models
│   │   ├── prompts.py        # Specialized prompts for different tasks
│   │   └── models.py         # Data models
│   ├── llm/
│   │   ├── client.py         # Unified LLM client with structured outputs
│   │   └── config.py         # Environment-based configuration
│   └── codegraph/
│       └── adapter.py        # CodeGraph database integration
├── .claude/
│   ├── skills/
│   │   └── code-refactoring.md
│   └── agents/
│       └── complexity-analyzer.md
├── demo_refactoring.py       # TDD refactoring demonstration
└── analyze_file_simple.py    # Simple file analysis (no DB)
```

## Current State

✅ **Completed**:
- Hierarchical agent framework
- Structured outputs with Pydantic
- TDD refactoring workflow
- OpenRouter/OpenAI/Anthropic support
- Static + LLM analysis

🚧 **In Progress**:
- Converting to use Claude Agent SDK
- Actual test execution for verification
- Parallel subagent analysis
- Self-healing iteration loop

## Usage

### Analyze a file
```bash
python analyze_file_simple.py path/to/file.py --llm
```

### Refactor complex functions
```bash
python demo_refactoring.py
```

### Use the refactoring skill (with Claude Code)
```
Use the code-refactoring skill to refactor the complex functions in hamlet/src/networks.py
```

## Key Principles

1. **Test-Driven**: Always generate and execute tests
2. **Verify with Execution**: Never rely on LLM judgment alone
3. **Parallel Where Possible**: Use subagents for independent tasks
4. **Iterate Until Correct**: Run tests, fix errors, repeat
5. **Preserve Behavior**: Refactored code must produce identical outputs

## Environment Setup

Required environment variables:
```bash
export LLM_PROVIDER=openai-compatible
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export LLM_MODEL=anthropic/claude-3.5-sonnet
```

## Next Steps

1. **Convert to Claude Agent SDK**: Use subagents instead of remote LLM calls
2. **Add Test Execution**: Actually run pytest to verify behavior
3. **Build Self-Healing Loop**: Iterate until all tests pass
4. **Integrate CodeGraph**: Add caller/callee context to analysis

## Files to Know

- `TDD_REFACTORING.md` - Documents the prompt-based refactoring approach
- `src/eidolon_mvp/agents/tasks.py` - Core task functions with Pydantic models
- `src/eidolon_mvp/llm/client.py` - LLM client with structured output support

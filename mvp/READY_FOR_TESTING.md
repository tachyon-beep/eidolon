#!/usr/bin/env bash
# Ready for Testing!

## What's Built

**Week 1-3 Complete!** The MVP hierarchical agent system is ready:

- ✅ **FunctionAgent** - Analyzes individual functions (static + optional LLM)
- ✅ **ModuleAgent** - Coordinates multiple FunctionAgents in parallel
- ✅ **Memory System** - Persistent storage of all analyses in Postgres
- ✅ **OpenRouter Support** - Use your OpenRouter key for LLM analysis
- ✅ **CodeGraph Integration** - Ready to provide call graph context (callers/callees)

## Quick Start

### 1. Database Setup

```bash
cd mvp/

# Create database
createdb eidolon_mvp

# Apply schema
psql eidolon_mvp < SCHEMA.sql
```

### 2. Configure OpenRouter (Optional)

```bash
# Copy template
cp .env.example .env

# Edit .env:
export LLM_PROVIDER=openai-compatible
export OPENAI_API_KEY=sk-or-v1-your-key-here
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export LLM_MODEL=anthropic/claude-3.5-sonnet

# Or just export directly:
export LLM_PROVIDER=openai-compatible
export OPENAI_API_KEY=sk-or-v1-...
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export LLM_MODEL=anthropic/claude-3.5-sonnet
```

### 3. Analyze a File

```bash
# Static analysis only (free, fast)
python analyze_file.py /path/to/file.py

# With LLM enhancement (requires API key)
python analyze_file.py /path/to/file.py --llm
```

## What It Finds

**Static Analysis** (always runs):
- High complexity functions
- Unclosed file handles
- Potential None access
- Bare except blocks
- Unused variables
- Module-level issues (wildcard imports, etc.)

**LLM Analysis** (with --llm):
- Logic errors
- Security vulnerabilities
- Edge case bugs
- Data validation issues

## Example Output

```bash
$ python analyze_file.py ../src/eidolon/rulepack/parser.py

Analyzing: ../src/eidolon/rulepack/parser.py

  Lines of code: 234
  Using: Static analysis only

🔍 Running analysis...

Module ../src/eidolon/rulepack/parser.py: found 8 functions
Analyzing 8 functions in parallel...
  Progress: 8/8 (100%)
✓ Complete

=======================================================================
RESULTS
=======================================================================

Found 5 issue(s):
  🟠 HIGH: 2
  🟡 MEDIUM: 2
  🟢 LOW: 1

HIGH Issues:
----------------------------------------------------------------------

1. Accessing attribute on 'data' which might be None
   Location: ../src/eidolon/rulepack/parser.py:42
   Type: bug
   Fix: Add None check: if data is not None:

2. File opened without context manager. May not be closed properly on error.
   Location: ../src/eidolon/rulepack/parser.py:87
   Type: bug
   Fix: Use 'with open(...) as f:' instead

...

Functions analyzed: 8
  ✓ parse_rulepack
  ⚠ validate_schema (2)
  ✓ compile_rule
  ⚠ check_syntax (1)
  ...

Confidence: 89%
Analysis ID: 123
```

## CodeGraph Integration (Coming Next)

The system is ready to integrate with your existing CodeGraph database:

```python
from eidolon_mvp.codegraph import CodeGraphAdapter

# Connect to CodeGraph
codegraph = CodeGraphAdapter(dsn="postgresql://...")
await codegraph.connect()

# Get call context for a function
context = await codegraph.get_function_context("validate_token", "src/auth.py")

# Use in agent prompts
print(f"Callers: {context.callers}")
print(f"Callees: {context.callees}")
```

This will give agents context like:
- "validate_token is called by: login, refresh_session, check_auth"
- "validate_token calls: decode_jwt, get_secret_key"

## What File Should We Test?

Point me to a Python file from your codebase and I'll run the analysis!

Options:
1. **Small file** (~100-200 lines) - Quick test
2. **Medium file** (~500 lines) - See parallel execution
3. **Complex file** - Stress test the system

Just say: "Analyze /path/to/file.py" and I'll run it!

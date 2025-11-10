# TDD Refactoring System

## Philosophy

**One Agent Type + Many Prompts** instead of many agent classes.

We use `FunctionAgent` conceptually with specialized prompts for different tasks:
- Analysis
- Refactoring planning
- Code generation
- Test generation
- Code review

This keeps the codebase simple while enabling complex workflows.

## How It Works

### 1. Find Complex Functions

```python
# ModuleAgent finds issues
findings = await module_agent.analyze()

# Filter for complexity
complex_functions = [f for f in findings if f.type == "performance" and "complexity" in f.description]
```

### 2. Plan Refactoring (TDD Step 1)

```python
plan = await plan_refactoring(
    llm=llm,
    function_code=original_code,
    function_name="process_order",
    issue_description="High complexity (18)"
)

# Plan includes:
# - behavior_tests: Capture current behavior
# - sub_functions: Proposed smaller functions
# - main_logic: How main function calls them
```

### 3. Generate Sub-functions (TDD Step 2)

```python
for sub_fn in plan.sub_functions:
    code = await generate_function(
        llm=llm,
        function_name=sub_fn['name'],
        purpose=sub_fn['purpose'],
        signature=sub_fn['signature']
    )
```

### 4. Review Changes (TDD Step 3)

```python
review = await review_refactoring(
    llm=llm,
    original_code=original,
    refactored_code=refactored
)

# Verifies:
# - behavior_preserved: Same inputs → same outputs
# - complexity_reduced: Simpler code
# - approval: "approved" | "needs_changes"
```

## Example Workflow

```python
from eidolon_mvp.agents.tasks import refactor_function_tdd

result = await refactor_function_tdd(
    llm=llm,
    function_code=complex_function,
    function_name="process_order",
    issue_description="High complexity (20+ decision points)"
)

if result["success"]:
    print("Behavior tests:", result["plan"].behavior_tests)
    print("Sub-functions:", result["plan"].sub_functions)
    print("Refactored code:", result["refactored_code"])
    print("Review:", result["review"])
```

## Key Files

### `src/eidolon_mvp/llm/client.py`

LLM client with structured outputs support:
- `complete()` - Basic text/JSON completion
- `complete_structured()` - **Pydantic model-based structured outputs**
- Supports OpenAI structured outputs API
- Falls back to JSON mode for Anthropic

### `src/eidolon_mvp/agents/prompts.py`

Contains all specialized prompts:
- `ANALYZE_FUNCTION` - Bug detection
- `PLAN_REFACTORING` - TDD refactoring plan
- `GENERATE_FUNCTION` - Code generation
- `GENERATE_TESTS` - Test generation
- `REVIEW_CODE` - Behavior verification

### `src/eidolon_mvp/agents/tasks.py`

Pydantic models for structured outputs:
- `BehaviorTest` - Test case model
- `SubFunction` - Sub-function specification
- `RefactoringTask` - Complete refactoring plan

High-level task functions:
- `analyze_function()` - Find bugs
- `plan_refactoring()` - Create refactoring plan (uses structured outputs)
- `generate_function()` - Generate code
- `generate_tests()` - Generate tests
- `review_refactoring()` - Verify preservation
- `refactor_function_tdd()` - Complete workflow

## Benefits

### 1. Simple Codebase
- One agent type, many prompts
- No proliferation of agent classes
- Easy to add new tasks (just add prompt)

### 2. TDD Approach
- Captures behavior first (tests)
- Plans refactoring
- Generates code
- Verifies behavior preserved

### 3. Modular
- Each task is independent
- Can mix and match
- Easy to test individual steps

### 4. LLM-Powered
- Uses LLM for all reasoning
- Prompt engineering > code complexity
- Easy to improve (just edit prompts)

### 5. Structured Outputs
- Uses Pydantic models for type-safe responses
- Leverages OpenAI structured outputs API
- Eliminates JSON parsing errors
- Provides IDE autocomplete and type checking

## Usage

### Find Issues
```bash
python analyze_file_simple.py ~/code/myfile.py --llm
```

### Refactor
```bash
python demo_refactoring.py
```

### In Code
```python
# 1. Analyze
findings = await analyze_function(llm, code, "func_name", "file.py")

# 2. If complex, plan refactoring
if "complexity" in findings[0].description:
    plan = await plan_refactoring(llm, code, "func_name", findings[0].description)

# 3. Generate new functions
for sub_fn in plan.sub_functions:
    new_code = await generate_function(llm, sub_fn['name'], sub_fn['purpose'], sub_fn['signature'])

# 4. Review
review = await review_refactoring(llm, original, refactored)
```

## Next Steps

1. **Add CodeGraph context** - Include callers/callees in prompts
2. **Test execution** - Actually run tests to verify behavior
3. **Iterative refinement** - If review fails, iterate
4. **Batch refactoring** - Refactor multiple functions
5. **Integration** - Hook into module agent for automatic refactoring

## Architecture Decision

**Why prompts over classes?**

- ❌ `RefactoringAgent`, `TestGeneratorAgent`, `CodeReviewAgent`, ... (10+ classes)
- ✅ `FunctionAgent` + `REFACTORING_PROMPT`, `TEST_GEN_PROMPT`, `REVIEW_PROMPT` (1 agent, N prompts)

The prompt approach is:
- Simpler to maintain
- Easier to improve (edit prompt vs change code)
- More flexible (mix and match prompts)
- Clearer separation of concerns

This is the essence of LLM engineering: **prompt design > code complexity**.

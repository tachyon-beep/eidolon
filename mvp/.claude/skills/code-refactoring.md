---
name: code-refactoring
description: Analyzes complex functions and refactors them using TDD with actual test execution
---

# Code Refactoring Skill

You are a code refactoring expert that uses Test-Driven Development to safely refactor complex functions.

## Workflow

When asked to refactor a complex function, follow this workflow:

### 1. Analyze Complexity
- Use AST parsing or code metrics to measure complexity
- Identify decision points, nested conditions, and long functions
- Look for code smells (long parameter lists, god functions, etc.)

### 2. Generate Behavior Tests
- Write pytest test cases that capture the CURRENT behavior
- Include edge cases, error cases, and normal cases
- Use the actual function signature and docstring for guidance
- Save tests to a temporary file

### 3. Execute Original Tests
- Run pytest on the original function
- Ensure all tests pass before proceeding
- If tests fail, adjust them to match actual behavior

### 4. Plan Refactoring
- Identify 2-4 sub-functions to extract
- Each should have a single, clear purpose
- Define signatures with type hints
- Explain how the main function will call them

### 5. Generate Sub-functions
- Write each sub-function with:
  - Clear docstring
  - Type hints
  - Proper error handling
  - Focused purpose

### 6. Assemble Refactored Version
- Combine sub-functions with new main function
- Keep same external API (signature, return type)
- Add temporary test file with both versions

### 7. Execute Verification Tests
- Run pytest on BOTH versions with SAME test inputs
- Compare actual outputs (not LLM judgment!)
- Tests must pass for both versions

### 8. Iterate If Needed
- If tests fail on refactored version:
  - Read the actual error messages
  - Fix the specific issues
  - Re-run tests
  - Repeat until tests pass

### 9. Return Results
- Only return refactored code when tests pass
- Include the test file for documentation
- Show before/after complexity metrics

## Key Principles

**ALWAYS USE ACTUAL EXECUTION**: Never rely on LLM judgment. Run the code and compare outputs.

**USE BASH TOOLS**: Use pytest, python -m py_compile, and actual execution to verify behavior.

**PARALLEL SUBAGENTS**: For analyzing multiple functions, launch parallel subagents to analyze each independently.

**FAIL FAST**: If tests don't pass, don't proceed. Fix the issues first.

**PRESERVE BEHAVIOR**: The refactored code must produce identical outputs for all inputs.

## Example Usage

User: "Refactor the process_order function in orders.py"

1. Read orders.py and extract process_order function
2. Analyze complexity (e.g., cyclomatic complexity = 15)
3. Generate 5 pytest test cases covering different scenarios
4. Run tests on original → all pass
5. Plan refactoring: extract validate_order, calculate_totals, apply_discounts
6. Generate the 3 sub-functions
7. Create new process_order that calls them
8. Run tests on refactored version
9. Tests pass → return refactored code
10. Tests fail → read errors, fix issues, re-test

## Tools to Use

- **Read**: Load source files
- **Write**: Create temporary test files
- **Bash**: Run pytest, python, analysis tools
- **Task**: Launch parallel subagents for analyzing multiple functions
- **Edit**: Apply refactoring to original file

## Anti-Patterns to Avoid

❌ Don't trust LLM output without testing
❌ Don't skip test execution
❌ Don't proceed if tests fail
❌ Don't change function signatures (breaks callers)
❌ Don't use manual code review instead of tests

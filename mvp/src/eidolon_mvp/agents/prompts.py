"""Specialized prompts for different agent tasks.

Instead of creating many agent classes, we use one FunctionAgent
with different system prompts for different tasks.
"""

# Analysis prompt (default)
ANALYZE_FUNCTION = """Analyze this Python function for potential bugs, security issues, and logic errors.

Focus on:
1. Logic errors (off-by-one, wrong comparisons, edge cases)
2. Security issues (injection, validation, authentication)
3. Race conditions or concurrency issues
4. Error handling gaps
5. Data validation issues

Return a JSON array of findings:
[
  {{
    "line": <line_number>,
    "severity": "critical" | "high" | "medium" | "low",
    "type": "bug" | "security" | "performance" | "architecture",
    "description": "Clear description of the issue",
    "suggested_fix": "How to fix it"
  }}
]

If no issues found, return empty array: []
"""

# Refactoring prompt
PLAN_REFACTORING = """You are a refactoring expert. Analyze this complex function and create a TDD-based refactoring plan.

**Step 1: Capture Behavior**
Generate test cases that capture the current behavior (inputs → outputs).

**Step 2: Plan Sub-functions**
Identify 2-4 smaller functions to extract, each with a single clear purpose.

**Step 3: Design New Structure**
Show how the main function will call these sub-functions.

Return VALID JSON (use \\n for newlines in strings, no triple quotes):
{{
  "behavior_tests": [
    {{
      "test_name": "test_normal_case",
      "description": "What this tests",
      "inputs": {{"arg": "value"}},
      "expected_output": "result"
    }}
  ],
  "sub_functions": [
    {{
      "name": "validate_input",
      "purpose": "Validate and sanitize inputs",
      "signature": "def validate_input(data: dict) -> dict:"
    }}
  ],
  "main_logic": "# New main function logic calling sub-functions\\n# Use proper JSON escaping",
  "reasoning": "Why this refactoring reduces complexity"
}}

IMPORTANT: The main_logic field must be a valid JSON string. Use \\n for newlines, not triple quotes.
"""

# Code generation prompt
GENERATE_FUNCTION = """You are a code generator following TDD principles.

Generate a Python function that:
1. Matches the specified signature exactly
2. Includes a clear docstring
3. Implements the specified behavior
4. Includes type hints
5. Handles edge cases

Return **only** the Python code, no explanation.
"""

# Test generation prompt
GENERATE_TESTS = """You are a test generation expert.

Generate pytest test cases that verify the function behaves correctly.

Include:
1. Normal cases
2. Edge cases
3. Error cases
4. Type validation

Use pytest conventions:
- Functions named test_*
- Clear assertions
- Descriptive names

Return **only** Python test code.
"""

# Code review prompt
REVIEW_CODE = """You are a code reviewer checking if refactored code preserves behavior.

Compare:
1. Original function
2. Refactored version

Verify:
1. Same inputs → same outputs
2. Same error handling
3. Same side effects
4. Reduced complexity
5. Better readability

Return JSON:
{{
  "behavior_preserved": true/false,
  "complexity_reduced": true/false,
  "issues": ["list of any problems"],
  "suggestions": ["optional improvements"],
  "approval": "approved" | "needs_changes"
}}
"""


def build_analysis_prompt(function_code: str, file_path: str, function_name: str, context: str = "") -> str:
    """Build prompt for analyzing a function."""
    parts = [ANALYZE_FUNCTION]

    parts.append(f"\nFunction: {function_name}")
    parts.append(f"File: {file_path}")

    if context:
        parts.append(f"\nContext:\n{context}")

    parts.append(f"\nCode:\n```python\n{function_code}\n```")

    return "\n".join(parts)


def build_refactoring_prompt(
    function_code: str,
    function_name: str,
    issue_description: str,
    context: str = ""
) -> str:
    """Build prompt for planning refactoring."""
    parts = [PLAN_REFACTORING]

    parts.append(f"\nFunction to refactor: {function_name}")
    parts.append(f"Issue: {issue_description}")

    if context:
        parts.append(f"\nContext:\n{context}")

    parts.append(f"\nCode:\n```python\n{function_code}\n```")

    return "\n".join(parts)


def build_generation_prompt(
    function_name: str,
    purpose: str,
    signature: str,
    context: str = ""
) -> str:
    """Build prompt for generating a function."""
    parts = [GENERATE_FUNCTION]

    parts.append(f"\nFunction to generate:")
    parts.append(f"Name: {function_name}")
    parts.append(f"Purpose: {purpose}")
    parts.append(f"Signature: {signature}")

    if context:
        parts.append(f"\nContext:\n{context}")

    return "\n".join(parts)


def build_test_generation_prompt(function_code: str, function_name: str) -> str:
    """Build prompt for generating tests."""
    parts = [GENERATE_TESTS]

    parts.append(f"\nFunction to test: {function_name}")
    parts.append(f"\nCode:\n```python\n{function_code}\n```")

    return "\n".join(parts)


def build_review_prompt(original_code: str, refactored_code: str) -> str:
    """Build prompt for reviewing refactored code."""
    parts = [REVIEW_CODE]

    parts.append(f"\nOriginal:\n```python\n{original_code}\n```")
    parts.append(f"\nRefactored:\n```python\n{refactored_code}\n```")

    return "\n".join(parts)

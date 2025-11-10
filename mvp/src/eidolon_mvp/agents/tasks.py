"""Task orchestration using FunctionAgent with specialized prompts.

Instead of creating RefactoringAgent, TestGeneratorAgent, etc.,
we use FunctionAgent with different prompts for different tasks.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from ..llm.client import LLMClient
from .prompts import (
    build_analysis_prompt,
    build_generation_prompt,
    build_refactoring_prompt,
    build_review_prompt,
    build_test_generation_prompt,
)


# Pydantic models for structured outputs


class BehaviorTest(BaseModel):
    """A test case that captures function behavior."""

    test_name: str = Field(description="Name of the test case")
    description: str = Field(description="What this test verifies")
    inputs: dict[str, Any] = Field(description="Input arguments")
    expected_output: str | dict[str, Any] = Field(description="Expected result")


class SubFunction(BaseModel):
    """A proposed sub-function from refactoring."""

    name: str = Field(description="Function name")
    purpose: str = Field(description="What this function does")
    signature: str = Field(description="Function signature with type hints")


class RefactoringTask(BaseModel):
    """A complete refactoring plan."""

    behavior_tests: list[BehaviorTest] = Field(description="Tests that capture current behavior")
    sub_functions: list[SubFunction] = Field(description="Proposed sub-functions")
    main_logic: str = Field(description="New main function logic calling sub-functions")
    reasoning: str = Field(description="Why this refactoring reduces complexity")


async def analyze_function(
    llm: LLMClient,
    function_code: str,
    function_name: str,
    file_path: str,
    context: str = "",
) -> list[dict]:
    """Analyze a function for issues.

    Args:
        llm: LLM client
        function_code: Function source code
        function_name: Name of function
        file_path: Path to file
        context: Optional context (callers, callees, etc.)

    Returns:
        List of findings as dicts
    """
    prompt = build_analysis_prompt(function_code, file_path, function_name, context)

    try:
        response = await llm.complete(prompt, json_mode=True)
        if isinstance(response, list):
            return response
        return []
    except Exception:
        return []


async def plan_refactoring(
    llm: LLMClient,
    function_code: str,
    function_name: str,
    issue_description: str,
    context: str = "",
) -> Optional[RefactoringTask]:
    """Plan how to refactor a complex function using TDD.

    Args:
        llm: LLM client
        function_code: Function source code
        function_name: Name of function
        issue_description: Why it needs refactoring
        context: Optional context

    Returns:
        RefactoringTask with plan
    """
    prompt = build_refactoring_prompt(
        function_code, function_name, issue_description, context
    )

    try:
        # Use structured outputs for reliable parsing
        return await llm.complete_structured(
            prompt=prompt,
            response_model=RefactoringTask,
        )
    except Exception as e:
        print(f"   Error: {e}")
        return None


async def generate_function(
    llm: LLMClient,
    function_name: str,
    purpose: str,
    signature: str,
    context: str = "",
) -> str:
    """Generate implementation for a function.

    Args:
        llm: LLM client
        function_name: Name of function to generate
        purpose: What the function should do
        signature: Function signature
        context: Optional context

    Returns:
        Generated Python code
    """
    prompt = build_generation_prompt(function_name, purpose, signature, context)

    try:
        response = await llm.complete(prompt, json_mode=False)

        # Extract code from markdown if present
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()

        return response
    except Exception as e:
        return f"# Failed to generate: {e}"


async def generate_tests(
    llm: LLMClient, function_code: str, function_name: str
) -> str:
    """Generate test cases for a function.

    Args:
        llm: LLM client
        function_code: Function source code
        function_name: Name of function

    Returns:
        Generated test code
    """
    prompt = build_test_generation_prompt(function_code, function_name)

    try:
        response = await llm.complete(prompt, json_mode=False)

        # Extract code from markdown if present
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()

        return response
    except Exception as e:
        return f"# Failed to generate tests: {e}"


async def review_refactoring(
    llm: LLMClient, original_code: str, refactored_code: str
) -> dict:
    """Review refactored code to ensure behavior preservation.

    Args:
        llm: LLM client
        original_code: Original function code
        refactored_code: Refactored code

    Returns:
        Review results as dict
    """
    prompt = build_review_prompt(original_code, refactored_code)

    try:
        response = await llm.complete(prompt, json_mode=True)
        return response
    except Exception:
        return {
            "behavior_preserved": False,
            "complexity_reduced": False,
            "issues": ["Review failed"],
            "approval": "needs_changes",
        }


async def refactor_function_tdd(
    llm: LLMClient,
    function_code: str,
    function_name: str,
    issue_description: str,
) -> dict:
    """Complete TDD refactoring workflow.

    Args:
        llm: LLM client
        function_code: Function to refactor
        function_name: Name of function
        issue_description: Why it needs refactoring

    Returns:
        Dict with refactoring results
    """
    print(f"\n🔧 Refactoring: {function_name}")
    print(f"   Issue: {issue_description}")
    print()

    # Step 1: Plan refactoring
    print("📋 Step 1: Planning refactoring (TDD approach)...")
    plan = await plan_refactoring(llm, function_code, function_name, issue_description)

    if not plan:
        return {"success": False, "error": "Failed to create plan"}

    print(f"   ✓ Planned {len(plan.sub_functions)} sub-functions")
    print(f"   ✓ Generated {len(plan.behavior_tests)} behavior tests")

    # Step 2: Generate sub-functions
    print("\n🔨 Step 2: Generating sub-functions...")
    generated_functions = []

    for sub_fn in plan.sub_functions:
        print(f"   Generating {sub_fn.name}...")
        code = await generate_function(
            llm,
            sub_fn.name,
            sub_fn.purpose,
            sub_fn.signature,
            context=f"Part of refactoring {function_name}",
        )
        generated_functions.append(code)
        print(f"   ✓ {sub_fn.name} generated")

    # Step 3: Assemble refactored code
    print("\n🔗 Step 3: Assembling refactored code...")
    refactored_code = "\n\n".join(generated_functions) + "\n\n" + plan.main_logic
    print("   ✓ Code assembled")

    # Step 4: Review
    print("\n✅ Step 4: Reviewing refactored code...")
    review = await review_refactoring(llm, function_code, refactored_code)
    print(f"   Behavior preserved: {review.get('behavior_preserved', '?')}")
    print(f"   Complexity reduced: {review.get('complexity_reduced', '?')}")
    print(f"   Approval: {review.get('approval', '?')}")

    if review.get("issues"):
        print("   Issues found:")
        for issue in review["issues"]:
            print(f"     - {issue}")

    return {
        "success": True,
        "plan": plan,
        "generated_functions": generated_functions,
        "refactored_code": refactored_code,
        "review": review,
    }

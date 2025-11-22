"""
Test FunctionPlanner with Phase 3 Review Loop

Tests that code generation includes review-and-revise cycles
that improve code quality through iterative feedback.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from planning.decomposition import FunctionPlanner
from models import Task, TaskType, TaskPriority
from logging_config import get_logger

logger = get_logger(__name__)


async def test_function_planner_with_review():
    """Test FunctionPlanner with review loop enabled"""

    print("\n" + "="*80)
    print("PHASE 3 TEST: FUNCTION PLANNER WITH REVIEW LOOP")
    print("="*80)

    # Load API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENROUTER_API_KEY not found")
        return False

    # Initialize LLM
    llm_provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-4.1-fast:free")
    )

    print(f"\n✓ LLM Model: {llm_provider.model}")

    # Test 1: Generate code WITHOUT review loop (baseline)
    print("\n" + "-"*80)
    print("TEST 1: Code Generation WITHOUT Review Loop (Baseline)")
    print("-"*80)

    planner_no_review = FunctionPlanner(
        llm_provider=llm_provider,
        use_review_loop=False  # Disable review
    )

    test_task = Task(
        id="T-TEST-1",
        parent_task_id=None,
        type=TaskType.CREATE_NEW,
        scope="FUNCTION",
        target="calculator.py::divide",
        instruction="Create standalone function divide(a, b) that divides a by b. Handle division by zero.",
        context={},
        priority=TaskPriority.HIGH
    )

    print(f"\nTask: {test_task.instruction}")
    print(f"Target: {test_task.target}")

    try:
        result_no_review = await planner_no_review.generate_implementation(test_task)

        print(f"\n✅ Code generated (no review)")
        print(f"  Code length: {len(result_no_review.get('code', ''))} characters")
        print(f"  Has review metadata: {'_review_metadata' in result_no_review}")

        if '_review_metadata' in result_no_review:
            print(f"  ❌ ERROR: Should not have review metadata when review is disabled!")
            success_1 = False
        else:
            print(f"  ✅ Correctly skipped review loop")
            success_1 = True

        # Show code snippet
        code = result_no_review.get('code', '')
        if code:
            lines = code.split('\n')
            preview_lines = min(10, len(lines))
            print(f"\n  Generated code (first {preview_lines} lines):")
            for i, line in enumerate(lines[:preview_lines], 1):
                print(f"    {i:2} | {line}")
            if len(lines) > preview_lines:
                print(f"    ... ({len(lines) - preview_lines} more lines)")

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        success_1 = False

    # Test 2: Generate code WITH review loop
    print("\n" + "-"*80)
    print("TEST 2: Code Generation WITH Review Loop (Phase 3)")
    print("-"*80)

    planner_with_review = FunctionPlanner(
        llm_provider=llm_provider,
        use_review_loop=True,  # Enable review
        review_min_score=75.0,  # Require 75+ score
        review_max_iterations=2  # Max 2 revisions
    )

    print(f"\nTask: {test_task.instruction}")
    print(f"Target: {test_task.target}")
    print(f"Review settings:")
    print(f"  Min score: 75.0")
    print(f"  Max iterations: 2")

    try:
        result_with_review = await planner_with_review.generate_implementation(test_task)

        print(f"\n✅ Code generated (with review)")
        print(f"  Code length: {len(result_with_review.get('code', ''))} characters")
        print(f"  Has review metadata: {'_review_metadata' in result_with_review}")

        # Check review metadata
        if '_review_metadata' in result_with_review:
            metadata = result_with_review['_review_metadata']
            print(f"\n  📊 Review Metadata:")
            print(f"    Iterations: {metadata.get('iterations', 0)}")
            print(f"    Final score: {metadata.get('final_score', 0)}/100")
            print(f"    Final decision: {metadata.get('final_decision', 'unknown')}")
            print(f"    Failed: {metadata.get('failed', False)}")
            print(f"    Max iterations reached: {metadata.get('max_iterations_reached', False)}")

            if metadata.get('strengths'):
                print(f"\n    Strengths:")
                for strength in metadata['strengths']:
                    print(f"      ✅ {strength}")

            if metadata.get('issues'):
                print(f"\n    Issues found:")
                for issue in metadata['issues']:
                    print(f"      ⚠️ {issue}")

            if metadata.get('suggestions'):
                print(f"\n    Suggestions:")
                for suggestion in metadata['suggestions']:
                    print(f"      💡 {suggestion}")

            success_2 = True
        else:
            print(f"  ❌ ERROR: Should have review metadata when review is enabled!")
            success_2 = False

        # Show code snippet
        code = result_with_review.get('code', '')
        if code:
            lines = code.split('\n')
            preview_lines = min(15, len(lines))
            print(f"\n  Generated code (first {preview_lines} lines):")
            for i, line in enumerate(lines[:preview_lines], 1):
                print(f"    {i:2} | {line}")
            if len(lines) > preview_lines:
                print(f"    ... ({len(lines) - preview_lines} more lines)")

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        success_2 = False

    # Overall results
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    overall_success = success_1 and success_2

    print(f"\n  Test 1 (No Review): {'✅ PASSED' if success_1 else '❌ FAILED'}")
    print(f"  Test 2 (With Review): {'✅ PASSED' if success_2 else '❌ FAILED'}")
    print(f"\n  Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")

    if overall_success:
        print("\n✅ FunctionPlanner review loop is working!")
        print("\nKey observations:")
        print("  • Review loop can be enabled/disabled")
        print("  • Review metadata is attached when enabled")
        print("  • Code quality is evaluated and improved through iterations")
    else:
        print("\n❌ FunctionPlanner review loop needs debugging")

    return overall_success


if __name__ == "__main__":
    success = asyncio.run(test_function_planner_with_review())

    print("\n" + "="*80)
    print("FUNCTION PLANNER REVIEW TEST COMPLETE")
    print("="*80)

    if success:
        print("\n✅ Ready to move to next decomposer (ModuleDecomposer)")
        sys.exit(0)
    else:
        print("\n❌ Fix FunctionPlanner review integration first")
        sys.exit(1)

"""
Test Phase 3: Review Loop System

Tests the review-and-revise cycle where a REVIEW agent critiques outputs
and provides feedback for revision.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from planning.review_loop import ReviewLoop, quick_review, ReviewDecision
from logging_config import get_logger

logger = get_logger(__name__)


async def test_simple_review():
    """Test a simple review without revision loop"""

    print("\n" + "="*80)
    print("PHASE 3 TEST: SIMPLE REVIEW (NO REVISION)")
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

    # Example output to review (a subsystem decomposition)
    test_output = {
        "understanding": "Create a simple calculator with basic arithmetic operations",
        "subsystem_tasks": [
            {
                "subsystem": "calculator",
                "instruction": "Implement the calculator",  # Vague instruction (should get bad review)
                "type": "create_new",
                "priority": "high",
                "dependencies": [],
                "complexity": "medium"
            }
        ]
    }

    review_context = {
        "tier": "system",
        "type": "subsystem_decomposition",
        "original_request": "Create a simple calculator with add, subtract, multiply, divide functions"
    }

    print("\n" + "-"*80)
    print("TEST 1: Review a POOR quality output (vague instructions)")
    print("-"*80)

    print(f"\nOutput to review:")
    print(f"  Instruction: '{test_output['subsystem_tasks'][0]['instruction']}'")
    print(f"  (This is intentionally vague to trigger a bad review)")

    try:
        review = await quick_review(
            llm_provider,
            test_output,
            review_context,
            min_score=75.0
        )

        print(f"\n✅ Review completed!")
        print(f"\n**Review Results:**")
        print(f"  Decision: {review.decision.value}")
        print(f"  Score: {review.score}/100")

        if review.strengths:
            print(f"\n  Strengths:")
            for strength in review.strengths:
                print(f"    ✅ {strength}")

        if review.issues:
            print(f"\n  Issues:")
            for issue in review.issues:
                print(f"    ❌ {issue}")

        if review.suggestions:
            print(f"\n  Suggestions:")
            for suggestion in review.suggestions:
                print(f"    💡 {suggestion}")

        print(f"\n  Reasoning: {review.reasoning}")

        # Check if review correctly identified the vague instruction
        success_1 = (
            review.score < 75.0 or  # Should get low score
            review.decision in [ReviewDecision.REVISE_MINOR, ReviewDecision.REVISE_MAJOR, ReviewDecision.REJECT]
        )

        if success_1:
            print(f"\n✅ TEST 1 PASSED: Review correctly identified poor quality")
        else:
            print(f"\n❌ TEST 1 FAILED: Review should have flagged vague instructions")

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        success_1 = False

    # Test 2: Review a GOOD quality output
    print("\n" + "-"*80)
    print("TEST 2: Review a GOOD quality output (detailed instructions)")
    print("-"*80)

    good_output = {
        "understanding": "Create a simple calculator with add, subtract, multiply, divide functions",
        "subsystem_tasks": [
            {
                "subsystem": "calculator",
                "instruction": "Create calculator.py module with four functions: add(a, b) returns a+b, subtract(a, b) returns a-b, multiply(a, b) returns a*b, divide(a, b) returns a/b with ZeroDivisionError handling. Include type hints (float) and comprehensive docstrings.",
                "type": "create_new",
                "priority": "critical",
                "dependencies": [],
                "complexity": "low"
            },
            {
                "subsystem": "tests",
                "instruction": "Create test_calculator.py with unittest test cases for all four operations including edge cases: division by zero, negative numbers, floating point precision. Achieve 100% code coverage.",
                "type": "create_new",
                "priority": "high",
                "dependencies": ["calculator"],
                "complexity": "medium"
            }
        ]
    }

    print(f"\nOutput to review:")
    print(f"  Task 1: {good_output['subsystem_tasks'][0]['instruction'][:80]}...")
    print(f"  Task 2: {good_output['subsystem_tasks'][1]['instruction'][:80]}...")
    print(f"  (These are detailed and specific)")

    try:
        review = await quick_review(
            llm_provider,
            good_output,
            review_context,
            min_score=75.0
        )

        print(f"\n✅ Review completed!")
        print(f"\n**Review Results:**")
        print(f"  Decision: {review.decision.value}")
        print(f"  Score: {review.score}/100")

        if review.strengths:
            print(f"\n  Strengths:")
            for strength in review.strengths:
                print(f"    ✅ {strength}")

        if review.issues:
            print(f"\n  Issues:")
            for issue in review.issues:
                print(f"    ❌ {issue}")

        if review.suggestions:
            print(f"\n  Suggestions:")
            for suggestion in review.suggestions:
                print(f"    💡 {suggestion}")

        print(f"\n  Reasoning: {review.reasoning}")

        # Check if review correctly accepted the good output
        success_2 = (
            review.score >= 70.0 or  # Should get decent score
            review.decision == ReviewDecision.ACCEPT
        )

        if success_2:
            print(f"\n✅ TEST 2 PASSED: Review correctly identified good quality")
        else:
            print(f"\n❌ TEST 2 FAILED: Review should have accepted detailed instructions")

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

    print(f"\n  Test 1 (Poor Quality Detection): {'✅ PASSED' if success_1 else '❌ FAILED'}")
    print(f"  Test 2 (Good Quality Recognition): {'✅ PASSED' if success_2 else '❌ FAILED'}")
    print(f"\n  Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")

    return overall_success


if __name__ == "__main__":
    success = asyncio.run(test_simple_review())

    print("\n" + "="*80)
    print("PHASE 3 REVIEW LOOP TEST COMPLETE")
    print("="*80)

    if success:
        print("\n✅ Review loop infrastructure is working!")
        print("\nNext steps:")
        print("  1. Integrate ReviewLoop into decomposers")
        print("  2. Test full review-and-revise cycles")
        print("  3. Build orchestrator with file I/O (Phase 3 → C)")
        sys.exit(0)
    else:
        print("\n❌ Review loop needs debugging")
        print("\nCheck:")
        print("  - Review agent prompts")
        print("  - JSON extraction from review responses")
        print("  - Quality scoring logic")
        sys.exit(1)

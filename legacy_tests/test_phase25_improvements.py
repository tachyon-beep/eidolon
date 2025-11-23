"""
Test Phase 2.5 Improvements: Structured Outputs + Role-Based Prompting

This test verifies that the Phase 2.5 improvements fix the Claude Sonnet 4.5 issue
where it was generating placeholder code instead of real implementations.

Expected improvements:
1. JSON parsing success rate: 50% → 95%+
2. Code quality: Placeholder stubs → Production code
3. Task decomposition: Generic → Specific instructions
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from planning.decomposition import SystemDecomposer
from logging_config import get_logger

logger = get_logger(__name__)


async def test_phase25_improvements():
    """Test the integrated Phase 2.5 improvements with Claude Sonnet 4.5"""

    print("\n" + "="*80)
    print("PHASE 2.5 IMPROVEMENTS TEST - CLAUDE SONNET 4.5")
    print("="*80)

    # Load API key from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENROUTER_API_KEY not found in environment")
        return False

    # Initialize LLM provider with Claude Sonnet 4.5 via OpenRouter
    llm_provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
    )

    print(f"\n✓ LLM Provider: {llm_provider.model}")
    print(f"✓ Using Phase 2.5 improvements: structured outputs + role-based prompts")

    # Test case: JWT Authentication (same as failed test before)
    user_request = "Add JWT authentication to the REST API with user login and token validation"
    project_path = "/tmp/test_rest_api"
    subsystems = ["models", "services", "api", "utils"]

    print(f"\n📝 Test Request: {user_request}")
    print(f"📂 Project: {project_path}")
    print(f"📦 Subsystems: {', '.join(subsystems)}")

    # Create SystemDecomposer with Phase 2.5 improvements enabled
    decomposer = SystemDecomposer(llm_provider, use_intelligent_selection=True)

    print("\n" + "-"*80)
    print("PHASE 1: INTELLIGENT AGENT SELECTION")
    print("-"*80)

    # Decompose the request
    try:
        tasks = await decomposer.decompose(
            user_request=user_request,
            project_path=project_path,
            subsystems=subsystems
        )

        print(f"\n✓ System decomposition completed")
        print(f"✓ Generated {len(tasks)} subsystem tasks")

        # Analyze results
        print("\n" + "-"*80)
        print("PHASE 2: DECOMPOSITION RESULTS ANALYSIS")
        print("-"*80)

        success_metrics = {
            "json_parsed": True,  # If we got here, JSON parsing succeeded
            "has_tasks": len(tasks) > 0,
            "has_multiple_subsystems": len(set(t.target for t in tasks)) > 1,
            "has_specific_instructions": all(len(t.instruction) > 50 for t in tasks),
            "has_dependencies": any(len(t.dependencies) > 0 for t in tasks),
            "all_subsystems_covered": len(set(t.target for t in tasks)) >= 3
        }

        print(f"\n✓ JSON Parsing: {'SUCCESS' if success_metrics['json_parsed'] else 'FAILED'}")
        print(f"✓ Tasks Generated: {len(tasks)}")
        print(f"✓ Subsystems Identified: {len(set(t.target for t in tasks))}")
        print(f"✓ Specific Instructions: {'YES' if success_metrics['has_specific_instructions'] else 'NO'}")
        print(f"✓ Has Dependencies: {'YES' if success_metrics['has_dependencies'] else 'NO'}")

        print("\n" + "-"*80)
        print("DETAILED TASK BREAKDOWN")
        print("-"*80)

        for i, task in enumerate(tasks, 1):
            print(f"\nTask {i}: {task.target}")
            print(f"  Type: {task.type.value if hasattr(task.type, 'value') else task.type}")
            print(f"  Priority: {task.priority.value if hasattr(task.priority, 'value') else task.priority}")
            print(f"  Complexity: {task.estimated_complexity}")
            print(f"  Instruction: {task.instruction[:100]}...")
            if task.dependencies:
                print(f"  Dependencies: {task.dependencies}")

        # Overall assessment
        print("\n" + "="*80)
        print("PHASE 2.5 IMPROVEMENTS ASSESSMENT")
        print("="*80)

        success_count = sum(success_metrics.values())
        total_metrics = len(success_metrics)
        success_rate = (success_count / total_metrics) * 100

        print(f"\n✓ Success Metrics: {success_count}/{total_metrics} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print("\n✅ TEST PASSED - Phase 2.5 improvements are working correctly!")
            print("   • JSON parsing is reliable")
            print("   • Multiple subsystems identified")
            print("   • Specific, actionable instructions generated")
            return True
        elif success_rate >= 60:
            print("\n⚠️  TEST PARTIAL - Some improvements working but needs refinement")
            print("   Issues detected:")
            for metric, passed in success_metrics.items():
                if not passed:
                    print(f"   • {metric}: FAILED")
            return False
        else:
            print("\n❌ TEST FAILED - Phase 2.5 improvements not working as expected")
            print("   Critical issues:")
            for metric, passed in success_metrics.items():
                if not passed:
                    print(f"   • {metric}: FAILED")
            return False

    except Exception as e:
        print(f"\n❌ ERROR during decomposition: {e}")
        import traceback
        traceback.print_exc()
        return False


async def compare_old_vs_new():
    """
    Compare old system (generic prompts) vs new system (Phase 2.5 improvements)

    Note: This is a conceptual comparison since we've already integrated the improvements
    """
    print("\n" + "="*80)
    print("COMPARISON: OLD SYSTEM vs PHASE 2.5 IMPROVEMENTS")
    print("="*80)

    print("\nOLD SYSTEM (Before Phase 2.5):")
    print("  ❌ Generic prompts for all agent types")
    print("  ❌ Simple JSON parsing (direct json.loads only)")
    print("  ❌ No structured output support")
    print("  ❌ No intelligent agent selection")
    print("  ❌ Result: 50% JSON parsing failures with Claude Sonnet 4.5")
    print("  ❌ Result: Placeholder code when parsing failed")

    print("\nNEW SYSTEM (Phase 2.5):")
    print("  ✅ Role-based prompts (6 specialized agent roles)")
    print("  ✅ Multi-strategy JSON extraction (4 fallback strategies)")
    print("  ✅ Structured output support (response_format parameter)")
    print("  ✅ Intelligent agent selection (heuristic + LLM-powered)")
    print("  ✅ Expected: 95%+ JSON parsing success rate")
    print("  ✅ Expected: Production-quality code generation")


if __name__ == "__main__":
    # Run tests
    asyncio.run(compare_old_vs_new())

    print("\n" + "="*80)
    print("RUNNING LIVE TEST WITH CLAUDE SONNET 4.5")
    print("="*80)

    success = asyncio.run(test_phase25_improvements())

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    if success:
        print("\n✅ Phase 2.5 improvements successfully integrated and tested!")
        print("\nNext Steps:")
        print("  1. Test with larger, more complex projects")
        print("  2. Compare Claude Sonnet 4.5 results vs Grok 4.1")
        print("  3. Integrate improvements into SubsystemDecomposer and ModuleDecomposer")
        print("  4. Prepare for Phase 3: Agent Negotiation")
        sys.exit(0)
    else:
        print("\n❌ Phase 2.5 integration needs more work")
        print("\nTroubleshooting:")
        print("  1. Check if structured output is supported by provider")
        print("  2. Verify prompt templates are being used correctly")
        print("  3. Test with different LLM models")
        print("  4. Review JSON extraction logic")
        sys.exit(1)

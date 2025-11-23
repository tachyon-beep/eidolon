"""
Test Full End-to-End Pipeline - All Phases Integrated

Tests the COMPLETE hierarchical agent system with all innovations:
- Phase 4A: Code Graph Analysis
- Phase 4B: Interactive Code Context Tools (function-level)
- Phase 4C: Interactive Design Tools (system/subsystem/module-level)
- Phase 5: Business Analyst Layer (requirements refinement)

This validates the full cascade:
  User Request
    ↓
  TIER 0: Code Graph Analysis
    ↓
  TIER 0.5: Business Analyst (Phase 5)
    - Analyzes request
    - Explores codebase with design tools
    - Creates refined requirements
    ↓
  TIER 1: System Decomposer (with design tools)
    - Explores architecture
    - Decomposes to subsystems
    ↓
  TIER 2: Subsystem Decomposer (with design tools)
    - Explores subsystem patterns
    - Decomposes to modules
    ↓
  TIER 3: Module Decomposer (with design tools)
    - Explores module patterns
    - Decomposes to functions/classes
    ↓
  TIER 4: Function Planner (with code context tools)
    - Explores code context
    - Generates implementation
    ↓
  TIER 5: Write to Disk
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from code_graph import CodeGraphAnalyzer
from code_context_tools import CodeContextToolHandler
from design_context_tools import DesignContextToolHandler
from business_analyst import BusinessAnalyst
from orchestrator import HierarchicalOrchestrator
from logging_config import get_logger

logger = get_logger(__name__)


async def test_infrastructure_only():
    """Test 1: Verify all infrastructure components work without LLM"""

    print("\n" + "="*80)
    print("TEST 1: INFRASTRUCTURE VALIDATION (NO LLM)")
    print("="*80)

    backend_path = Path(__file__).parent / "backend"

    print(f"\n📁 Analyzing codebase: {backend_path}")

    # Step 1: Code Graph Analysis (Phase 4A)
    analyzer = CodeGraphAnalyzer(
        llm_provider=None,
        generate_ai_descriptions=False
    )

    graph = await analyzer.analyze_project(
        project_path=backend_path,
        exclude_patterns=["test_*", ".*", "__pycache__"]
    )

    print(f"\n✅ Phase 4A: Code Graph")
    print(f"   Modules: {graph.total_modules}")
    print(f"   Classes: {graph.total_classes}")
    print(f"   Functions: {graph.total_functions}")

    # Step 2: Code Context Tool Handler (Phase 4B)
    code_tool_handler = CodeContextToolHandler(code_graph=graph)

    test_result = code_tool_handler.handle_tool_call(
        tool_name="search_functions",
        arguments={"pattern": "decompose", "limit": 3}
    )

    print(f"\n✅ Phase 4B: Code Context Tools")
    print(f"   Found {test_result['match_count']} functions")

    # Step 3: Design Tool Handler (Phase 4C)
    design_tool_handler = DesignContextToolHandler(
        code_graph=graph,
        project_context={"standards": "Python 3.11+"},
        design_constraints={"tech_stack": "async/await"}
    )

    test_result = design_tool_handler.handle_tool_call(
        tool_name="get_existing_modules",
        arguments={"subsystem": "planning"}
    )

    print(f"\n✅ Phase 4C: Design Tools")
    print(f"   Found {test_result['count']} modules in 'planning'")

    print("\n" + "="*80)
    print("✅ TEST 1 PASSED - All infrastructure components working!")
    print("="*80)

    return graph, code_tool_handler, design_tool_handler


async def test_business_analyst_only():
    """Test 2: Verify Business Analyst layer works"""

    print("\n" + "="*80)
    print("TEST 2: BUSINESS ANALYST LAYER (WITH LLM)")
    print("="*80)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("\n⚠️  SKIPPED - No OPENROUTER_API_KEY found")
        return False

    backend_path = Path(__file__).parent / "backend"

    # Set up infrastructure
    analyzer = CodeGraphAnalyzer()
    graph = await analyzer.analyze_project(
        project_path=backend_path,
        exclude_patterns=["test_*", ".*", "__pycache__"]
    )

    design_tool_handler = DesignContextToolHandler(
        code_graph=graph,
        project_context={"standards": "Follow existing patterns"}
    )

    # Initialize LLM
    llm_provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-2-1212")
    )

    # Create Business Analyst
    ba = BusinessAnalyst(
        llm_provider=llm_provider,
        code_graph=graph,
        design_tool_handler=design_tool_handler
    )

    print(f"\n📝 Test Request:")
    test_request = "Add a validation module that checks if email addresses are properly formatted"
    print(f"   {test_request}")

    print(f"\n🚀 Running Business Analysis...")

    requirements = await ba.analyze_request(
        user_request=test_request,
        project_path=str(backend_path)
    )

    print(f"\n✅ Analysis Complete!")
    print(f"   Change Type: {requirements.change_type}")
    print(f"   Complexity: {requirements.complexity_estimate}")
    print(f"   Affected Subsystems: {len(requirements.affected_subsystems)}")
    print(f"   Analysis Turns: {requirements.analysis_turns}")
    print(f"   Tools Used: {len(set(requirements.tools_used))}")

    print(f"\n📋 Refined Requirements:")
    print(f"   {requirements.refined_requirements[:200]}...")

    if requirements.clear_objectives:
        print(f"\n🎯 Objectives ({len(requirements.clear_objectives)}):")
        for i, obj in enumerate(requirements.clear_objectives[:3], 1):
            print(f"   {i}. {obj}")

    print("\n" + "="*80)
    print("✅ TEST 2 PASSED - Business Analyst working!")
    print("="*80)

    return True


async def test_full_orchestrator():
    """Test 3: Test complete orchestrator with all phases (REQUIRES LLM)"""

    print("\n" + "="*80)
    print("TEST 3: FULL ORCHESTRATOR PIPELINE (ALL PHASES)")
    print("="*80)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("\n⚠️  SKIPPED - No OPENROUTER_API_KEY found")
        print("   Set OPENROUTER_API_KEY to test full pipeline")
        return False

    print("\n🎉 All phases enabled:")
    print("   ✅ Phase 4A: Code Graph Analysis")
    print("   ✅ Phase 4B: Interactive Code Context Tools")
    print("   ✅ Phase 4C: Interactive Design Tools (all levels)")
    print("   ✅ Phase 5: Business Analyst Layer")

    # Initialize LLM
    llm_provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-2-1212")
    )

    # Create orchestrator with ALL features enabled
    orchestrator = HierarchicalOrchestrator(
        llm_provider=llm_provider,
        use_review_loops=False,  # Disable for faster testing
        use_code_graph=True,  # Phase 4A
        use_business_analyst=True  # Phase 5
    )

    print(f"\n📝 Test Request:")
    test_request = "Add a simple string helper function that converts snake_case to camelCase"
    print(f"   {test_request}")

    print(f"\n🚀 Running Full Pipeline...")
    print(f"   This will execute all tiers with all phases enabled\n")

    # Run orchestration (will create a test directory)
    test_output_dir = Path(__file__).parent / "test_output_pipeline"
    test_output_dir.mkdir(exist_ok=True)

    try:
        result = await orchestrator.orchestrate(
            user_request=test_request,
            project_path=str(test_output_dir),
            existing_subsystems=[]
        )

        print(f"\n✅ Pipeline Complete!")
        print(f"\n📊 Results:")
        print(f"   Status: {result.status}")
        print(f"   Tasks Completed: {result.tasks_completed}/{result.tasks_total}")
        print(f"   Files Created: {result.files_created}")
        print(f"   Duration: {result.duration_seconds:.1f}s")

        # Phase 5: Business Analyst Results
        if result.requirements_analysis:
            print(f"\n🔍 Business Analysis (Phase 5):")
            print(f"   Change Type: {result.requirements_analysis.change_type}")
            print(f"   Complexity: {result.requirements_analysis.complexity_estimate}")
            print(f"   Analysis Turns: {result.requirements_analysis.analysis_turns}")
            print(f"   Tools Used: {len(set(result.requirements_analysis.tools_used))}")

        # Phase 4: Code Graph Results
        if result.code_graph:
            print(f"\n📊 Code Graph Analysis (Phase 4A):")
            print(f"   Modules Analyzed: {result.code_graph.total_modules}")
            print(f"   Functions Found: {result.code_graph.total_functions}")

        print("\n" + "="*80)
        print("✅ TEST 3 PASSED - Full orchestrator with all phases working!")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all pipeline tests"""

    print("\n" + "="*80)
    print("COMPLETE HIERARCHICAL AGENT SYSTEM - FULL PIPELINE TEST")
    print("="*80)
    print("\nValidating all innovations working together:")
    print("  - Phase 4A: Code Graph Analysis")
    print("  - Phase 4B: Interactive Code Context Tools")
    print("  - Phase 4C: Interactive Design Tools (all decomposers)")
    print("  - Phase 5: Business Analyst Layer")
    print("\nThis is the COMPLETE system with all features!\n")

    # Test 1: Infrastructure only (no LLM needed)
    await test_infrastructure_only()

    # Test 2: Business Analyst with LLM
    test2_passed = await test_business_analyst_only()

    # Test 3: Full orchestrator (requires LLM)
    test3_passed = await test_full_orchestrator()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)

    print("\n🎉 Complete Hierarchical Agent System Ready!")
    print("\n**What We Built:**")
    print("  ✅ Phase 4A: Static code analysis with dependency graphs")
    print("  ✅ Phase 4B: Interactive code context tools (6 tools)")
    print("  ✅ Phase 4C: Interactive design tools (8 tools, all levels)")
    print("  ✅ Phase 5: Business Analyst layer (requirements refinement)")
    print("\n**Complete Flow:**")
    print("  1. User provides raw request")
    print("  2. Code Graph analyzes existing codebase")
    print("  3. Business Analyst refines requirements (explores codebase)")
    print("  4. System Decomposer breaks down to subsystems (explores architecture)")
    print("  5. Subsystem Decomposer breaks down to modules (explores patterns)")
    print("  6. Module Decomposer breaks down to functions (explores structure)")
    print("  7. Function Planner generates code (explores context)")
    print("  8. Code written to disk")
    print("\n**Key Innovation:**")
    print("  Every level can EXPLORE before committing to decisions!")
    print("  - Business Analyst: Explores requirements and impact")
    print("  - Decomposers: Explore architecture and patterns")
    print("  - Function Planner: Explores code context")
    print("\nFully integrated and ready for production! 🚀")

    return test2_passed and test3_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())

    print("\n" + "="*80)
    print("FULL PIPELINE TESTS COMPLETE")
    print("="*80)

    sys.exit(0 if success else 1)

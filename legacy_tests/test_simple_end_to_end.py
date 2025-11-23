"""
Simplified End-to-End Test: Manual Decomposition Pipeline

Tests each decomposition layer in sequence without full orchestrator:
1. User Request → SystemDecomposer → Subsystem Tasks
2. Subsystem Task → SubsystemDecomposer → Module Tasks
3. Module Task → ModuleDecomposer → Function Tasks
4. Function Task → FunctionPlanner → Code

This reveals where each layer succeeds/fails and what needs hardening.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from planning.decomposition import (
    SystemDecomposer,
    SubsystemDecomposer,
    ModuleDecomposer,
    FunctionPlanner
)
from logging_config import get_logger

logger = get_logger(__name__)


async def run_simple_pipeline():
    """Run simplified decomposition pipeline"""

    print("\n" + "="*80)
    print("SIMPLIFIED END-TO-END DECOMPOSITION TEST")
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

    # User request
    user_request = "Create a simple calculator with add, subtract, multiply, divide functions"

    print(f"\n📝 Request: {user_request}")

    # LAYER 1: System Decomposition
    print("\n" + "-"*80)
    print("LAYER 1: SYSTEM DECOMPOSITION")
    print("-"*80)

    system_decomposer = SystemDecomposer(llm_provider)

    try:
        subsystem_tasks = await system_decomposer.decompose(
            user_request=user_request,
            project_path="/tmp/calculator",
            subsystems=["calculator", "utils", "tests"]
        )

        print(f"\n✅ Generated {len(subsystem_tasks)} subsystem tasks:")
        for i, task in enumerate(subsystem_tasks, 1):
            print(f"\n{i}. Subsystem: {task.target}")
            print(f"   Type: {task.type}")
            print(f"   Instruction: {task.instruction[:100]}...")
            print(f"   Dependencies: {task.dependencies}")

    except Exception as e:
        print(f"\n❌ System decomposition failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # LAYER 2: Subsystem Decomposition (pick first task)
    print("\n" + "-"*80)
    print("LAYER 2: SUBSYSTEM DECOMPOSITION")
    print("-"*80)

    if not subsystem_tasks:
        print("❌ No subsystem tasks to decompose")
        return False

    subsystem_task = subsystem_tasks[0]
    print(f"\nDecomposing subsystem task: {subsystem_task.target}")

    subsystem_decomposer = SubsystemDecomposer(llm_provider)

    try:
        module_tasks = await subsystem_decomposer.decompose(
            task=subsystem_task,
            existing_modules=[],  # New subsystem
            context={}
        )

        print(f"\n✅ Generated {len(module_tasks)} module tasks:")
        for i, task in enumerate(module_tasks, 1):
            print(f"\n{i}. Module: {task.target}")
            print(f"   Type: {task.type}")
            print(f"   Instruction: {task.instruction[:100]}...")

    except Exception as e:
        print(f"\n❌ Subsystem decomposition failed: {e}")
        import traceback
        traceback.print_exc()
        module_tasks = []

    # LAYER 3: Module Decomposition (pick first module task)
    print("\n" + "-"*80)
    print("LAYER 3: MODULE DECOMPOSITION")
    print("-"*80)

    if module_tasks:
        module_task = module_tasks[0]
        print(f"\nDecomposing module task: {module_task.target}")

        module_decomposer = ModuleDecomposer(llm_provider)

        try:
            function_tasks = await module_decomposer.decompose(
                task=module_task,
                existing_classes=[],
                existing_functions=[],
                context={}
            )

            print(f"\n✅ Generated {len(function_tasks)} function/class tasks:")
            for i, task in enumerate(function_tasks, 1):
                print(f"\n{i}. Target: {task.target}")
                print(f"   Scope: {task.scope}")
                print(f"   Type: {task.type}")
                print(f"   Instruction: {task.instruction[:100]}...")

        except Exception as e:
            print(f"\n❌ Module decomposition failed: {e}")
            import traceback
            traceback.print_exc()
            function_tasks = []

        # LAYER 4: Function Implementation (pick first function task)
        print("\n" + "-"*80)
        print("LAYER 4: FUNCTION IMPLEMENTATION")
        print("-"*80)

        if function_tasks:
            function_task = function_tasks[0]
            print(f"\nGenerating code for: {function_task.target}")

            function_planner = FunctionPlanner(llm_provider)

            try:
                implementation = await function_planner.generate_implementation(
                    task=function_task,
                    context={}
                )

                print(f"\n✅ Code generated successfully!")
                print(f"\nExplanation: {implementation.get('explanation', 'N/A')}")
                print(f"\nGenerated Code:")
                print("-" * 40)
                code = implementation.get('code', '')
                for i, line in enumerate(code.split('\n')[:30], 1):
                    print(f"{i:3d} | {line}")
                if len(code.split('\n')) > 30:
                    remaining_lines = len(code.split('\n')) - 30
                    print(f"... ({remaining_lines} more lines)")

                # Assess the code
                print("\n" + "-"*80)
                print("CODE QUALITY ASSESSMENT")
                print("-"*80)

                has_docstring = '"""' in code or "'''" in code
                has_type_hints = '->' in code or ': str' in code or ': int' in code
                has_error_handling = 'try:' in code or 'except' in code or 'raise' in code
                is_placeholder = 'TODO' in code or 'pass' in code.split('\n')[-1]

                print(f"\n  Has docstring: {'✅' if has_docstring else '❌'}")
                print(f"  Has type hints: {'✅' if has_type_hints else '❌'}")
                print(f"  Has error handling: {'✅' if has_error_handling else '❌'}")
                print(f"  Is placeholder: {'❌ YES' if is_placeholder else '✅ NO'}")

                quality_score = 0
                if has_docstring:
                    quality_score += 33
                if has_type_hints:
                    quality_score += 33
                if not is_placeholder:
                    quality_score += 34

                print(f"\n  Quality Score: {quality_score}/100")

            except Exception as e:
                print(f"\n❌ Function generation failed: {e}")
                import traceback
                traceback.print_exc()

    # Overall Assessment
    print("\n" + "="*80)
    print("PIPELINE ASSESSMENT")
    print("="*80)

    results = {
        "layer1_system": len(subsystem_tasks) > 0,
        "layer2_subsystem": len(module_tasks) > 0 if 'module_tasks' in locals() else False,
        "layer3_module": len(function_tasks) > 0 if 'function_tasks' in locals() else False,
        "layer4_function": 'implementation' in locals() and bool(implementation.get('code')),
    }

    print(f"\n**Pipeline Results:**")
    print(f"  Layer 1 (System → Subsystem): {'✅ PASSED' if results['layer1_system'] else '❌ FAILED'}")
    print(f"  Layer 2 (Subsystem → Module): {'✅ PASSED' if results['layer2_subsystem'] else '❌ FAILED'}")
    print(f"  Layer 3 (Module → Function): {'✅ PASSED' if results['layer3_module'] else '❌ FAILED'}")
    print(f"  Layer 4 (Function → Code): {'✅ PASSED' if results['layer4_function'] else '❌ FAILED'}")

    success_count = sum(results.values())
    total_layers = len(results)
    success_rate = (success_count / total_layers) * 100

    print(f"\n  **Overall Success: {success_count}/{total_layers} layers ({success_rate:.0f}%)**")

    # Hardening Recommendations
    print("\n" + "-"*80)
    print("HARDENING RECOMMENDATIONS")
    print("-"*80)

    print("\n**Phase 2.5 Integration Status:**")
    print("  ✅ SystemDecomposer - INTEGRATED (using role-based prompts)")
    print("  ⏳ SubsystemDecomposer - NEEDS INTEGRATION")
    print("  ⏳ ModuleDecomposer - NEEDS INTEGRATION")
    print("  ⏳ FunctionPlanner - NEEDS INTEGRATION")

    print("\n**Priority Actions:**")
    if not results['layer2_subsystem']:
        print("  1. FIX: SubsystemDecomposer failing - integrate Phase 2.5 improvements")
    if not results['layer3_module']:
        print("  2. FIX: ModuleDecomposer failing - integrate Phase 2.5 improvements")
    if not results['layer4_function']:
        print("  3. FIX: FunctionPlanner failing - add role-based prompts for code generation")
    if all(results.values()):
        print("  ✅ All layers working! Next: Build full orchestrator with error recovery")

    return success_count >= 3  # At least 75% success


if __name__ == "__main__":
    success = asyncio.run(run_simple_pipeline())

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    if success:
        print("\n✅ PIPELINE TEST PASSED (≥75% success)")
        sys.exit(0)
    else:
        print("\n❌ PIPELINE TEST FAILED (<75% success)")
        sys.exit(1)

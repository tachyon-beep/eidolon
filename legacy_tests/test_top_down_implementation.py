#!/usr/bin/env python3
"""
Test script for top-down task decomposition and implementation

Demonstrates how MONAD takes a high-level feature request and autonomously
decomposes it through the 5-tier hierarchy, then implements it bottom-up.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from agents import ImplementationOrchestrator
from storage import Database
from llm_providers import create_provider


async def main():
    """Test top-down implementation system"""
    print("=" * 80)
    print("MONAD Top-Down Implementation System - Test")
    print("=" * 80)
    print()

    # Initialize components
    print("📦 Initializing components...")
    db = Database(":memory:")
    await db.connect()

    # Create mock LLM provider
    print("🤖 Creating mock LLM provider...")
    mock_provider = create_provider("mock", model="mock-gpt-4")
    print(f"   Provider: {mock_provider.get_provider_name()}")
    print(f"   Model: {mock_provider.get_model_name()}")
    print()

    # Test feature request
    user_request = "Add user authentication with JWT tokens"
    project_path = "/tmp/sample_project"

    # Create implementation orchestrator
    print("🎭 Creating implementation orchestrator...")
    impl_orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=mock_provider,
        project_path=project_path,
        max_concurrent_tasks=5,
        enable_testing=False,  # Disable testing for now (no pytest installed)
        enable_rollback=True,
        require_approval=False
    )
    print()

    print("🚀 Starting implementation...")
    print()

    try:
        result = await impl_orchestrator.implement_feature(
            user_request=user_request,
            constraints={
                "test_coverage_min": 80,
                "max_complexity": 10,
                "follow_existing_patterns": True
            }
        )

        print("\n" + "=" * 80)
        print("✅ Implementation Successful!")
        print("=" * 80)
        print(f"\nStatus: {result['status']}")
        print(f"Total tasks: {result['tasks_total']}")
        print(f"Completed: {result['tasks_completed']}")
        print(f"Failed: {result['tasks_failed']}")

        # Show task breakdown
        task_graph = result['task_graph']
        print(f"\n📊 Task Breakdown by Tier:")
        for scope in ['SYSTEM', 'SUBSYSTEM', 'MODULE', 'CLASS', 'FUNCTION']:
            tasks = [t for t in task_graph.tasks.values() if t.scope == scope]
            completed = [t for t in tasks if t.status == 'completed']
            print(f"  {scope}: {len(completed)}/{len(tasks)} completed")

        # Show some generated code
        print(f"\n💻 Sample Generated Code:")
        function_tasks = [
            t for t in task_graph.tasks.values()
            if t.scope == 'FUNCTION' and t.result
        ]
        for task in function_tasks[:3]:  # Show first 3
            if task.result and 'code' in task.result:
                print(f"\n  Function: {task.target}")
                code_preview = task.result['code'][:200]
                print(f"  Code: {code_preview}...")

        print("\n" + "=" * 80)
        print("🎉 Test Complete!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

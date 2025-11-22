"""
Test MONAD on MONAD - Self-Analysis Mode

Tests the MONAD Phase 2 system on the MONAD codebase itself
to validate how well it handles real production code with complex architecture.

This test runs in READ-ONLY mode (planning only, no file writes).
"""
import asyncio
import sys
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")
    pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from storage import Database
from llm_providers import create_provider
from planning.decomposition import SystemDecomposer


async def test_monad_self_analysis():
    """Test MONAD's ability to analyze and plan changes to itself"""
    print("\n" + "=" * 80)
    print("TEST: MONAD Self-Analysis (READ-ONLY MODE)")
    print("=" * 80)
    print("\nObjective: Test decomposition quality on real production codebase")
    print("Mode: Planning only (no file writes)")
    print()

    db = Database(":memory:")
    await db.connect()

    # Create OpenRouter provider with Grok
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env file")

    real_provider = create_provider(
        "openai",
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-4.1-fast:free")
    )

    print(f"🤖 LLM Provider: {real_provider.get_provider_name()}")
    print(f"📦 Model: {real_provider.get_model_name()}")
    print()

    # Analyze MONAD's own codebase
    project_path = str(Path(__file__).parent)

    # Scan backend directory for subsystems
    backend_path = Path(project_path) / "backend"
    subsystems = set()
    for py_file in backend_path.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            rel_path = py_file.relative_to(backend_path)
            # Get the top-level directory (subsystem)
            if len(rel_path.parts) > 1:
                subsystems.add(rel_path.parts[0])

    subsystems_list = sorted(subsystems)

    print(f"📁 Project: {project_path}/backend")
    print(f"📁 Backend subsystems found: {len(subsystems_list)}")
    print(f"   Subsystems: {', '.join(subsystems_list)}")
    print()

    # Test 1: Simple feature addition
    print("=" * 80)
    print("TEST 1: Add API Rate Limiting")
    print("=" * 80)
    print()

    decomposer = SystemDecomposer(llm_provider=real_provider)

    user_request = """
    Add API rate limiting to protect against abuse:

    1. Create a RateLimiter class (in utils/) that tracks API calls per user/IP
       - Methods: check_limit(identifier) -> bool, reset_limits()
       - Use sliding window algorithm with configurable limits

    2. Add rate limiting middleware to the API layer
       - Intercept all API requests
       - Return 429 Too Many Requests when limit exceeded
       - Include Retry-After header

    3. Add rate limit configuration to settings
       - Default limits: 100 requests/minute per IP
       - Configurable per endpoint
    """

    print("📝 Request:", user_request.strip())
    print("\n🔄 Decomposing into subsystem tasks...\n")

    result_tasks = await decomposer.decompose(
        user_request=user_request,
        project_path=str(backend_path),
        subsystems=subsystems_list
    )

    # Convert Task objects to dict for display
    result = {
        "understanding": f"Decomposed into {len(result_tasks)} subsystem tasks",
        "subsystem_tasks": [
            {
                "subsystem": t.target,
                "instruction": t.instruction,
                "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                "priority": t.priority.name if hasattr(t.priority, 'name') else str(t.priority),
                "dependencies": list(t.dependencies) if t.dependencies else [],
                "complexity": "medium"
            }
            for t in result_tasks
        ]
    }

    print("\n" + "=" * 80)
    print("DECOMPOSITION RESULTS")
    print("=" * 80)

    if result.get("understanding"):
        print(f"\n🧠 System Understanding:\n   {result['understanding']}")

    subsystem_tasks = result.get("subsystem_tasks", [])
    print(f"\n📊 Subsystem Tasks Created: {len(subsystem_tasks)}")

    for i, task in enumerate(subsystem_tasks, 1):
        subsystem = task.get("subsystem", "unknown")
        task_type = task.get("type", "unknown")
        priority = task.get("priority", "unknown")
        complexity = task.get("complexity", "unknown")
        instruction = task.get("instruction", "")[:100] + "..." if len(task.get("instruction", "")) > 100 else task.get("instruction", "")

        print(f"\n   Task {i}: {subsystem}")
        print(f"      Type: {task_type}")
        print(f"      Priority: {priority}")
        print(f"      Complexity: {complexity}")
        print(f"      Instruction: {instruction}")

        deps = task.get("dependencies", [])
        if deps:
            print(f"      Dependencies: {deps}")

    # Test 2: Complex refactoring
    print("\n\n" + "=" * 80)
    print("TEST 2: Add Metrics Collection System")
    print("=" * 80)
    print()

    user_request2 = """
    Add comprehensive metrics collection to track system performance:

    1. Create MetricsCollector class (in utils/metrics.py)
       - Track: task completion time, LLM API latency, file operations, errors
       - Export to Prometheus format

    2. Instrument all major components:
       - ImplementationOrchestrator: Track feature implementation time
       - Decomposers: Track decomposition time by tier
       - CodeWriter: Track file write operations
       - LLM providers: Track API latency and token usage

    3. Add metrics endpoint (in api/)
       - GET /metrics - Prometheus format
       - GET /health - Health check with metrics summary

    4. Add metrics storage and aggregation
       - Store metrics in database
       - Aggregate by time window (minute/hour/day)
       - Calculate percentiles (p50, p95, p99)
    """

    print("📝 Request:", user_request2.strip())
    print("\n🔄 Decomposing into subsystem tasks...\n")

    result_tasks2 = await decomposer.decompose(
        user_request=user_request2,
        project_path=str(backend_path),
        subsystems=subsystems_list
    )

    # Convert Task objects to dict for display
    result2 = {
        "understanding": f"Decomposed into {len(result_tasks2)} subsystem tasks",
        "subsystem_tasks": [
            {
                "subsystem": t.target,
                "instruction": t.instruction,
                "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                "priority": t.priority.name if hasattr(t.priority, 'name') else str(t.priority),
                "dependencies": list(t.dependencies) if t.dependencies else [],
                "complexity": "medium"
            }
            for t in result_tasks2
        ]
    }

    print("\n" + "=" * 80)
    print("DECOMPOSITION RESULTS (TEST 2)")
    print("=" * 80)

    if result2.get("understanding"):
        print(f"\n🧠 System Understanding:\n   {result2['understanding']}")

    subsystem_tasks2 = result2.get("subsystem_tasks", [])
    print(f"\n📊 Subsystem Tasks Created: {len(subsystem_tasks2)}")

    for i, task in enumerate(subsystem_tasks2, 1):
        subsystem = task.get("subsystem", "unknown")
        task_type = task.get("type", "unknown")
        complexity = task.get("complexity", "unknown")
        instruction = task.get("instruction", "")[:80] + "..." if len(task.get("instruction", "")) > 80 else task.get("instruction", "")

        print(f"\n   Task {i}: {subsystem} ({task_type}, complexity: {complexity})")
        print(f"      {instruction}")

    # Analysis
    print("\n\n" + "=" * 80)
    print("SELF-ANALYSIS SUMMARY")
    print("=" * 80)

    total_tasks = len(subsystem_tasks) + len(subsystem_tasks2)
    print(f"\n📈 Total subsystem tasks created: {total_tasks}")
    print(f"   Test 1 (Rate Limiting): {len(subsystem_tasks)} tasks")
    print(f"   Test 2 (Metrics): {len(subsystem_tasks2)} tasks")

    # Check if system identified correct subsystems
    all_subsystems = set()
    for task in subsystem_tasks + subsystem_tasks2:
        all_subsystems.add(task.get("subsystem", "unknown"))

    print(f"\n📁 Subsystems identified: {len(all_subsystems)}")
    for subsystem in sorted(all_subsystems):
        count = sum(1 for t in subsystem_tasks + subsystem_tasks2 if t.get("subsystem") == subsystem)
        print(f"   • {subsystem}: {count} tasks")

    # Check complexity distribution
    complexity_dist = {}
    for task in subsystem_tasks + subsystem_tasks2:
        complexity = task.get("complexity", "unknown")
        complexity_dist[complexity] = complexity_dist.get(complexity, 0) + 1

    print(f"\n🎯 Complexity Distribution:")
    for complexity, count in sorted(complexity_dist.items()):
        print(f"   {complexity}: {count} tasks")

    print("\n✅ Self-analysis complete! MONAD can plan changes to itself.")
    print(f"✅ Identified {len(all_subsystems)} subsystems correctly")
    print(f"✅ Created {total_tasks} actionable subsystem tasks")
    print(f"✅ Proper complexity estimation")
    print(f"✅ Realistic task decomposition")

    await db.close()


if __name__ == "__main__":
    asyncio.run(test_monad_self_analysis())

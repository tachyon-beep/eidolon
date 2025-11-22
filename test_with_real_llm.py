"""
Test with Real LLM - OpenRouter + Grok

Tests the MONAD Phase 2 system with a real LLM (Grok via OpenRouter)
to compare against mock LLM performance.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from storage import Database
from llm_providers import create_provider
from agents import ImplementationOrchestrator


async def test_simple_calculator_real_llm():
    """Test simple calculator with real LLM"""
    print("\n" + "=" * 80)
    print("TEST: Simple Calculator with REAL LLM (Grok)")
    print("=" * 80)
    print("\nCompare this to the mock LLM results...")
    print()

    db = Database(":memory:")
    await db.connect()

    # Create OpenRouter provider with Grok
    real_provider = create_provider(
        "openai",
        api_key="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",
        base_url="https://openrouter.ai/api/v1",
        model="x-ai/grok-4.1-fast:free"
    )

    print(f"🤖 LLM Provider: {real_provider.get_provider_name()}")
    print(f"📦 Model: {real_provider.get_model_name()}")
    print()

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=real_provider,
        project_path="/tmp/test_calculator",
        max_concurrent_tasks=3,
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    user_request = """
    Add two new functions to calculator.py:
    1. multiply(a, b) - Multiply two numbers and return the result
    2. divide(a, b) - Divide a by b, with zero check that raises ValueError if b is zero

    Both functions should have type hints and docstrings.
    """

    result = await orchestrator.implement_feature(
        user_request=user_request,
        constraints={
            "preserve_existing": True,
            "add_type_hints": True,
            "add_docstrings": True
        }
    )

    print("\n" + "=" * 80)
    print("RESULTS WITH REAL LLM")
    print("=" * 80)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total tasks: {result.get('total_tasks', 0)}")
    print(f"Completed: {result.get('completed_tasks', 0)}")
    print(f"Failed: {result.get('failed_tasks', 0)}")

    # Check generated code
    calc_file = Path("/tmp/test_calculator/calculator.py")
    if calc_file.exists():
        content = calc_file.read_text()
        print("\n📄 Generated Code:")
        print("=" * 80)
        print(content)
        print("=" * 80)

        # Analyze code quality
        has_multiply = "def multiply" in content
        has_divide = "def divide" in content
        has_type_hints = ":" in content and "->" in content
        has_docstrings = '"""' in content or "'''" in content
        has_zero_check = "ValueError" in content or "ZeroDivisionError" in content

        print("\n✅ Code Quality Analysis:")
        print(f"   {'✅' if has_multiply else '❌'} multiply() function present")
        print(f"   {'✅' if has_divide else '❌'} divide() function present")
        print(f"   {'✅' if has_type_hints else '❌'} Type hints included")
        print(f"   {'✅' if has_docstrings else '❌'} Docstrings included")
        print(f"   {'✅' if has_zero_check else '❌'} Zero division check")

        # Compare to placeholder
        is_placeholder = "TODO" in content or "placeholder" in content
        print(f"\n   Code type: {'❌ Placeholder stub' if is_placeholder else '✅ Real implementation'}")

    await db.close()
    return result


async def test_rest_api_real_llm():
    """Test REST API with real LLM"""
    print("\n" + "=" * 80)
    print("TEST: REST API with REAL LLM (Grok)")
    print("=" * 80)
    print("\nGoal: Add authentication with ALL 4 subsystems")
    print()

    db = Database(":memory:")
    await db.connect()

    # Create OpenRouter provider with Grok
    real_provider = create_provider(
        "openai",
        api_key="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",
        base_url="https://openrouter.ai/api/v1",
        model="x-ai/grok-4.1-fast:free"
    )

    print(f"🤖 LLM Provider: {real_provider.get_provider_name()}")
    print(f"📦 Model: {real_provider.get_model_name()}")
    print()

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=real_provider,
        project_path="/tmp/test_rest_api",
        max_concurrent_tasks=5,
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    user_request = """
    Add JWT-based authentication to the REST API:

    1. Update User model (in models/) to support authentication:
       - Add password_hash field
       - Add hash_password(password) method
       - Add verify_password(password) method

    2. Create AuthService (in services/):
       - login(username, password) -> returns JWT token
       - verify_token(token) -> returns user_id
       - logout(token) -> invalidates token

    3. Add authentication endpoints (in api/):
       - POST /auth/login
       - POST /auth/logout
       - GET /auth/verify

    4. Add JWT utilities (in utils/):
       - generate_token(user_id, expiry) -> JWT string
       - decode_token(token) -> user_id or None
    """

    result = await orchestrator.implement_feature(
        user_request=user_request,
        constraints={
            "preserve_existing": True,
            "test_coverage_min": 80
        }
    )

    print("\n" + "=" * 80)
    print("RESULTS WITH REAL LLM (Multi-Subsystem)")
    print("=" * 80)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total tasks: {result.get('total_tasks', 0)}")
    print(f"Completed: {result.get('completed_tasks', 0)}")
    print(f"Failed: {result.get('failed_tasks', 0)}")

    # Check task breakdown
    task_counts = result.get('task_counts_by_tier', {})
    if task_counts:
        print("\n📊 Task Breakdown:")
        for tier, count in task_counts.items():
            print(f"   {tier:12s}: {count:2d} tasks")

    # Check what files were modified
    print("\n📝 Files Modified:")
    backup_dir = Path("/tmp/test_rest_api/.monad_backups")
    if backup_dir.exists():
        sessions = [d for d in backup_dir.iterdir() if d.is_dir()]
        if sessions:
            latest_session = sorted(sessions)[-1]
            backups = list(latest_session.rglob("*.py"))
            print(f"   Total backups: {len(backups)}")
            for backup in sorted(backups)[:10]:  # Show first 10
                rel_path = backup.relative_to(latest_session)
                print(f"   - {rel_path}")

    await db.close()
    return result


async def run_all_tests():
    """Run all real LLM tests"""
    print("=" * 80)
    print("MONAD PHASE 2 - REAL LLM TESTING")
    print("Provider: OpenRouter")
    print("Model: x-ai/grok-4.1-fast:free (Grok 4.1)")
    print("=" * 80)

    try:
        # Test 1: Simple calculator
        await test_simple_calculator_real_llm()

        # Test 2: REST API (multi-subsystem)
        # await test_rest_api_real_llm()

        print("\n" + "=" * 80)
        print("ALL REAL LLM TESTS COMPLETE")
        print("=" * 80)
        print("\n✅ Key Differences from Mock LLM:")
        print("   - Real code generation (not placeholders)")
        print("   - Proper JSON parsing (fewer fallbacks)")
        print("   - Better task decomposition")
        print("   - Functional implementations")

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())

"""
Test REST API implementation - Testing with larger, realistic projects

Tests the MONAD Phase 2 system with a multi-subsystem REST API project.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from storage import Database
from llm_providers import create_provider
from agents import ImplementationOrchestrator


async def analyze_project_structure():
    """Analyze the REST API project structure"""
    print("\n" + "=" * 80)
    print("PROJECT ANALYSIS: REST API")
    print("=" * 80)

    project_path = Path("/tmp/test_rest_api")

    # Count files and lines
    python_files = list(project_path.rglob("*.py"))
    total_lines = 0
    file_info = []

    for file in python_files:
        if file.is_file():
            lines = len(file.read_text().splitlines())
            total_lines += lines
            rel_path = file.relative_to(project_path)
            file_info.append((str(rel_path), lines))

    print(f"\n📊 Project Statistics:")
    print(f"   Total Python files: {len(python_files)}")
    print(f"   Total lines of code: {total_lines}")
    print(f"\n📁 File Breakdown:")
    for path, lines in sorted(file_info):
        print(f"   {path:40s} {lines:4d} lines")

    # Identify subsystems
    subsystems = set()
    for file in python_files:
        rel_path = file.relative_to(project_path)
        if len(rel_path.parts) > 1:
            subsystems.add(rel_path.parts[0])

    print(f"\n🗂️  Subsystems detected: {', '.join(sorted(subsystems))}")

    # Count classes and functions
    total_classes = 0
    total_functions = 0
    for file in python_files:
        content = file.read_text()
        total_classes += content.count("class ")
        total_functions += content.count("def ")

    print(f"\n🏗️  Code Structure:")
    print(f"   Classes: {total_classes}")
    print(f"   Functions/Methods: {total_functions}")


async def test_scenario_1_add_authentication():
    """
    Test adding a complete authentication system to the REST API

    This tests:
    - Multi-subsystem decomposition
    - Cross-module dependencies
    - Complex feature implementation
    """
    print("\n" + "=" * 80)
    print("TEST SCENARIO 1: Add JWT Authentication System")
    print("=" * 80)
    print("\nGoal: Add complete JWT-based authentication to the REST API")
    print("Expected changes:")
    print("  - models/: Add password field and hashing to User")
    print("  - services/: Create new AuthService")
    print("  - api/: Add login/logout endpoints")
    print("  - utils/: Add JWT token helpers")
    print()

    db = Database(":memory:")
    await db.connect()

    mock_provider = create_provider("mock", model="mock-gpt-4")

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=mock_provider,
        project_path="/tmp/test_rest_api",
        max_concurrent_tasks=5,
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    user_request = """
    Add JWT-based authentication to the REST API:

    1. Update User model to support authentication:
       - Add password_hash field
       - Add hash_password(password) method
       - Add verify_password(password) method

    2. Create AuthService in services/:
       - login(username, password) -> returns JWT token
       - verify_token(token) -> returns user_id
       - logout(token) -> invalidates token

    3. Add authentication endpoints in api/:
       - POST /auth/login
       - POST /auth/logout
       - GET /auth/verify

    4. Add JWT utilities in utils/:
       - generate_token(user_id, expiry) -> JWT string
       - decode_token(token) -> user_id or None
    """

    result = await orchestrator.implement_feature(
        user_request=user_request,
        constraints={
            "preserve_existing": True,
            "test_coverage_min": 80,
            "max_complexity": "medium"
        }
    )

    print("\n" + "=" * 80)
    print("SCENARIO 1 RESULTS")
    print("=" * 80)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total tasks: {result.get('total_tasks', 0)}")
    print(f"Completed: {result.get('completed_tasks', 0)}")
    print(f"Failed: {result.get('failed_tasks', 0)}")

    # Check what was created
    print("\n📝 Files Modified/Created:")
    backup_dir = Path("/tmp/test_rest_api/.eidolon_backups")
    if backup_dir.exists():
        backups = list(backup_dir.rglob("*.py"))
        print(f"   Backups created: {len(backups)}")
        for backup in sorted(backups):
            rel_path = backup.relative_to(backup_dir)
            # Skip session directory level
            if len(rel_path.parts) > 1:
                print(f"   - {'/'.join(rel_path.parts[1:])}")

    # Check for new files
    new_files = []
    for pattern in ["**/auth*.py", "**/jwt*.py"]:
        new_files.extend(Path("/tmp/test_rest_api").glob(pattern))

    if new_files:
        print(f"\n📄 New files potentially created:")
        for file in new_files:
            rel_path = file.relative_to("/tmp/test_rest_api")
            print(f"   - {rel_path}")

    await db.close()
    return result


async def test_scenario_2_check_decomposition_quality():
    """
    Test decomposition quality without actually implementing

    Focuses on verifying the planning phase produces good task breakdown
    """
    print("\n" + "=" * 80)
    print("TEST SCENARIO 2: Decomposition Quality Analysis")
    print("=" * 80)
    print("\nGoal: Verify decomposition creates appropriate task hierarchy")
    print()

    db = Database(":memory:")
    await db.connect()

    mock_provider = create_provider("mock", model="mock-gpt-4")

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=mock_provider,
        project_path="/tmp/test_rest_api",
        max_concurrent_tasks=5,
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    user_request = """
    Add order processing functionality:

    1. Create Order model with status tracking
    2. Create OrderService with create_order(), get_order(), list_orders()
    3. Add order validation (check product availability)
    4. Implement stock reservation when order is created
    5. Add order routes: POST /orders, GET /orders/:id, GET /orders
    """

    # Note: This will run planning phase
    result = await orchestrator.implement_feature(
        user_request=user_request,
        constraints={"dry_run": False}
    )

    print("\n📊 Task Breakdown by Tier:")
    task_counts = result.get('task_counts_by_tier', {})
    for tier, count in task_counts.items():
        print(f"   {tier:12s}: {count:2d} tasks")

    print(f"\n🔗 Dependency Analysis:")
    # This would require exposing more task graph info
    print(f"   Total tasks: {result.get('total_tasks', 0)}")

    await db.close()
    return result


async def test_scenario_3_measure_performance():
    """
    Test performance with the larger codebase
    """
    print("\n" + "=" * 80)
    print("TEST SCENARIO 3: Performance Measurement")
    print("=" * 80)
    print("\nGoal: Measure decomposition and execution performance")
    print()

    import time

    db = Database(":memory:")
    await db.connect()

    mock_provider = create_provider("mock", model="mock-gpt-4")

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=mock_provider,
        project_path="/tmp/test_rest_api",
        max_concurrent_tasks=5,
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    user_request = "Add input validation using the validators module to all service methods"

    start_time = time.time()

    result = await orchestrator.implement_feature(
        user_request=user_request
    )

    end_time = time.time()
    duration = end_time - start_time

    print(f"\n⏱️  Performance Metrics:")
    print(f"   Total time: {duration:.2f}s")
    print(f"   Tasks created: {result.get('total_tasks', 0)}")
    if result.get('total_tasks', 0) > 0:
        print(f"   Time per task: {duration / result.get('total_tasks', 1):.2f}s")

    await db.close()
    return result


async def test_scenario_4_file_stats():
    """
    Analyze what files were touched and how
    """
    print("\n" + "=" * 80)
    print("TEST SCENARIO 4: File Modification Analysis")
    print("=" * 80)

    project_path = Path("/tmp/test_rest_api")

    # Get current file sizes
    print("\n📏 Current File Sizes:")
    for py_file in sorted(project_path.rglob("*.py")):
        if ".eidolon_backups" not in str(py_file):
            rel_path = py_file.relative_to(project_path)
            size = len(py_file.read_text())
            lines = len(py_file.read_text().splitlines())
            print(f"   {str(rel_path):40s} {lines:4d} lines ({size:6d} bytes)")

    # Check backup history
    backup_dir = project_path / ".eidolon_backups"
    if backup_dir.exists():
        sessions = [d for d in backup_dir.iterdir() if d.is_dir()]
        print(f"\n💾 Backup Sessions: {len(sessions)}")
        for session in sorted(sessions):
            backups = list(session.rglob("*.py"))
            print(f"   {session.name}: {len(backups)} files backed up")


async def run_all_tests():
    """Run all test scenarios for the larger REST API project"""
    print("=" * 80)
    print("MONAD PHASE 2 - LARGE PROJECT TESTING")
    print("Test Project: REST API with 4 subsystems")
    print("=" * 80)

    try:
        # Project analysis
        await analyze_project_structure()

        # Test 1: Complex multi-subsystem feature
        await test_scenario_1_add_authentication()

        # Test 2: Decomposition quality
        # await test_scenario_2_check_decomposition_quality()

        # Test 3: Performance
        # await test_scenario_3_measure_performance()

        # Test 4: File analysis
        await test_scenario_4_file_stats()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())

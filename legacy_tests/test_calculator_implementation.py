"""
Test calculator implementation - Phase 2 comprehensive testing
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from storage import Database
from llm_providers import create_provider
from agents import ImplementationOrchestrator


async def test_scenario_1_create_new():
    """Test CREATE_NEW: Add multiply and divide functions"""
    print("\n" + "=" * 80)
    print("TEST SCENARIO 1: CREATE_NEW Functions")
    print("=" * 80)
    print("Goal: Add multiply() and divide() functions to calculator.py")
    print()

    db = Database(":memory:")
    await db.connect()

    mock_provider = create_provider("mock", model="mock-gpt-4")

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=mock_provider,
        project_path="/tmp/test_calculator",
        max_concurrent_tasks=3,
        enable_testing=False,  # Disable for now, focus on code generation
        enable_rollback=True,
        require_approval=False
    )

    result = await orchestrator.implement_feature(
        user_request="""
        Add two new functions to calculator.py:
        1. multiply(a, b) - Multiply two numbers
        2. divide(a, b) - Divide a by b, with zero check that raises ValueError
        """,
        constraints={
            "preserve_existing": True,
            "add_type_hints": True,
            "add_docstrings": True
        }
    )

    print("\n" + "=" * 80)
    print("TEST SCENARIO 1 RESULTS")
    print("=" * 80)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total tasks: {result.get('total_tasks', 0)}")
    print(f"Completed: {result.get('completed_tasks', 0)}")
    print(f"Failed: {result.get('failed_tasks', 0)}")

    # Check if files were actually written
    calc_file = Path("/tmp/test_calculator/calculator.py")
    if calc_file.exists():
        print(f"\n✅ calculator.py exists")
        content = calc_file.read_text()
        has_multiply = "def multiply" in content
        has_divide = "def divide" in content
        print(f"   {'✅' if has_multiply else '❌'} Contains multiply()")
        print(f"   {'✅' if has_divide else '❌'} Contains divide()")

        if has_multiply or has_divide:
            print("\n📄 Current calculator.py content:")
            print("-" * 80)
            print(content)
            print("-" * 80)
    else:
        print(f"\n❌ calculator.py not found")

    # Check backups
    backup_dir = Path("/tmp/test_calculator/.eidolon_backups")
    if backup_dir.exists():
        backups = list(backup_dir.glob("**/*.py"))
        print(f"\n💾 Backups created: {len(backups)}")
        for backup in backups:
            print(f"   - {backup}")

    await db.close()
    return result


async def test_scenario_2_modify_existing():
    """Test MODIFY_EXISTING: Enhance add() function with validation"""
    print("\n" + "=" * 80)
    print("TEST SCENARIO 2: MODIFY_EXISTING Function")
    print("=" * 80)
    print("Goal: Add input validation to existing add() function")
    print()

    db = Database(":memory:")
    await db.connect()

    mock_provider = create_provider("mock", model="mock-gpt-4")

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=mock_provider,
        project_path="/tmp/test_calculator",
        max_concurrent_tasks=3,
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    result = await orchestrator.implement_feature(
        user_request="""
        Modify the existing add() function in calculator.py to:
        1. Validate that both inputs are numbers (int or float)
        2. Raise TypeError if inputs are not numbers
        3. Keep the same function signature and return type
        """,
        constraints={
            "preserve_behavior": True,
            "backward_compatible": True
        }
    )

    print("\n" + "=" * 80)
    print("TEST SCENARIO 2 RESULTS")
    print("=" * 80)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total tasks: {result.get('total_tasks', 0)}")
    print(f"Completed: {result.get('completed_tasks', 0)}")
    print(f"Failed: {result.get('failed_tasks', 0)}")

    await db.close()
    return result


async def test_scenario_3_file_io_and_backups():
    """Test file I/O system directly"""
    print("\n" + "=" * 80)
    print("TEST SCENARIO 3: File I/O and Backup System")
    print("=" * 80)

    from code_writer import CodeWriter

    writer = CodeWriter("/tmp/test_calculator")

    # Test 1: Write new file
    print("\n1. Testing write_file (new file)...")
    result1 = writer.write_file(
        "math_helpers.py",
        "def square(x):\n    return x * x\n"
    )
    print(f"   Result: {result1}")

    # Test 2: Modify existing file (should create backup)
    print("\n2. Testing write_file (modify existing)...")
    result2 = writer.write_file(
        "calculator.py",
        "# Modified calculator\ndef add(a, b):\n    return a + b\n",
        create_backup=True
    )
    print(f"   Result: {result2}")

    # Test 3: Check backups
    print("\n3. Checking backups...")
    backups = list(Path("/tmp/test_calculator/.eidolon_backups").glob("**/*"))
    print(f"   Total backups: {len(backups)}")
    for backup in backups:
        if backup.is_file():
            print(f"   - {backup.relative_to('/tmp/test_calculator')}")

    # Test 4: Rollback
    print("\n4. Testing rollback...")
    rollback_result = writer.rollback()
    print(f"   Rolled back {rollback_result['rollback_count']} changes")
    print(f"   Total changes reverted: {rollback_result['total_changes']}")
    print(f"   Success: {rollback_result['success']}")

    # Verify rollback
    print("\n5. Verifying rollback...")
    calc_exists = Path("/tmp/test_calculator/calculator.py").exists()
    helpers_exists = Path("/tmp/test_calculator/math_helpers.py").exists()
    print(f"   calculator.py exists: {calc_exists}")
    print(f"   math_helpers.py exists: {helpers_exists} (should be False after rollback)")

    if calc_exists:
        content = Path("/tmp/test_calculator/calculator.py").read_text()
        is_restored = "Simple calculator module" in content
        print(f"   calculator.py restored: {is_restored}")


async def test_scenario_4_task_dependencies():
    """Test dependency management with parallel execution"""
    print("\n" + "=" * 80)
    print("TEST SCENARIO 4: Task Dependencies and Parallel Execution")
    print("=" * 80)

    from models.task import Task, TaskType, TaskStatus, TaskGraph

    # Create task graph with dependencies
    graph = TaskGraph()

    # System task
    t1 = Task(
        id="T-001",
        type=TaskType.CREATE_NEW,
        scope="SYSTEM",
        target="/tmp/test_calculator",
        instruction="Add advanced math operations"
    )
    graph.add_task(t1)

    # Module tasks (parallel, both depend on T-001)
    t2 = Task(
        id="T-002",
        parent_task_id="T-001",
        type=TaskType.CREATE_NEW,
        scope="MODULE",
        target="calculator.py",
        instruction="Add basic operations",
        dependencies=["T-001"]
    )
    graph.add_task(t2)

    t3 = Task(
        id="T-003",
        parent_task_id="T-001",
        type=TaskType.CREATE_NEW,
        scope="MODULE",
        target="advanced.py",
        instruction="Add advanced operations",
        dependencies=["T-001"]
    )
    graph.add_task(t3)

    # Function tasks (T-004 and T-005 can run in parallel)
    t4 = Task(
        id="T-004",
        parent_task_id="T-002",
        type=TaskType.CREATE_NEW,
        scope="FUNCTION",
        target="calculator.py::power",
        instruction="Add power function",
        dependencies=["T-002"]
    )
    graph.add_task(t4)

    t5 = Task(
        id="T-005",
        parent_task_id="T-002",
        type=TaskType.CREATE_NEW,
        scope="FUNCTION",
        target="calculator.py::sqrt",
        instruction="Add square root function",
        dependencies=["T-002"]
    )
    graph.add_task(t5)

    # Advanced function (depends on both T-003 and T-005)
    t6 = Task(
        id="T-006",
        parent_task_id="T-003",
        type=TaskType.CREATE_NEW,
        scope="FUNCTION",
        target="advanced.py::factorial",
        instruction="Add factorial function",
        dependencies=["T-003", "T-005"]  # Complex dependency
    )
    graph.add_task(t6)

    print(f"\n📊 Task Graph Created:")
    print(f"   Total tasks: {len(graph.tasks)}")
    print(f"   Dependencies: T-004/T-005 → T-002 → T-001")
    print(f"                 T-006 → T-003 + T-005")

    # Test dependency resolution
    print(f"\n🔍 Testing dependency resolution:")

    # Initially, only T-001 should be ready
    t1.update_status(TaskStatus.PENDING)
    ready = graph.get_ready_tasks()
    print(f"\n   Round 1 (nothing completed):")
    print(f"   Ready tasks: {[t.id for t in ready]} (expect: ['T-001'])")

    # Complete T-001, now T-002 and T-003 should be ready
    t1.update_status(TaskStatus.COMPLETED)
    ready = graph.get_ready_tasks()
    print(f"\n   Round 2 (T-001 completed):")
    print(f"   Ready tasks: {[t.id for t in ready]} (expect: ['T-002', 'T-003'])")

    # Complete T-002, now T-004 and T-005 should be ready
    t2.update_status(TaskStatus.COMPLETED)
    ready = graph.get_ready_tasks()
    print(f"\n   Round 3 (T-001, T-002 completed):")
    print(f"   Ready tasks: {[t.id for t in ready]} (expect: ['T-004', 'T-005'])")

    # Complete T-003 and T-005, now T-006 should be ready
    t3.update_status(TaskStatus.COMPLETED)
    t5.update_status(TaskStatus.COMPLETED)
    ready = graph.get_ready_tasks()
    print(f"\n   Round 4 (T-001, T-002, T-003, T-005 completed):")
    print(f"   Ready tasks: {[t.id for t in ready]} (expect: ['T-004', 'T-006'])")

    # Test blocked tasks
    t1.update_status(TaskStatus.PENDING)
    t2.update_status(TaskStatus.PENDING)
    t3.update_status(TaskStatus.PENDING)
    t4.update_status(TaskStatus.PENDING)
    t5.update_status(TaskStatus.PENDING)
    t6.update_status(TaskStatus.PENDING)

    blocked = graph.get_blocked_tasks()
    print(f"\n   Blocked tasks: {[t.id for t in blocked]}")
    print(f"   (expect: ['T-002', 'T-003', 'T-004', 'T-005', 'T-006'])")


async def run_all_tests():
    """Run all test scenarios"""
    print("=" * 80)
    print("MONAD PHASE 2 COMPREHENSIVE TESTING")
    print("=" * 80)
    print()

    try:
        # Test 1: CREATE_NEW
        await test_scenario_1_create_new()

        # Test 2: MODIFY_EXISTING
        # await test_scenario_2_modify_existing()

        # Test 3: File I/O
        await test_scenario_3_file_io_and_backups()

        # Test 4: Dependencies
        await test_scenario_4_task_dependencies()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())

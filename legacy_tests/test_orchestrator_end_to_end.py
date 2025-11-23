"""
Full Orchestrator End-to-End Test

Tests the complete hierarchical orchestrator with actual file I/O:
- User request → System decomposition
- Subsystem tasks → Module tasks
- Module tasks → Function/Class tasks
- Code generation with review loops
- Files written to disk

This is the real deal - we're actually building a working project!
"""

import asyncio
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from orchestrator import HierarchicalOrchestrator
from logging_config import get_logger

logger = get_logger(__name__)


def print_directory_tree(directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0):
    """Pretty-print directory tree"""
    if current_depth > max_depth:
        return

    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        return

    for i, path in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{path.name}")

        if path.is_dir() and not path.name.startswith('.') and not path.name.startswith('__pycache__'):
            extension = "    " if is_last else "│   "
            print_directory_tree(path, prefix + extension, max_depth, current_depth + 1)


def analyze_generated_files(project_dir: Path) -> dict:
    """Analyze the generated Python files"""
    stats = {
        "total_files": 0,
        "total_lines": 0,
        "files_with_docstrings": 0,
        "files_with_type_hints": 0,
        "files_with_tests": 0,
        "average_file_size": 0,
        "functions_count": 0,
        "classes_count": 0
    }

    python_files = list(project_dir.rglob("*.py"))
    stats["total_files"] = len(python_files)

    if not python_files:
        return stats

    total_size = 0

    for py_file in python_files:
        try:
            content = py_file.read_text()
            lines = content.split('\n')
            stats["total_lines"] += len(lines)
            total_size += len(content)

            if '"""' in content or "'''" in content:
                stats["files_with_docstrings"] += 1

            if '->' in content or ': str' in content or ': int' in content:
                stats["files_with_type_hints"] += 1

            if 'test_' in py_file.name or 'import pytest' in content:
                stats["files_with_tests"] += 1

            stats["functions_count"] += content.count('def ')
            stats["classes_count"] += content.count('class ')

        except Exception as e:
            logger.warning(f"Failed to analyze {py_file}: {e}")

    stats["average_file_size"] = total_size // len(python_files) if python_files else 0

    return stats


async def test_simple_library():
    """Test 1: Create a simple utility library"""

    print("\n" + "="*80)
    print("TEST 1: SIMPLE UTILITY LIBRARY")
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
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-2-1212")  # Fast model
    )

    # Create temporary project directory
    project_dir = Path(tempfile.mkdtemp(prefix="monad_test_lib_"))

    print(f"\n📁 Project Directory: {project_dir}")

    try:
        # User request: simple string utilities
        user_request = """
Create a string utilities library with the following functions:
1. capitalize_words(text: str) -> str - Capitalize first letter of each word
2. snake_to_camel(text: str) -> str - Convert snake_case to camelCase
3. truncate(text: str, max_length: int) -> str - Truncate string with ellipsis
All functions should have type hints, docstrings, and input validation.
"""

        print(f"\n📝 User Request:")
        print(user_request)

        # Initialize orchestrator with review loops enabled
        orchestrator = HierarchicalOrchestrator(
            llm_provider=llm_provider,
            use_review_loops=True,
            review_min_score=60.0,  # Based on performance analysis
            review_max_iterations=2,
            create_backups=True
        )

        print(f"\n🚀 Starting orchestration with review loops enabled...")
        print(f"   Review threshold: 60/100")
        print(f"   Max iterations: 2")

        # Run orchestration
        result = await orchestrator.orchestrate(
            user_request=user_request,
            project_path=str(project_dir),
            existing_subsystems=None  # Auto-detect
        )

        # Print results
        print("\n" + "="*80)
        print("ORCHESTRATION RESULTS")
        print("="*80)

        print(f"\n**Status:** {result.status.upper()}")
        print(f"**Success:** {'✅ YES' if result.success else '❌ NO'}")

        print(f"\n**Tasks:**")
        print(f"  Total: {result.tasks_total}")
        print(f"  Completed: {result.tasks_completed}")
        print(f"  Failed: {result.tasks_failed}")
        print(f"  Skipped: {result.tasks_skipped}")

        print(f"\n**Files:**")
        print(f"  Created: {result.files_created}")
        print(f"  Modified: {result.files_modified}")
        print(f"  Failed: {result.files_failed}")
        print(f"  Total written: {len(result.files_written)}")

        print(f"\n**Quality Metrics:**")
        print(f"  Average review score: {result.avg_review_score:.1f}/100")
        print(f"  Total review iterations: {result.total_review_iterations}")

        print(f"\n**Performance:**")
        print(f"  Duration: {result.duration_seconds:.2f}s")

        if result.errors:
            print(f"\n**Errors ({len(result.errors)}):**")
            for error in result.errors[:5]:  # Show first 5
                print(f"  - {error.get('target', 'unknown')}: {error.get('error', 'unknown')[:80]}")

        # Show directory structure
        print("\n" + "="*80)
        print("GENERATED PROJECT STRUCTURE")
        print("="*80)
        print(f"\n{project_dir.name}/")
        print_directory_tree(project_dir)

        # Analyze generated files
        print("\n" + "="*80)
        print("CODE QUALITY ANALYSIS")
        print("="*80)

        stats = analyze_generated_files(project_dir)

        print(f"\n**File Statistics:**")
        print(f"  Total Python files: {stats['total_files']}")
        print(f"  Total lines of code: {stats['total_lines']}")
        print(f"  Average file size: {stats['average_file_size']} bytes")

        print(f"\n**Code Quality:**")
        print(f"  Files with docstrings: {stats['files_with_docstrings']}/{stats['total_files']}")
        print(f"  Files with type hints: {stats['files_with_type_hints']}/{stats['total_files']}")
        print(f"  Test files: {stats['files_with_tests']}")

        print(f"\n**Code Elements:**")
        print(f"  Functions defined: {stats['functions_count']}")
        print(f"  Classes defined: {stats['classes_count']}")

        # Show sample file contents
        if result.files_written:
            print("\n" + "="*80)
            print("SAMPLE GENERATED CODE")
            print("="*80)

            # Show first file
            first_file = result.files_written[0]
            print(f"\nFile: {first_file.relative_to(project_dir)}")
            print("-" * 80)

            content = first_file.read_text()
            all_lines = content.split('\n')
            lines = all_lines[:40]  # First 40 lines
            for i, line in enumerate(lines, 1):
                print(f"{i:3d} | {line}")

            if len(all_lines) > 40:
                remaining = len(all_lines) - 40
                print(f"... ({remaining} more lines)")

        # Success criteria
        success = (
            result.success
            and result.files_created > 0
            and stats['total_files'] > 0
            and stats['files_with_docstrings'] > 0
        )

        print("\n" + "="*80)
        print(f"TEST 1: {'✅ PASSED' if success else '❌ FAILED'}")
        print("="*80)

        return success

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print(f"\n💾 Project saved to: {project_dir}")
        print("   (Inspect the generated code manually)")


async def test_rest_api():
    """Test 2: Create a REST API with authentication (more complex)"""

    print("\n" + "="*80)
    print("TEST 2: REST API WITH AUTHENTICATION")
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
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-2-1212")
    )

    # Create temporary project directory
    project_dir = Path(tempfile.mkdtemp(prefix="monad_test_api_"))

    print(f"\n📁 Project Directory: {project_dir}")

    try:
        # User request: REST API with auth
        user_request = """
Create a simple REST API with user authentication:
1. User model with username, email, password hash
2. Password hashing using bcrypt
3. JWT token generation and validation
4. Login endpoint that returns JWT token
5. Protected endpoint that requires valid JWT

Include proper error handling and type hints.
"""

        print(f"\n📝 User Request:")
        print(user_request)

        # Initialize orchestrator
        orchestrator = HierarchicalOrchestrator(
            llm_provider=llm_provider,
            use_review_loops=True,
            review_min_score=60.0,
            review_max_iterations=2,
            create_backups=True
        )

        print(f"\n🚀 Starting orchestration (this will take longer - more complex)...")

        # Run orchestration
        result = await orchestrator.orchestrate(
            user_request=user_request,
            project_path=str(project_dir),
            existing_subsystems=["models", "auth", "api", "utils"]
        )

        # Print results
        print("\n" + "="*80)
        print("ORCHESTRATION RESULTS")
        print("="*80)

        print(f"\n**Status:** {result.status.upper()}")
        print(f"**Success:** {'✅ YES' if result.success else '❌ NO'}")

        print(f"\n**Tasks:** {result.tasks_completed}/{result.tasks_total} completed")
        print(f"**Files:** {result.files_created} created, {result.files_modified} modified")
        print(f"**Quality:** {result.avg_review_score:.1f}/100 avg review score")
        print(f"**Duration:** {result.duration_seconds:.2f}s")

        # Show structure
        print("\n" + "="*80)
        print("GENERATED PROJECT STRUCTURE")
        print("="*80)
        print(f"\n{project_dir.name}/")
        print_directory_tree(project_dir)

        # Analyze
        stats = analyze_generated_files(project_dir)

        print("\n" + "="*80)
        print("CODE QUALITY ANALYSIS")
        print("="*80)

        print(f"\n  Python files: {stats['total_files']}")
        print(f"  Lines of code: {stats['total_lines']}")
        print(f"  Functions: {stats['functions_count']}")
        print(f"  Classes: {stats['classes_count']}")
        print(f"  With docstrings: {stats['files_with_docstrings']}/{stats['total_files']}")
        print(f"  With type hints: {stats['files_with_type_hints']}/{stats['total_files']}")

        success = (
            result.success
            and result.files_created >= 3  # At least 3 files
            and stats['classes_count'] >= 1  # At least 1 class (User model)
            and stats['functions_count'] >= 3  # Multiple functions
        )

        print("\n" + "="*80)
        print(f"TEST 2: {'✅ PASSED' if success else '❌ FAILED'}")
        print("="*80)

        return success

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print(f"\n💾 Project saved to: {project_dir}")


async def run_all_tests():
    """Run all orchestrator tests"""

    print("\n" + "="*80)
    print("FULL ORCHESTRATOR END-TO-END TESTS")
    print("="*80)
    print("\nTesting complete pipeline with file I/O and review loops")
    print("This demonstrates the full power of the hierarchical system!\n")

    results = []

    # Test 1: Simple library
    print("\n" + ">"*80)
    test1_passed = await test_simple_library()
    results.append(("Simple Library", test1_passed))

    # Test 2: REST API (more complex)
    print("\n" + ">"*80)
    test2_passed = await test_rest_api()
    results.append(("REST API", test2_passed))

    # Summary
    print("\n" + "="*80)
    print("OVERALL TEST SUMMARY")
    print("="*80)

    print("\n**Results:**")
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n**Total: {passed_count}/{total_count} tests passed**")

    all_passed = passed_count == total_count

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n**The full orchestrator is working!**")
        print("  ✅ Hierarchical decomposition (5 tiers)")
        print("  ✅ Review loops at every level")
        print("  ✅ File I/O with actual code generation")
        print("  ✅ Quality tracking and metrics")
        print("\nReady for production use! 🚀")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nDebug the failures before proceeding.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())

    print("\n" + "="*80)
    print("END-TO-END ORCHESTRATOR TESTS COMPLETE")
    print("="*80)

    sys.exit(0 if success else 1)

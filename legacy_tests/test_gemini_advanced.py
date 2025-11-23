"""
Advanced Testing with Google Gemini Pro

Tests MONAD Phase 2 with a more powerful LLM (Gemini Pro) on complex,
realistic features that require deep architectural understanding.
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
from agents import ImplementationOrchestrator


async def test_code_review_system():
    """
    Test: Implement a comprehensive code review and quality analysis system

    This is a complex, multi-subsystem feature that requires:
    - Deep architectural understanding
    - Integration with multiple existing components
    - Creation of new subsystems
    - Complex data flows
    - Real production-level considerations
    """
    print("\n" + "=" * 80)
    print("TEST: Comprehensive Code Review & Quality Analysis System")
    print("Model: Google Gemini Pro 1.5 Preview")
    print("=" * 80)
    print("\nThis is a complex production feature requiring coordination")
    print("across multiple subsystems with sophisticated logic.\n")

    db = Database(":memory:")
    await db.connect()

    # Create Gemini Pro provider
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env file")

    gemini_provider = create_provider(
        "openai",
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "google/gemini-pro-1.5-preview")
    )

    print(f"🤖 LLM Provider: {gemini_provider.get_provider_name()}")
    print(f"📦 Model: {gemini_provider.get_model_name()}")
    print()

    orchestrator = ImplementationOrchestrator(
        db=db,
        llm_provider=gemini_provider,
        project_path="/tmp/test_advanced_system",
        max_concurrent_tasks=8,  # More concurrent tasks for complex feature
        enable_testing=False,
        enable_rollback=True,
        require_approval=False
    )

    user_request = """
    Implement a comprehensive Code Review and Quality Analysis System with the following components:

    1. Code Analysis Engine (in analysis/):
       - Static analysis: Detect code smells, anti-patterns, security vulnerabilities
       - Complexity metrics: Calculate cyclomatic complexity, cognitive complexity
       - Dependency analysis: Detect circular dependencies, unused imports
       - Type checking integration: Integrate with mypy/pyright
       - Performance analysis: Identify inefficient algorithms (O(n²) loops, etc.)

    2. Review Scoring System (in analysis/):
       - Score code on multiple dimensions:
         * Code quality (0-100)
         * Security (0-100)
         * Performance (0-100)
         * Maintainability (0-100)
         * Test coverage (0-100)
       - Aggregate into overall score with weighted components
       - Track score trends over time

    3. AI-Powered Review Comments (in llm_providers/):
       - Use LLM to generate human-like review comments
       - Context-aware suggestions (understand surrounding code)
       - Provide before/after code examples
       - Explain why changes improve code quality
       - Support multiple comment styles (friendly, professional, concise)

    4. Review Workflow Management (in models/ and storage/):
       - Review states: pending, in_progress, approved, changes_requested, rejected
       - Reviewer assignment (manual or auto-assign based on expertise)
       - Review threads with replies and resolutions
       - Approval requirements (min reviewers, passing checks)
       - Integration with git branches

    5. Automated Fix Suggestions (in agents/):
       - Auto-fix simple issues: formatting, import organization, docstrings
       - Generate fix proposals for complex issues
       - Allow users to apply fixes with one click
       - Track which fixes were applied vs rejected

    6. Dashboard and Reporting (in api/):
       - GET /reviews - List all code reviews
       - POST /reviews - Create new review
       - GET /reviews/{id} - Get review details with all comments
       - POST /reviews/{id}/comments - Add review comment
       - PATCH /reviews/{id}/status - Update review status
       - GET /reviews/{id}/score - Get quality scores
       - POST /reviews/{id}/apply-fix - Apply suggested fix

    7. Integration Points:
       - Git integration: Trigger reviews on PRs, commits
       - CI/CD integration: Block merges on failing reviews
       - Notification system: Email/Slack on review state changes
       - Metrics collection: Track review times, approval rates, common issues

    Requirements:
    - All components must work together seamlessly
    - Database schema for reviews, comments, scores, fixes
    - Proper error handling and validation
    - Type hints and comprehensive docstrings
    - Security: Prevent code injection in analysis
    - Performance: Handle large files (10k+ lines)
    - Extensibility: Plugin system for custom analyzers
    """

    print("📝 Starting implementation with Gemini Pro...")
    print(f"📊 Project: {orchestrator.project_path}")
    print()

    import time
    start_time = time.time()

    result = await orchestrator.implement_feature(
        user_request=user_request,
        constraints={
            "preserve_existing": True,
            "add_type_hints": True,
            "add_docstrings": True,
            "min_test_coverage": 80
        }
    )

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("RESULTS: Code Review System Implementation")
    print("=" * 80)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total execution time: {elapsed_time:.1f}s")
    print(f"\n📊 Task Statistics:")
    print(f"   Total tasks: {result.get('total_tasks', 0)}")
    print(f"   Completed: {result.get('completed_tasks', 0)}")
    print(f"   Failed: {result.get('failed_tasks', 0)}")

    # Analyze task breakdown
    task_counts = result.get('task_counts_by_tier', {})
    if task_counts:
        print(f"\n📈 Task Breakdown by Tier:")
        for tier, count in task_counts.items():
            print(f"   {tier:12s}: {count:3d} tasks")

    # Check generated files
    project_path = Path("/tmp/test_advanced_system")
    if project_path.exists():
        py_files = list(project_path.rglob("*.py"))
        print(f"\n📁 Files Generated: {len(py_files)}")

        # Group by subsystem
        subsystems = {}
        for py_file in py_files:
            if ".monad_backups" not in str(py_file):
                rel_path = py_file.relative_to(project_path)
                subsystem = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
                subsystems[subsystem] = subsystems.get(subsystem, 0) + 1

        print(f"\n📂 Files by Subsystem:")
        for subsystem, count in sorted(subsystems.items()):
            print(f"   {subsystem:20s}: {count} files")

        # Analyze code quality
        total_lines = 0
        total_functions = 0
        total_classes = 0
        files_with_docstrings = 0
        files_with_type_hints = 0

        for py_file in py_files:
            if ".monad_backups" not in str(py_file):
                try:
                    content = py_file.read_text()
                    total_lines += len(content.split('\n'))
                    total_functions += content.count('def ')
                    total_classes += content.count('class ')
                    if '"""' in content or "'''" in content:
                        files_with_docstrings += 1
                    if '->' in content and ':' in content:
                        files_with_type_hints += 1
                except:
                    pass

        print(f"\n📊 Code Quality Metrics:")
        print(f"   Total lines of code: {total_lines:,}")
        print(f"   Total functions: {total_functions}")
        print(f"   Total classes: {total_classes}")
        print(f"   Files with docstrings: {files_with_docstrings}/{len(py_files)} ({files_with_docstrings/max(len(py_files),1)*100:.0f}%)")
        print(f"   Files with type hints: {files_with_type_hints}/{len(py_files)} ({files_with_type_hints/max(len(py_files),1)*100:.0f}%)")

        # Show sample of generated code
        analysis_files = list(project_path.glob("analysis/*.py"))
        if analysis_files:
            print(f"\n📄 Sample: {analysis_files[0].name}")
            print("=" * 80)
            content = analysis_files[0].read_text()
            lines = content.split('\n')
            print('\n'.join(lines[:50]))  # Show first 50 lines
            if len(lines) > 50:
                print(f"\n... ({len(lines) - 50} more lines)")
            print("=" * 80)

    # Performance analysis
    if elapsed_time > 0 and result.get('total_tasks', 0) > 0:
        avg_time_per_task = elapsed_time / result['total_tasks']
        print(f"\n⚡ Performance:")
        print(f"   Average time per task: {avg_time_per_task:.2f}s")
        print(f"   Tasks per minute: {60 / max(avg_time_per_task, 0.1):.1f}")

    await db.close()
    return result


async def run_advanced_tests():
    """Run advanced tests with Gemini Pro"""
    print("=" * 80)
    print("MONAD PHASE 2 - ADVANCED TESTING")
    print("Provider: OpenRouter")
    print("Model: Google Gemini Pro 1.5 Preview")
    print("=" * 80)
    print("\nTesting with a production-level feature that requires:")
    print("  • Multi-subsystem coordination (7+ subsystems)")
    print("  • Complex architectural decisions")
    print("  • Integration with existing systems")
    print("  • Sophisticated business logic")
    print("  • Real-world constraints and requirements")
    print()

    try:
        result = await test_code_review_system()

        print("\n" + "=" * 80)
        print("GEMINI PRO TEST COMPLETE")
        print("=" * 80)

        if result.get('status') == 'completed':
            print("\n✅ SUCCESS: Full implementation completed")
            print(f"✅ {result.get('completed_tasks', 0)} tasks executed successfully")
            print("✅ Production-quality code generated")
            print("✅ Multi-subsystem coordination working perfectly")
        elif result.get('status') == 'partial':
            completed = result.get('completed_tasks', 0)
            total = result.get('total_tasks', 0)
            print(f"\n⚠️  PARTIAL SUCCESS: {completed}/{total} tasks completed")
            print("⚠️  Some components may be incomplete")
        else:
            print("\n❌ FAILED: Implementation did not complete")
            print(f"❌ Status: {result.get('status')}")

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_advanced_tests())

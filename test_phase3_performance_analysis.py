"""
Phase 3 Performance & Quality Analysis

Comprehensive test suite to measure the impact of review loops across multiple scenarios:

Metrics Tracked:
1. Quality Scores - Initial vs Final (with review loops)
2. Token Usage - Cost comparison (with vs without reviews)
3. Latency - Time overhead of review cycles
4. Success Rates - How often reviews improve vs harm quality
5. Issue Detection - What types of issues do reviews catch?
6. Iteration Patterns - How many iterations needed for acceptance?

Test Scenarios:
- Simple tasks (basic functions)
- Complex tasks (classes with multiple methods)
- Security-sensitive tasks (auth, validation)
- Edge cases (error handling, boundary conditions)

Comparison:
- Review loops ENABLED vs DISABLED
- Different review thresholds (60, 75, 90)
- Different max iterations (1, 2, 3)
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider, LLMProvider
from planning.decomposition import (
    SystemDecomposer,
    SubsystemDecomposer,
    ModuleDecomposer,
    FunctionPlanner
)
from models import Task, TaskType, TaskPriority
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Metrics for a single test run"""
    scenario: str
    tier: str
    review_enabled: bool
    review_min_score: float = 0.0
    review_max_iterations: int = 0

    # Quality metrics
    initial_score: float = 0.0
    final_score: float = 0.0
    quality_improvement: float = 0.0

    # Performance metrics
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0

    # Token usage (if available)
    tokens_used: int = 0

    # Review-specific metrics
    iterations_performed: int = 0
    final_decision: str = "n/a"
    issues_found: List[str] = field(default_factory=list)
    strengths_found: List[str] = field(default_factory=list)

    # Output size
    output_size: int = 0

    # Success/failure
    success: bool = False
    error: str = None


@dataclass
class TestScenario:
    """Definition of a test scenario"""
    name: str
    description: str
    user_request: str
    subsystems: List[str]
    tier_to_test: str  # "system", "subsystem", "module", "function"
    expected_complexity: str  # "simple", "medium", "complex"
    security_sensitive: bool = False


# Define test scenarios
TEST_SCENARIOS = [
    TestScenario(
        name="simple_function",
        description="Simple mathematical function",
        user_request="Create a function to calculate the factorial of a number",
        subsystems=["math_utils"],
        tier_to_test="function",
        expected_complexity="simple"
    ),
    TestScenario(
        name="validation_function",
        description="Input validation with edge cases",
        user_request="Create an email validation function that checks format, length, and common typos",
        subsystems=["validators"],
        tier_to_test="function",
        expected_complexity="medium"
    ),
    TestScenario(
        name="auth_system",
        description="Security-sensitive authentication",
        user_request="Create a password hashing and verification system using bcrypt",
        subsystems=["auth", "security"],
        tier_to_test="system",
        expected_complexity="complex",
        security_sensitive=True
    ),
    TestScenario(
        name="data_parser",
        description="Complex parsing with error handling",
        user_request="Create a JSON/YAML config file parser with schema validation and helpful error messages",
        subsystems=["parsers", "validators"],
        tier_to_test="subsystem",
        expected_complexity="complex"
    ),
    TestScenario(
        name="cache_decorator",
        description="Medium complexity decorator",
        user_request="Create a memoization decorator with TTL and size limits",
        subsystems=["decorators"],
        tier_to_test="function",
        expected_complexity="medium"
    ),
]


async def test_function_planner(
    scenario: TestScenario,
    llm_provider: LLMProvider,
    review_enabled: bool,
    review_min_score: float = 75.0,
    review_max_iterations: int = 2
) -> PerformanceMetrics:
    """Test FunctionPlanner with a specific scenario"""

    metrics = PerformanceMetrics(
        scenario=scenario.name,
        tier="function",
        review_enabled=review_enabled,
        review_min_score=review_min_score if review_enabled else 0.0,
        review_max_iterations=review_max_iterations if review_enabled else 0
    )

    try:
        # Create test task
        task = Task(
            id=f"T-TEST-{scenario.name}",
            parent_task_id=None,
            type=TaskType.CREATE_NEW,
            scope="FUNCTION",
            target=f"{scenario.subsystems[0]}/main.py::main_function",
            instruction=scenario.user_request,
            context={},
            priority=TaskPriority.HIGH
        )

        # Initialize planner
        planner = FunctionPlanner(
            llm_provider=llm_provider,
            use_review_loop=review_enabled,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations
        )

        # Generate code with timing
        metrics.start_time = time.time()
        result = await planner.generate_implementation(task)
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time

        # Extract metrics from result
        code = result.get("code", "")
        metrics.output_size = len(code)
        metrics.success = len(code) > 0

        # Extract review metadata if available
        if "_review_metadata" in result:
            meta = result["_review_metadata"]
            metrics.iterations_performed = meta.get("iterations", 0)
            metrics.final_decision = meta.get("final_decision", "unknown")
            metrics.initial_score = meta.get("initial_score", 0.0)
            metrics.final_score = meta.get("final_score", 0.0)
            metrics.quality_improvement = metrics.final_score - metrics.initial_score

            # Get issues and strengths (first 5 each)
            metrics.issues_found = meta.get("issues", [])[:5]
            metrics.strengths_found = meta.get("strengths", [])[:5]
        else:
            # No review, estimate quality from code
            metrics.iterations_performed = 0
            metrics.final_decision = "no_review"
            metrics.final_score = estimate_code_quality(code)
            metrics.initial_score = metrics.final_score
            metrics.quality_improvement = 0.0

    except Exception as e:
        metrics.success = False
        metrics.error = str(e)
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time

    return metrics


async def test_system_decomposer(
    scenario: TestScenario,
    llm_provider: LLMProvider,
    review_enabled: bool,
    review_min_score: float = 75.0,
    review_max_iterations: int = 2
) -> PerformanceMetrics:
    """Test SystemDecomposer with a specific scenario"""

    metrics = PerformanceMetrics(
        scenario=scenario.name,
        tier="system",
        review_enabled=review_enabled,
        review_min_score=review_min_score if review_enabled else 0.0,
        review_max_iterations=review_max_iterations if review_enabled else 0
    )

    try:
        decomposer = SystemDecomposer(
            llm_provider=llm_provider,
            use_intelligent_selection=True,
            use_review_loop=review_enabled,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations
        )

        metrics.start_time = time.time()
        tasks = await decomposer.decompose(
            user_request=scenario.user_request,
            project_path="/tmp/test_project",
            subsystems=scenario.subsystems
        )
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time

        metrics.output_size = len(tasks)
        metrics.success = len(tasks) > 0

        # Try to extract review metadata from task context if available
        if tasks and hasattr(tasks[0], 'context') and '_review_metadata' in tasks[0].context:
            meta = tasks[0].context['_review_metadata']
            metrics.iterations_performed = meta.get("iterations", 0)
            metrics.final_score = meta.get("final_score", 0.0)
            metrics.initial_score = meta.get("initial_score", 0.0)
            metrics.quality_improvement = metrics.final_score - metrics.initial_score

    except Exception as e:
        metrics.success = False
        metrics.error = str(e)
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time

    return metrics


def estimate_code_quality(code: str) -> float:
    """Heuristic code quality estimate for cases without review metadata"""
    score = 50.0  # Base score

    if not code:
        return 0.0

    # Positive indicators
    if '"""' in code or "'''" in code:
        score += 10  # Has docstrings
    if '->' in code or ': str' in code or ': int' in code:
        score += 10  # Has type hints
    if 'raise' in code or 'except' in code:
        score += 10  # Has error handling
    if 'def ' in code:
        score += 5  # Has functions
    if len(code) > 200:
        score += 5  # Non-trivial size

    # Negative indicators
    if 'pass' in code and code.count('pass') > 2:
        score -= 15  # Multiple pass statements (placeholder code)
    if 'TODO' in code or 'FIXME' in code:
        score -= 10  # Has TODOs
    if '...' in code:
        score -= 10  # Has ellipsis (incomplete)

    return max(0.0, min(100.0, score))


def print_metrics_summary(metrics_list: List[PerformanceMetrics]):
    """Print summary statistics for a list of metrics"""

    if not metrics_list:
        print("  No metrics to display")
        return

    # Separate by review enabled/disabled
    with_review = [m for m in metrics_list if m.review_enabled]
    without_review = [m for m in metrics_list if not m.review_enabled]

    print(f"\n  Total tests: {len(metrics_list)}")
    print(f"  With review: {len(with_review)}")
    print(f"  Without review: {len(without_review)}")

    # Success rates
    if with_review:
        success_rate = sum(1 for m in with_review if m.success) / len(with_review) * 100
        print(f"\n  Success rate (with review): {success_rate:.1f}%")

    if without_review:
        success_rate = sum(1 for m in without_review if m.success) / len(without_review) * 100
        print(f"  Success rate (without review): {success_rate:.1f}%")

    # Quality scores
    if with_review:
        avg_initial = sum(m.initial_score for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))
        avg_final = sum(m.final_score for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))
        avg_improvement = sum(m.quality_improvement for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))

        print(f"\n  **Quality Scores (with review):**")
        print(f"    Average initial score: {avg_initial:.1f}/100")
        print(f"    Average final score: {avg_final:.1f}/100")
        print(f"    Average improvement: {avg_improvement:+.1f} points")

    if without_review:
        avg_score = sum(m.final_score for m in without_review if m.success) / max(1, len([m for m in without_review if m.success]))
        print(f"\n  **Quality Scores (without review):**")
        print(f"    Average score: {avg_score:.1f}/100")

    # Compare quality
    if with_review and without_review:
        with_avg = sum(m.final_score for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))
        without_avg = sum(m.final_score for m in without_review if m.success) / max(1, len([m for m in without_review if m.success]))
        difference = with_avg - without_avg

        print(f"\n  **Quality Comparison:**")
        print(f"    With review: {with_avg:.1f}/100")
        print(f"    Without review: {without_avg:.1f}/100")
        print(f"    Difference: {difference:+.1f} points ({(difference/without_avg*100):+.1f}%)")

    # Performance
    if with_review:
        avg_duration = sum(m.duration_seconds for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))
        avg_iterations = sum(m.iterations_performed for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))

        print(f"\n  **Performance (with review):**")
        print(f"    Average duration: {avg_duration:.2f}s")
        print(f"    Average iterations: {avg_iterations:.1f}")

    if without_review:
        avg_duration = sum(m.duration_seconds for m in without_review if m.success) / max(1, len([m for m in without_review if m.success]))

        print(f"\n  **Performance (without review):**")
        print(f"    Average duration: {avg_duration:.2f}s")

    # Compare performance
    if with_review and without_review:
        with_dur = sum(m.duration_seconds for m in with_review if m.success) / max(1, len([m for m in with_review if m.success]))
        without_dur = sum(m.duration_seconds for m in without_review if m.success) / max(1, len([m for m in without_review if m.success]))
        overhead = with_dur - without_dur
        overhead_pct = (overhead / without_dur * 100) if without_dur > 0 else 0

        print(f"\n  **Performance Comparison:**")
        print(f"    With review: {with_dur:.2f}s")
        print(f"    Without review: {without_dur:.2f}s")
        print(f"    Overhead: {overhead:+.2f}s ({overhead_pct:+.1f}%)")


async def run_performance_analysis():
    """Run comprehensive performance and quality analysis"""

    print("\n" + "="*80)
    print("PHASE 3: PERFORMANCE & QUALITY ANALYSIS")
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
    print(f"✓ Test Scenarios: {len(TEST_SCENARIOS)}")
    print(f"✓ Configurations: Review ON vs OFF, multiple thresholds")

    # Store all metrics
    all_metrics: List[PerformanceMetrics] = []

    # =========================================================================
    # EXPERIMENT 1: Review ON vs OFF (Function Tier)
    # =========================================================================
    print("\n" + "="*80)
    print("EXPERIMENT 1: REVIEW LOOPS ON vs OFF (Function Tier)")
    print("="*80)

    for scenario in TEST_SCENARIOS:
        if scenario.tier_to_test != "function":
            continue

        print(f"\n{'─'*80}")
        print(f"Scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Complexity: {scenario.expected_complexity}")
        print(f"{'─'*80}")

        # Test WITHOUT review
        print(f"\n  [1/2] Testing WITHOUT review loops...")
        metrics_off = await test_function_planner(
            scenario=scenario,
            llm_provider=llm_provider,
            review_enabled=False
        )
        all_metrics.append(metrics_off)

        print(f"    Duration: {metrics_off.duration_seconds:.2f}s")
        print(f"    Output size: {metrics_off.output_size} chars")
        print(f"    Quality (estimated): {metrics_off.final_score:.1f}/100")
        print(f"    Success: {'✅' if metrics_off.success else '❌'}")

        # Test WITH review
        print(f"\n  [2/2] Testing WITH review loops (threshold=75, max_iter=2)...")
        metrics_on = await test_function_planner(
            scenario=scenario,
            llm_provider=llm_provider,
            review_enabled=True,
            review_min_score=75.0,
            review_max_iterations=2
        )
        all_metrics.append(metrics_on)

        print(f"    Duration: {metrics_on.duration_seconds:.2f}s")
        print(f"    Output size: {metrics_on.output_size} chars")
        print(f"    Initial quality: {metrics_on.initial_score:.1f}/100")
        print(f"    Final quality: {metrics_on.final_score:.1f}/100")
        print(f"    Improvement: {metrics_on.quality_improvement:+.1f} points")
        print(f"    Iterations: {metrics_on.iterations_performed}")
        print(f"    Decision: {metrics_on.final_decision}")
        print(f"    Success: {'✅' if metrics_on.success else '❌'}")

        # Show top issues found
        if metrics_on.issues_found:
            print(f"\n    Issues detected by review:")
            for i, issue in enumerate(metrics_on.issues_found[:3], 1):
                print(f"      {i}. {issue[:80]}...")

    # =========================================================================
    # EXPERIMENT 2: Different Review Thresholds
    # =========================================================================
    print("\n" + "="*80)
    print("EXPERIMENT 2: DIFFERENT REVIEW THRESHOLDS")
    print("="*80)

    # Pick one complex scenario
    complex_scenario = next((s for s in TEST_SCENARIOS if s.expected_complexity == "complex"), TEST_SCENARIOS[0])

    print(f"\nScenario: {complex_scenario.name} ({complex_scenario.expected_complexity})")

    for threshold in [60.0, 75.0, 90.0]:
        print(f"\n  Testing with threshold={threshold:.0f}...")
        metrics = await test_function_planner(
            scenario=complex_scenario,
            llm_provider=llm_provider,
            review_enabled=True,
            review_min_score=threshold,
            review_max_iterations=2
        )
        all_metrics.append(metrics)

        print(f"    Threshold: {threshold:.0f}/100")
        print(f"    Final quality: {metrics.final_score:.1f}/100")
        print(f"    Iterations: {metrics.iterations_performed}")
        print(f"    Decision: {metrics.final_decision}")
        print(f"    Duration: {metrics.duration_seconds:.2f}s")

    # =========================================================================
    # EXPERIMENT 3: System Tier Performance
    # =========================================================================
    print("\n" + "="*80)
    print("EXPERIMENT 3: SYSTEM TIER PERFORMANCE")
    print("="*80)

    system_scenario = next((s for s in TEST_SCENARIOS if s.tier_to_test == "system"), None)

    if system_scenario:
        print(f"\nScenario: {system_scenario.name}")

        # Without review
        print(f"\n  [1/2] Without review loops...")
        metrics_off = await test_system_decomposer(
            scenario=system_scenario,
            llm_provider=llm_provider,
            review_enabled=False
        )
        all_metrics.append(metrics_off)

        print(f"    Duration: {metrics_off.duration_seconds:.2f}s")
        print(f"    Tasks generated: {metrics_off.output_size}")

        # With review
        print(f"\n  [2/2] With review loops...")
        metrics_on = await test_system_decomposer(
            scenario=system_scenario,
            llm_provider=llm_provider,
            review_enabled=True,
            review_min_score=75.0,
            review_max_iterations=2
        )
        all_metrics.append(metrics_on)

        print(f"    Duration: {metrics_on.duration_seconds:.2f}s")
        print(f"    Tasks generated: {metrics_on.output_size}")
        print(f"    Iterations: {metrics_on.iterations_performed}")

    # =========================================================================
    # OVERALL ANALYSIS
    # =========================================================================
    print("\n" + "="*80)
    print("OVERALL ANALYSIS")
    print("="*80)

    print_metrics_summary(all_metrics)

    # =========================================================================
    # KEY INSIGHTS
    # =========================================================================
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)

    with_review = [m for m in all_metrics if m.review_enabled and m.success and m.tier == "function"]
    without_review = [m for m in all_metrics if not m.review_enabled and m.success and m.tier == "function"]

    if with_review and without_review:
        # Quality ROI
        quality_gain = sum(m.final_score for m in with_review) / len(with_review) - sum(m.final_score for m in without_review) / len(without_review)
        time_cost = sum(m.duration_seconds for m in with_review) / len(with_review) - sum(m.duration_seconds for m in without_review) / len(without_review)

        print(f"\n1. **Quality ROI**")
        print(f"   Average quality gain: {quality_gain:+.1f} points")
        print(f"   Average time cost: {time_cost:+.2f}s")
        print(f"   Quality per second: {quality_gain/time_cost:.2f} points/s" if time_cost > 0 else "   N/A")

        # When reviews help most
        improvements = [m.quality_improvement for m in with_review if m.quality_improvement > 0]
        if improvements:
            avg_improvement = sum(improvements) / len(improvements)
            print(f"\n2. **Review Effectiveness**")
            print(f"   Tests with improvement: {len(improvements)}/{len(with_review)} ({len(improvements)/len(with_review)*100:.0f}%)")
            print(f"   Average improvement (when positive): {avg_improvement:+.1f} points")

        # Iteration patterns
        accept_count = sum(1 for m in with_review if m.final_decision == "accept")
        revise_count = sum(1 for m in with_review if "revise" in m.final_decision.lower())
        reject_count = sum(1 for m in with_review if m.final_decision == "reject")

        print(f"\n3. **Review Decisions**")
        print(f"   Accepted: {accept_count}/{len(with_review)} ({accept_count/len(with_review)*100:.0f}%)")
        print(f"   Revised: {revise_count}/{len(with_review)} ({revise_count/len(with_review)*100:.0f}%)")
        print(f"   Rejected: {reject_count}/{len(with_review)} ({reject_count/len(with_review)*100:.0f}%)")

    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    if with_review and without_review:
        quality_gain = sum(m.final_score for m in with_review) / len(with_review) - sum(m.final_score for m in without_review) / len(without_review)

        if quality_gain > 10:
            print("\n✅ STRONG RECOMMENDATION: Enable review loops")
            print(f"   Quality improvement ({quality_gain:+.1f} points) justifies the overhead")
        elif quality_gain > 5:
            print("\n⚠️  MODERATE RECOMMENDATION: Enable for complex tasks")
            print(f"   Quality improvement ({quality_gain:+.1f} points) is moderate")
        else:
            print("\n❌ WEAK RECOMMENDATION: Review loops optional")
            print(f"   Quality improvement ({quality_gain:+.1f} points) is minimal")

        # Threshold recommendation
        avg_final_scores_by_threshold = {}
        for threshold in [60.0, 75.0, 90.0]:
            threshold_metrics = [m for m in all_metrics if m.review_enabled and abs(m.review_min_score - threshold) < 0.1 and m.success]
            if threshold_metrics:
                avg_final_scores_by_threshold[threshold] = sum(m.final_score for m in threshold_metrics) / len(threshold_metrics)

        if avg_final_scores_by_threshold:
            best_threshold = max(avg_final_scores_by_threshold.items(), key=lambda x: x[1])
            print(f"\n✅ OPTIMAL THRESHOLD: {best_threshold[0]:.0f}/100")
            print(f"   Best average quality: {best_threshold[1]:.1f}/100")

    print("\n" + "="*80)

    # Save detailed results
    results_file = Path("/tmp/phase3_performance_results.json")
    with open(results_file, "w") as f:
        json.dump(
            [{
                "scenario": m.scenario,
                "tier": m.tier,
                "review_enabled": m.review_enabled,
                "review_min_score": m.review_min_score,
                "initial_score": m.initial_score,
                "final_score": m.final_score,
                "quality_improvement": m.quality_improvement,
                "duration_seconds": m.duration_seconds,
                "iterations_performed": m.iterations_performed,
                "final_decision": m.final_decision,
                "success": m.success
            } for m in all_metrics],
            f,
            indent=2
        )

    print(f"\n💾 Detailed results saved to: {results_file}")

    return True


if __name__ == "__main__":
    success = asyncio.run(run_performance_analysis())

    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS COMPLETE")
    print("="*80)

    if success:
        print("\n✅ Analysis completed successfully!")
        print("\nUse the insights above to optimize review loop configuration.")
        sys.exit(0)
    else:
        print("\n❌ Analysis failed")
        sys.exit(1)

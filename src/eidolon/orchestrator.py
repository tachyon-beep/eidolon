"""
Full Pipeline Orchestrator - Phase 4

Orchestrates the complete hierarchical decomposition and implementation pipeline:

0. CodeGraphAnalyzer: Parse project and build dependency graphs (Phase 4)
1. SystemDecomposer: User request → Subsystem tasks
2. SubsystemDecomposer: Subsystem tasks → Module tasks
3. ModuleDecomposer: Module tasks → Function/Class tasks
4. FunctionPlanner: Function/Class tasks → Code (with graph context!)
5. File Writer: Code → Disk

Features:
- Phase 4: Code graph analysis provides rich context
- Review loops enabled at all tiers
- Dependency resolution and ordering
- Progress tracking and state management
- File I/O with backup/rollback
- Error handling and recovery
- Comprehensive logging
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
import uuid
import json
from datetime import datetime

from eidolon.models import Task, TaskType, TaskStatus, TaskPriority
from eidolon.llm_providers import LLMProvider
from eidolon.planning.decomposition import (
    SystemDecomposer,
    SubsystemDecomposer,
    ModuleDecomposer,
    ClassDecomposer,
    FunctionPlanner
)
from eidolon.code_graph import CodeGraphAnalyzer, CodeGraph
from eidolon.code_context_tools import CodeContextToolHandler
from eidolon.design_context_tools import DesignContextToolHandler
from eidolon.business_analyst import BusinessAnalyst, RequirementsAnalysis
from eidolon.linting_agent import LintingAgent, LintingResult
from eidolon.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OrchestrationResult:
    """Result of an orchestration run"""
    success: bool
    status: str  # "completed", "partial", "failed"

    # Task statistics
    tasks_total: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0

    # File statistics
    files_created: int = 0
    files_modified: int = 0
    files_failed: int = 0

    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Quality metrics
    avg_review_score: float = 0.0
    total_review_iterations: int = 0

    # Outputs
    project_path: Path = None
    files_written: List[Path] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Task tree for inspection
    task_tree: Dict[str, Any] = field(default_factory=dict)

    # Phase 4: Code graph
    code_graph: Optional[CodeGraph] = None

    # Phase 5: Requirements analysis
    requirements_analysis: Optional[RequirementsAnalysis] = None

    # Phase 6: Linting statistics
    total_lint_issues: int = 0
    lint_issues_fixed: int = 0
    lint_auto_fixed: int = 0
    lint_llm_fixed: int = 0


class HierarchicalOrchestrator:
    """
    Orchestrates the full hierarchical decomposition and implementation pipeline

    This is the main entry point for turning user requests into working code.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        use_review_loops: bool = True,
        review_min_score: float = 60.0,  # Lower threshold based on performance analysis
        review_max_iterations: int = 2,
        max_concurrent_tasks: int = 3,
        create_backups: bool = True,
        use_code_graph: bool = True,  # Phase 4: Enable code graph analysis
        generate_ai_descriptions: bool = False,  # Optional AI descriptions for UX
        use_business_analyst: bool = True,  # Phase 5: Enable requirements analysis
        use_linting: bool = True,  # Phase 6: Enable automatic linting/fixing
        target_python_version: str = "3.12"  # Phase 6: Target Python version
    ):
        """
        Initialize the orchestrator

        Args:
            llm_provider: LLM provider for all decomposers
            use_review_loops: Enable review loops at all tiers
            review_min_score: Minimum quality score for review acceptance
            review_max_iterations: Max revision iterations per task
            max_concurrent_tasks: Max tasks to process in parallel
            create_backups: Create backups before overwriting files
            use_code_graph: Enable code graph analysis for context (Phase 4)
            generate_ai_descriptions: Generate AI descriptions for functions/classes
            use_business_analyst: Enable requirements analysis layer (Phase 5)
            use_linting: Enable automatic linting and fixing (Phase 6)
            target_python_version: Target Python version for linting (Phase 6)
        """
        self.llm_provider = llm_provider
        self.use_review_loops = use_review_loops
        self.review_min_score = review_min_score
        self.review_max_iterations = review_max_iterations
        self.max_concurrent_tasks = max_concurrent_tasks
        self.create_backups = create_backups
        self.use_code_graph = use_code_graph
        self.generate_ai_descriptions = generate_ai_descriptions
        self.use_business_analyst = use_business_analyst
        self.use_linting = use_linting
        self.target_python_version = target_python_version

        # Phase 4: Initialize code graph analyzer and tool handler
        self.code_graph_analyzer = CodeGraphAnalyzer(
            llm_provider=llm_provider if generate_ai_descriptions else None,
            generate_ai_descriptions=generate_ai_descriptions
        ) if use_code_graph else None

        # Phase 4B: Tool handler for interactive context fetching
        # Will be initialized with code_graph after project analysis
        self.tool_handler = None

        # Phase 4C: Design tool handler for interactive design exploration
        # Will be initialized with code_graph after project analysis
        self.design_tool_handler = None

        # Phase 5: Business Analyst for requirements analysis
        # Will be initialized with code_graph and design_tool_handler after project analysis
        self.business_analyst = None

        # Phase 6: Linting Agent for code quality
        self.linting_agent = LintingAgent(
            llm_provider=llm_provider,
            use_ruff=True,
            use_mypy=True,
            use_llm_fixes=True,
            target_python_version=target_python_version
        ) if use_linting else None

        # Initialize all decomposers with review loops
        self.system_decomposer = SystemDecomposer(
            llm_provider=llm_provider,
            use_intelligent_selection=True,
            use_review_loop=use_review_loops,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations,
            design_tool_handler=None  # Will be set after project analysis
        )

        self.subsystem_decomposer = SubsystemDecomposer(
            llm_provider=llm_provider,
            use_intelligent_selection=True,
            use_review_loop=use_review_loops,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations,
            design_tool_handler=None  # Will be set after project analysis
        )

        self.module_decomposer = ModuleDecomposer(
            llm_provider=llm_provider,
            use_intelligent_selection=True,
            use_review_loop=use_review_loops,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations,
            design_tool_handler=None  # Will be set after project analysis
        )

        self.class_decomposer = ClassDecomposer(
            llm_provider=llm_provider,
            use_intelligent_selection=True,
            use_review_loop=use_review_loops,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations
        )

        self.function_planner = FunctionPlanner(
            llm_provider=llm_provider,
            use_review_loop=use_review_loops,
            review_min_score=review_min_score,
            review_max_iterations=review_max_iterations,
            code_graph=None,  # Will be set after project analysis
            tool_handler=None  # Will be set after project analysis
        )

        # State tracking
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.task_outputs: Dict[str, Any] = {}

        logger.info(
            "orchestrator_initialized",
            review_loops=use_review_loops,
            review_threshold=review_min_score,
            max_iterations=review_max_iterations
        )

    async def orchestrate(
        self,
        user_request: str,
        project_path: str,
        existing_subsystems: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResult:
        """
        Run the complete orchestration pipeline

        Args:
            user_request: High-level user request (e.g., "Create a REST API with auth")
            project_path: Path where code should be generated
            existing_subsystems: List of existing subsystems/directories (auto-detected if None)
            context: Additional context

        Returns:
            OrchestrationResult with all statistics and outputs
        """
        result = OrchestrationResult(
            success=False,
            status="starting",
            start_time=datetime.now(),
            project_path=Path(project_path)
        )

        context = context or {}

        try:
            logger.info(
                "orchestration_started",
                user_request=user_request[:100],
                project_path=project_path,
                review_enabled=self.use_review_loops
            )

            # Ensure project directory exists
            project_dir = Path(project_path)
            project_dir.mkdir(parents=True, exist_ok=True)

            # Auto-detect subsystems if not provided
            if existing_subsystems is None:
                existing_subsystems = self._detect_subsystems(project_dir)
                logger.info("subsystems_detected", subsystems=existing_subsystems)

            # ================================================================
            # TIER 0: Code Graph Analysis (Phase 4)
            # ================================================================
            code_graph = None
            if self.use_code_graph and self.code_graph_analyzer:
                logger.info("tier0_starting", tier="code_graph_analysis")
                try:
                    code_graph = await self.code_graph_analyzer.analyze_project(
                        project_path=project_dir,
                        exclude_patterns=["test_*", "*_test.py", ".*", "__pycache__", "venv", "env"]
                    )
                    result.code_graph = code_graph

                    logger.info(
                        "tier0_complete",
                        modules=code_graph.total_modules,
                        functions=code_graph.total_functions,
                        classes=code_graph.total_classes,
                        lines=code_graph.total_lines
                    )

                    # Add code graph to context for all decomposers
                    context["code_graph"] = code_graph

                    # Phase 4B: Initialize tool handler for interactive context fetching
                    self.tool_handler = CodeContextToolHandler(code_graph=code_graph)

                    # Update function planner with code graph and tool handler
                    self.function_planner.code_graph = code_graph
                    self.function_planner.tool_handler = self.tool_handler

                    logger.info("tool_handler_initialized", tools_available=True)

                    # Phase 4C: Initialize design tool handler for interactive design
                    self.design_tool_handler = DesignContextToolHandler(
                        code_graph=code_graph,
                        project_context=self.project_context if hasattr(self, 'project_context') else None,
                        design_constraints=context.get("design_constraints")
                    )

                    # Update all decomposers with design tool handler
                    self.system_decomposer.design_tool_handler = self.design_tool_handler
                    self.subsystem_decomposer.design_tool_handler = self.design_tool_handler
                    self.module_decomposer.design_tool_handler = self.design_tool_handler

                    logger.info("design_tool_handler_initialized", design_tools_available=True)

                    # Phase 5: Initialize Business Analyst for requirements analysis
                    if self.use_business_analyst:
                        self.business_analyst = BusinessAnalyst(
                            llm_provider=self.llm_provider,
                            code_graph=code_graph,
                            design_tool_handler=self.design_tool_handler
                        )
                        logger.info("business_analyst_initialized", ba_available=True)

                except Exception as e:
                    logger.warning("code_graph_analysis_failed", error=str(e))
                    # Continue without code graph - graceful degradation

            # ================================================================
            # TIER 0.5: Business Analysis (Phase 5 - Requirements Refinement)
            # ================================================================
            # Analyze request and create structured requirements/change plan
            # before passing to system decomposer
            requirements_analysis = None
            refined_request = user_request  # Default to original request

            # Check if requirements already provided in context (e.g., from interactive BA)
            if context.get("requirements_analysis"):
                logger.info("tier0.5_skipped", reason="requirements_already_provided")
                requirements_analysis = context["requirements_analysis"]
                refined_request = requirements_analysis.refined_requirements
                result.requirements_analysis = requirements_analysis

                logger.info(
                    "tier0.5_using_provided_analysis",
                    change_type=requirements_analysis.change_type,
                    complexity=requirements_analysis.complexity_estimate,
                    affected_subsystems=len(requirements_analysis.affected_subsystems or []),
                    analysis_turns=requirements_analysis.analysis_turns
                )

            elif self.business_analyst:
                logger.info("tier0.5_starting", tier="business_analysis")
                try:
                    requirements_analysis = await self.business_analyst.analyze_request(
                        user_request=user_request,
                        project_path=project_path,
                        context=context
                    )
                    result.requirements_analysis = requirements_analysis

                    # Use refined requirements for system decomposition
                    refined_request = requirements_analysis.refined_requirements

                    logger.info(
                        "tier0.5_complete",
                        change_type=requirements_analysis.change_type,
                        complexity=requirements_analysis.complexity_estimate,
                        affected_subsystems=len(requirements_analysis.affected_subsystems),
                        analysis_turns=requirements_analysis.analysis_turns
                    )

                    # Add requirements analysis to context for downstream use
                    context["requirements_analysis"] = requirements_analysis

                except Exception as e:
                    logger.warning("business_analysis_failed", error=str(e))
                    # Continue with original request if BA fails

            # ================================================================
            # TIER 1: System Decomposition (User Request → Subsystem Tasks)
            # ================================================================
            logger.info("tier1_starting", tier="system")

            subsystem_tasks = await self.system_decomposer.decompose(
                user_request=refined_request,  # Use refined request from BA
                project_path=project_path,
                subsystems=existing_subsystems or ["src"],
                context=context
            )

            result.tasks_total = len(subsystem_tasks)
            result.task_tree["subsystem_tasks"] = [
                {
                    "id": t.id,
                    "target": t.target,
                    "type": str(t.type.value if hasattr(t.type, 'value') else t.type),
                    "instruction": t.instruction[:100]
                }
                for t in subsystem_tasks
            ]

            logger.info(
                "tier1_complete",
                subsystem_tasks=len(subsystem_tasks),
                targets=[t.target for t in subsystem_tasks]
            )

            # ================================================================
            # TIER 2-4: Process each subsystem task hierarchically
            # ================================================================

            for subsystem_task in subsystem_tasks:
                try:
                    await self._process_subsystem_task(
                        subsystem_task=subsystem_task,
                        project_dir=project_dir,
                        result=result,
                        context=context
                    )
                    result.tasks_completed += 1

                except Exception as e:
                    logger.error(
                        "subsystem_task_failed",
                        task_id=subsystem_task.id,
                        target=subsystem_task.target,
                        error=str(e)
                    )
                    result.tasks_failed += 1
                    result.errors.append({
                        "task_id": subsystem_task.id,
                        "target": subsystem_task.target,
                        "error": str(e),
                        "tier": "subsystem"
                    })

            # ================================================================
            # Finalize result
            # ================================================================

            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()

            if result.tasks_failed == 0:
                result.status = "completed"
                result.success = True
            elif result.tasks_completed > 0:
                result.status = "partial"
                result.success = True
            else:
                result.status = "failed"
                result.success = False

            logger.info(
                "orchestration_complete",
                status=result.status,
                tasks_total=result.tasks_total,
                tasks_completed=result.tasks_completed,
                tasks_failed=result.tasks_failed,
                files_created=result.files_created,
                files_modified=result.files_modified,
                duration_seconds=result.duration_seconds
            )

            return result

        except Exception as e:
            logger.error("orchestration_failed", error=str(e))
            result.status = "failed"
            result.success = False
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            result.errors.append({
                "error": str(e),
                "tier": "orchestrator"
            })
            return result

    async def _process_subsystem_task(
        self,
        subsystem_task: Task,
        project_dir: Path,
        result: OrchestrationResult,
        context: Dict[str, Any]
    ):
        """Process a subsystem task through tiers 2-4"""

        logger.info(
            "tier2_starting",
            tier="subsystem",
            task_id=subsystem_task.id,
            target=subsystem_task.target
        )

        # ================================================================
        # TIER 2: Subsystem → Module Tasks
        # ================================================================

        # Detect existing modules in this subsystem
        subsystem_dir = project_dir / subsystem_task.target
        existing_modules = self._detect_modules(subsystem_dir)

        module_tasks = await self.subsystem_decomposer.decompose(
            task=subsystem_task,
            existing_modules=existing_modules,
            context=context
        )

        logger.info(
            "tier2_complete",
            module_tasks=len(module_tasks),
            targets=[t.target for t in module_tasks]
        )

        # ================================================================
        # TIER 3: Process each module task
        # ================================================================

        for module_task in module_tasks:
            try:
                await self._process_module_task(
                    module_task=module_task,
                    project_dir=project_dir,
                    subsystem_name=subsystem_task.target,
                    result=result,
                    context=context
                )

            except Exception as e:
                logger.error(
                    "module_task_failed",
                    task_id=module_task.id,
                    target=module_task.target,
                    error=str(e)
                )
                result.errors.append({
                    "task_id": module_task.id,
                    "target": module_task.target,
                    "error": str(e),
                    "tier": "module"
                })

    async def _process_module_task(
        self,
        module_task: Task,
        project_dir: Path,
        subsystem_name: str,
        result: OrchestrationResult,
        context: Dict[str, Any]
    ):
        """Process a module task through tiers 3-4"""

        logger.info(
            "tier3_starting",
            tier="module",
            task_id=module_task.id,
            target=module_task.target
        )

        # ================================================================
        # TIER 3: Module → Function/Class Tasks
        # ================================================================

        # Detect existing classes/functions in this module
        module_file = project_dir / subsystem_name / module_task.target
        existing_classes, existing_functions = self._detect_code_elements(module_file)

        code_tasks = await self.module_decomposer.decompose(
            task=module_task,
            existing_classes=existing_classes,
            existing_functions=existing_functions,
            context=context
        )

        logger.info(
            "tier3_complete",
            code_tasks=len(code_tasks),
            targets=[t.target for t in code_tasks]
        )

        # ================================================================
        # TIER 4: Generate code for each function/class task
        # ================================================================

        for code_task in code_tasks:
            try:
                await self._process_code_task(
                    code_task=code_task,
                    module_file=module_file,
                    result=result,
                    context=context
                )

            except Exception as e:
                logger.error(
                    "code_task_failed",
                    task_id=code_task.id,
                    target=code_task.target,
                    error=str(e)
                )
                result.errors.append({
                    "task_id": code_task.id,
                    "target": code_task.target,
                    "error": str(e),
                    "tier": "code"
                })

    async def _process_code_task(
        self,
        code_task: Task,
        module_file: Path,
        result: OrchestrationResult,
        context: Dict[str, Any]
    ):
        """Generate and write code for a function/class task"""

        logger.info(
            "tier4_starting",
            tier="code",
            task_id=code_task.id,
            target=code_task.target,
            scope=code_task.scope
        )

        # ================================================================
        # TIER 4: Generate Code (with Code Graph Context - Phase 4)
        # ================================================================

        # Enrich context with code graph information if available
        if "code_graph" in context and context["code_graph"]:
            code_graph = context["code_graph"]

            # Try to extract function ID from task target
            # Format: "module.py::function_name" or "module.py::Class::method"
            function_id = None
            if "::" in code_task.target:
                # Convert file path to module path for graph lookup
                parts = code_task.target.split("::")
                if len(parts) >= 2:
                    # Build function ID for graph lookup
                    module_part = parts[0].replace("/", "/").replace(".py", "")
                    func_part = "::".join(parts[1:])
                    function_id = f"{module_part}::{func_part}"

            # Get rich context if we found the function
            if function_id:
                rich_context = self.code_graph_analyzer.get_context_for_function(
                    function_id=function_id,
                    graph=code_graph,
                    max_depth=2
                )

                if rich_context:
                    # Add to task context
                    if not hasattr(code_task, 'context') or code_task.context is None:
                        code_task.context = {}

                    code_task.context["rich_context"] = rich_context

                    logger.info(
                        "code_graph_context_added",
                        function=function_id,
                        callers=len(rich_context.get("callers", [])),
                        callees=len(rich_context.get("callees", [])),
                        related_classes=len(rich_context.get("related_classes", []))
                    )

        code_result = await self.function_planner.generate_implementation(code_task)

        code = code_result.get("code", "")
        review_metadata = code_result.get("_review_metadata", {})

        # Track review metrics
        if review_metadata:
            result.total_review_iterations += review_metadata.get("iterations", 0)
            final_score = review_metadata.get("final_score", 0)
            if final_score > 0:
                # Running average
                total_scores = result.avg_review_score * (result.files_created + result.files_modified)
                result.avg_review_score = (total_scores + final_score) / (result.files_created + result.files_modified + 1)

        logger.info(
            "tier4_complete",
            code_length=len(code),
            review_score=review_metadata.get("final_score", 0) if review_metadata else None,
            review_iterations=review_metadata.get("iterations", 0) if review_metadata else None
        )

        # ================================================================
        # TIER 4.5: Linting & Code Quality (Phase 6)
        # ================================================================
        if self.linting_agent:
            logger.info("tier4.5_starting", tier="linting")

            try:
                lint_result = await self.linting_agent.lint_and_fix(
                    code=code,
                    filename=module_file.name,
                    context=context
                )

                # Use linted code instead of original
                code = lint_result.fixed_code

                # Track linting statistics
                result.total_lint_issues += lint_result.total_issues
                result.lint_auto_fixed += lint_result.auto_fixed
                result.lint_llm_fixed += lint_result.llm_fixed
                result.lint_issues_fixed += (lint_result.auto_fixed + lint_result.llm_fixed)

                logger.info(
                    "tier4.5_complete",
                    success=lint_result.success,
                    issues_found=lint_result.total_issues,
                    auto_fixed=lint_result.auto_fixed,
                    llm_fixed=lint_result.llm_fixed,
                    unfixed=lint_result.unfixed
                )

            except Exception as e:
                logger.warning("linting_failed", error=str(e))
                # Continue with original code if linting fails

        # ================================================================
        # TIER 5: Write to File
        # ================================================================

        await self._write_code_to_file(
            file_path=module_file,
            code=code,
            task=code_task,
            result=result
        )

    async def _write_code_to_file(
        self,
        file_path: Path,
        code: str,
        task: Task,
        result: OrchestrationResult
    ):
        """Write generated code to file with backup"""

        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file exists
            file_exists = file_path.exists()
            if file_exists and self.create_backups:
                backup_path = file_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
                backup_path.write_text(file_path.read_text())
                logger.info("backup_created", original=str(file_path), backup=str(backup_path))

            # Write code
            if task.scope == "FUNCTION" and file_exists:
                # Append function to existing file
                existing_code = file_path.read_text()
                new_code = existing_code + "\n\n" + code
                file_path.write_text(new_code)
                result.files_modified += 1
                logger.info("file_modified", path=str(file_path), code_length=len(code))
            else:
                # Write new file or overwrite
                file_path.write_text(code)
                if file_exists:
                    result.files_modified += 1
                    logger.info("file_overwritten", path=str(file_path), code_length=len(code))
                else:
                    result.files_created += 1
                    logger.info("file_created", path=str(file_path), code_length=len(code))

            result.files_written.append(file_path)

        except Exception as e:
            logger.error("file_write_failed", path=str(file_path), error=str(e))
            result.files_failed += 1
            raise

    def _detect_subsystems(self, project_dir: Path) -> List[str]:
        """Auto-detect subsystems (directories) in project"""
        if not project_dir.exists():
            return ["src"]

        subsystems = []
        for item in project_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
                subsystems.append(item.name)

        return subsystems if subsystems else ["src"]

    def _detect_modules(self, subsystem_dir: Path) -> List[str]:
        """Detect existing Python modules in a subsystem"""
        if not subsystem_dir.exists():
            return []

        modules = []
        for item in subsystem_dir.rglob("*.py"):
            if not item.name.startswith('__'):
                rel_path = item.relative_to(subsystem_dir)
                modules.append(str(rel_path))

        return modules

    def _detect_code_elements(self, module_file: Path) -> tuple[List[str], List[str]]:
        """Detect existing classes and functions in a module file"""
        if not module_file.exists():
            return [], []

        try:
            content = module_file.read_text()

            # Simple regex-based detection
            classes = []
            functions = []

            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('class '):
                    class_name = stripped.split('class ')[1].split('(')[0].split(':')[0].strip()
                    classes.append(class_name)
                elif stripped.startswith('def '):
                    func_name = stripped.split('def ')[1].split('(')[0].strip()
                    functions.append(func_name)

            return classes, functions

        except Exception as e:
            logger.warning("code_detection_failed", file=str(module_file), error=str(e))
            return [], []

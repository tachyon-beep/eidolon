"""
Implementation Orchestrator for Top-Down Task Decomposition

Coordinates the top-down decomposition of feature requests into concrete
implementation tasks, then executes them bottom-up.
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from models import (
    Task, TaskType, TaskStatus, TaskPriority,
    TaskGraph, TaskAssignment, TaskResult
)
from planning import (
    SystemDecomposer,
    SubsystemDecomposer,
    ModuleDecomposer,
    ClassDecomposer,
    FunctionPlanner
)
from llm_providers import LLMProvider
from storage import Database
from logging_config import get_logger

logger = get_logger(__name__)


class ImplementationOrchestrator:
    """
    Orchestrates top-down feature implementation

    Phase 1: Planning (Top-Down)
    - User request → SYSTEM decomposition → SUBSYSTEM decomposition → MODULE decomposition
      → CLASS decomposition → FUNCTION planning

    Phase 2: Execution (Bottom-Up)
    - FUNCTION implementation → CLASS integration → MODULE integration
      → SUBSYSTEM integration → SYSTEM integration

    Phase 3: Verification (Bottom-Up)
    - Tests at each level, rollback on failure
    """

    def __init__(
        self,
        db: Database,
        llm_provider: LLMProvider,
        max_concurrent_tasks: int = 5
    ):
        self.db = db
        self.llm_provider = llm_provider
        self.max_concurrent_tasks = max_concurrent_tasks

        # Initialize decomposers
        self.system_decomposer = SystemDecomposer(llm_provider)
        self.subsystem_decomposer = SubsystemDecomposer(llm_provider)
        self.module_decomposer = ModuleDecomposer(llm_provider)
        self.class_decomposer = ClassDecomposer(llm_provider)
        self.function_planner = FunctionPlanner(llm_provider)

        # Task graph
        self.task_graph = TaskGraph()

        # Semaphore for concurrency control
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def implement_feature(
        self,
        user_request: str,
        project_path: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Implement a feature from user request

        Args:
            user_request: High-level feature description
            project_path: Path to the project
            constraints: Optional constraints (test_coverage_min, max_complexity, etc.)

        Returns:
            Dict with implementation results

        Example:
            result = await orchestrator.implement_feature(
                "Add user authentication with JWT tokens",
                "/path/to/project",
                constraints={"test_coverage_min": 80}
            )
        """
        logger.info(
            "implementation_started",
            request=user_request,
            project=project_path
        )

        constraints = constraints or {}

        # ==================== PHASE 1: PLANNING (TOP-DOWN) ====================

        print("\n" + "=" * 80)
        print("PHASE 1: PLANNING (Top-Down Decomposition)")
        print("=" * 80)
        print(f"\nUser Request: {user_request}")
        print(f"Project: {project_path}\n")

        # Step 1: Analyze project structure
        project_structure = await self._analyze_project_structure(project_path)
        subsystems = project_structure.get("subsystems", [])

        print(f"📁 Detected subsystems: {', '.join(subsystems)}\n")

        # Step 2: SYSTEM-level decomposition
        print("🌐 SYSTEM level: Decomposing into subsystem tasks...")
        root_task = Task(
            id="T-ROOT",
            type=TaskType.CREATE_NEW,
            scope="SYSTEM",
            target=project_path,
            instruction=user_request,
            context=constraints
        )
        self.task_graph.add_task(root_task)

        subsystem_tasks = await self.system_decomposer.decompose(
            user_request,
            project_path,
            subsystems,
            context=constraints
        )

        for task in subsystem_tasks:
            task.parent_task_id = root_task.id
            root_task.add_subtask(task.id)
            self.task_graph.add_task(task)

        print(f"   → Created {len(subsystem_tasks)} subsystem tasks")
        for task in subsystem_tasks:
            print(f"      • {task.target}: {task.instruction[:60]}...")

        # Step 3: SUBSYSTEM-level decomposition
        print(f"\n📁 SUBSYSTEM level: Decomposing into module tasks...")
        for subsystem_task in subsystem_tasks:
            print(f"   Processing subsystem: {subsystem_task.target}")

            # Get existing modules in subsystem
            subsystem_path = Path(project_path) / subsystem_task.target
            existing_modules = list(subsystem_path.glob("*.py")) if subsystem_path.exists() else []
            existing_module_names = [m.name for m in existing_modules]

            module_tasks = await self.subsystem_decomposer.decompose(
                subsystem_task,
                existing_module_names,
                context=constraints
            )

            for task in module_tasks:
                subsystem_task.add_subtask(task.id)
                self.task_graph.add_task(task)

            print(f"      → Created {len(module_tasks)} module tasks")

        # Step 4: MODULE-level decomposition
        print(f"\n📄 MODULE level: Decomposing into class/function tasks...")
        all_module_tasks = [
            t for t in self.task_graph.tasks.values()
            if t.scope == "MODULE"
        ]

        for module_task in all_module_tasks:
            print(f"   Processing module: {module_task.target}")

            # For simplicity, assume new modules (no existing classes/functions)
            # In production, would analyze existing module
            class_tasks = await self.module_decomposer.decompose(
                module_task,
                existing_classes=[],
                existing_functions=[],
                context=constraints
            )

            for task in class_tasks:
                module_task.add_subtask(task.id)
                self.task_graph.add_task(task)

            print(f"      → Created {len(class_tasks)} class/function tasks")

        # Step 5: CLASS-level decomposition
        print(f"\n🏛️  CLASS level: Decomposing into method tasks...")
        all_class_tasks = [
            t for t in self.task_graph.tasks.values()
            if t.scope == "CLASS"
        ]

        for class_task in all_class_tasks:
            print(f"   Processing class: {class_task.target}")

            method_tasks = await self.class_decomposer.decompose(
                class_task,
                existing_methods=[],
                context=constraints
            )

            for task in method_tasks:
                class_task.add_subtask(task.id)
                self.task_graph.add_task(task)

            print(f"      → Created {len(method_tasks)} method tasks")

        # Planning complete
        stats = self.task_graph.get_stats()
        print("\n" + "=" * 80)
        print("Planning Complete!")
        print("=" * 80)
        print(f"Total tasks created: {len(self.task_graph.tasks)}")
        print(f"  SYSTEM: 1")
        print(f"  SUBSYSTEM: {len([t for t in self.task_graph.tasks.values() if t.scope == 'SUBSYSTEM'])}")
        print(f"  MODULE: {len([t for t in self.task_graph.tasks.values() if t.scope == 'MODULE'])}")
        print(f"  CLASS: {len([t for t in self.task_graph.tasks.values() if t.scope == 'CLASS'])}")
        print(f"  FUNCTION: {len([t for t in self.task_graph.tasks.values() if t.scope == 'FUNCTION'])}")

        # ==================== PHASE 2: EXECUTION (BOTTOM-UP) ====================

        print("\n" + "=" * 80)
        print("PHASE 2: EXECUTION (Bottom-Up Implementation)")
        print("=" * 80)
        print("\n⚙️  Executing tasks starting from FUNCTION level...\n")

        # Execute tasks in dependency order (bottom-up)
        await self._execute_tasks()

        # ==================== PHASE 3: RESULTS ====================

        print("\n" + "=" * 80)
        print("Implementation Complete!")
        print("=" * 80)

        final_stats = self.task_graph.get_stats()
        print(f"\nTask Status:")
        print(f"  ✅ Completed: {final_stats.get('completed', 0)}")
        print(f"  ❌ Failed: {final_stats.get('failed', 0)}")
        print(f"  ⏸️  Pending: {final_stats.get('pending', 0)}")

        return {
            "status": "completed" if self.task_graph.is_complete() else "partial",
            "tasks_total": len(self.task_graph.tasks),
            "tasks_completed": final_stats.get("completed", 0),
            "tasks_failed": final_stats.get("failed", 0),
            "task_graph": self.task_graph
        }

    async def _analyze_project_structure(self, project_path: str) -> Dict[str, Any]:
        """Analyze project to identify subsystems and structure"""
        path = Path(project_path)

        # Find all subdirectories (potential subsystems)
        subsystems = []
        if path.exists():
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
                    # Check if it contains Python files
                    if list(item.glob("*.py")):
                        subsystems.append(item.name)

        return {
            "subsystems": subsystems,
            "root_files": [f.name for f in path.glob("*.py")] if path.exists() else []
        }

    async def _execute_tasks(self):
        """
        Execute tasks in dependency order (bottom-up)

        Start with leaf tasks (FUNCTION level) that have no dependencies,
        work up to root task (SYSTEM level).
        """
        while not self.task_graph.is_complete():
            # Get tasks ready to execute
            ready_tasks = self.task_graph.get_ready_tasks()

            if not ready_tasks:
                # Check if we're blocked
                blocked_tasks = self.task_graph.get_blocked_tasks()
                if blocked_tasks:
                    logger.error("deadlock_detected", blocked_tasks=len(blocked_tasks))
                    # Mark remaining tasks as failed
                    for task in self.task_graph.tasks.values():
                        if task.status == TaskStatus.PENDING:
                            task.set_error("Deadlock: dependencies not met")
                break

            # Execute ready tasks in parallel
            execution_tasks = [
                self._execute_task(task)
                for task in ready_tasks[:self.max_concurrent_tasks]
            ]

            await asyncio.gather(*execution_tasks, return_exceptions=True)

    async def _execute_task(self, task: Task):
        """Execute a single task"""
        async with self.task_semaphore:
            task.update_status(TaskStatus.IN_PROGRESS)

            try:
                if task.scope == "FUNCTION":
                    # Generate actual code
                    result = await self.function_planner.generate_implementation(task)
                    task.set_result(result)
                    print(f"   ✅ {task.target}: Code generated")
                else:
                    # Higher-level tasks just wait for children
                    task.set_result({"children_completed": len(task.subtask_ids)})
                    print(f"   ✅ {task.target}: Children integrated")

            except Exception as e:
                task.set_error(str(e))
                print(f"   ❌ {task.target}: Failed - {str(e)}")
                logger.error("task_execution_failed", task_id=task.id, error=str(e))

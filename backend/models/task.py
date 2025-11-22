"""
Task models for top-down decomposition system

Represents tasks that flow from SYSTEM down to FUNCTION level,
with results flowing back up.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Type of task to perform"""
    CREATE_NEW = "create_new"           # Create new code
    MODIFY_EXISTING = "modify_existing" # Modify existing code
    REFACTOR = "refactor"               # Improve without changing behavior
    DELETE = "delete"                   # Remove code
    FIX = "fix"                         # Fix a bug or issue
    TEST = "test"                       # Write tests


class TaskStatus(str, Enum):
    """Status of a task"""
    PENDING = "pending"           # Not started
    PLANNING = "planning"         # Decomposing into subtasks
    READY = "ready"               # Ready to execute (dependencies met)
    IN_PROGRESS = "in_progress"   # Currently executing
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"             # Failed with errors
    BLOCKED = "blocked"           # Waiting for dependencies
    CANCELLED = "cancelled"       # Cancelled by user or system


class TaskPriority(int, Enum):
    """Priority of a task"""
    CRITICAL = 0  # Must be done first
    HIGH = 1      # Important
    MEDIUM = 2    # Normal priority
    LOW = 3       # Can be delayed
    OPTIONAL = 4  # Nice to have


class Task(BaseModel):
    """
    Represents a task in the decomposition hierarchy

    A task flows down from parent to child agents for decomposition,
    and results flow back up after completion.
    """
    id: str = Field(..., description="Unique task ID (e.g., T-001)")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID")
    agent_id: Optional[str] = Field(None, description="Agent assigned to this task")

    # Task definition
    type: TaskType = Field(..., description="Type of task")
    scope: str = Field(..., description="Agent scope (SYSTEM, SUBSYSTEM, MODULE, CLASS, FUNCTION)")
    target: str = Field(..., description="What to modify (file path, class name, function name)")
    instruction: str = Field(..., description="What to do")

    # Context and constraints
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    constraints: List[str] = Field(default_factory=list, description="Constraints to follow")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this depends on")

    # Status and priority
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)

    # Subtasks (for decomposition)
    subtask_ids: List[str] = Field(default_factory=list, description="Child task IDs")

    # Result tracking
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_complexity: Optional[str] = Field(None, description="low/medium/high")

    class Config:
        use_enum_values = True

    def update_status(self, new_status: TaskStatus):
        """Update task status with timestamp tracking"""
        self.status = new_status
        if new_status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.completed_at = datetime.utcnow()

    def add_subtask(self, subtask_id: str):
        """Add a subtask"""
        if subtask_id not in self.subtask_ids:
            self.subtask_ids.append(subtask_id)

    def set_result(self, result: Dict[str, Any]):
        """Set task result"""
        self.result = result
        self.update_status(TaskStatus.COMPLETED)

    def set_error(self, error: str):
        """Set task error"""
        self.error = error
        self.update_status(TaskStatus.FAILED)


class TaskAssignment(BaseModel):
    """
    Message sent from parent agent to child agent assigning a task
    """
    task: Task
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """
    Message sent from child agent to parent agent reporting task completion
    """
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Metrics
    subtasks_completed: List[str] = Field(default_factory=list)
    subtasks_failed: List[str] = Field(default_factory=list)
    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    files_deleted: List[str] = Field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    coverage: Optional[float] = None

    # Completion time
    duration_seconds: Optional[float] = None

    # Issues encountered
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class TaskGraph(BaseModel):
    """
    Directed Acyclic Graph of tasks with dependency tracking

    Manages task execution order based on dependencies.
    """
    tasks: Dict[str, Task] = Field(default_factory=dict, description="Task ID -> Task")

    def add_task(self, task: Task):
        """Add a task to the graph"""
        self.tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (all dependencies met)"""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_met = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )

            if deps_met:
                ready.append(task)

        # Sort by priority
        ready.sort(key=lambda t: t.priority.value)
        return ready

    def get_blocked_tasks(self) -> List[Task]:
        """Get tasks that are blocked by dependencies"""
        blocked = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if any dependencies are not completed
            has_incomplete_deps = any(
                self.tasks[dep_id].status != TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )

            if has_incomplete_deps:
                blocked.append(task)

        return blocked

    def get_subtasks(self, task_id: str) -> List[Task]:
        """Get all subtasks of a task"""
        task = self.get_task(task_id)
        if not task:
            return []

        return [
            self.tasks[subtask_id]
            for subtask_id in task.subtask_ids
            if subtask_id in self.tasks
        ]

    def is_complete(self) -> bool:
        """Check if all tasks are complete"""
        return all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
            for task in self.tasks.values()
        )

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about task statuses"""
        stats = {status.value: 0 for status in TaskStatus}
        for task in self.tasks.values():
            stats[task.status] += 1
        return stats

"""
Task decomposition strategies for each agent tier

Each decomposer uses AI to break down a high-level task into
concrete subtasks for the next tier down.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from models import Task, TaskType, TaskStatus, TaskPriority
from llm_providers import LLMProvider
from logging_config import get_logger

logger = get_logger(__name__)


class SystemDecomposer:
    """
    Decomposes user requests into subsystem-level tasks

    User: "Add user authentication with JWT"
    → api subsystem: Add /login and /logout endpoints
    → services subsystem: Implement JWT authentication service
    → models subsystem: Add User model with password hashing
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def decompose(
        self,
        user_request: str,
        project_path: str,
        subsystems: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose user request into subsystem tasks

        Args:
            user_request: High-level feature request from user
            project_path: Path to project
            subsystems: List of subsystems (directories) in project
            context: Additional context

        Returns:
            List of subsystem-level tasks with dependencies
        """
        context = context or {}

        # Build prompt for AI
        prompt = f"""You are a system architect decomposing a feature request into subsystem-level tasks.

User Request: {user_request}
Project Path: {project_path}
Available Subsystems: {', '.join(subsystems)}

Your task:
1. Understand the strategic intent of the request
2. Identify which subsystems need changes
3. For each subsystem, define what needs to be done
4. Identify dependencies between subsystem tasks
5. Estimate complexity (low/medium/high)

Respond in JSON format:
{{
  "understanding": "Brief explanation of what user wants",
  "subsystem_tasks": [
    {{
      "subsystem": "subsystem_name",
      "instruction": "What this subsystem needs to do",
      "type": "create_new|modify_existing|refactor",
      "priority": "critical|high|medium|low",
      "dependencies": ["other_subsystem_names"],
      "complexity": "low|medium|high"
    }}
  ],
  "overall_complexity": "low|medium|high"
}}"""

        # Call LLM
        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.0
        )

        # Parse response (in production, use proper JSON parsing with error handling)
        import json
        try:
            plan = json.loads(response.content)
        except:
            # Fallback: create a simple task structure
            logger.warning("Failed to parse LLM response, using fallback")
            plan = {
                "understanding": user_request,
                "subsystem_tasks": [
                    {
                        "subsystem": subsystems[0] if subsystems else "root",
                        "instruction": user_request,
                        "type": "modify_existing",
                        "priority": "high",
                        "dependencies": [],
                        "complexity": "medium"
                    }
                ],
                "overall_complexity": "medium"
            }

        # Create Task objects
        tasks = []
        for i, subtask_def in enumerate(plan.get("subsystem_tasks", [])):
            task = Task(
                id=f"T-SYS-{uuid.uuid4().hex[:8]}",
                parent_task_id=None,  # Root task
                type=TaskType(subtask_def.get("type", "modify_existing")),
                scope="SUBSYSTEM",
                target=subtask_def.get("subsystem", "unknown"),
                instruction=subtask_def.get("instruction", ""),
                context={
                    "user_request": user_request,
                    "project_path": project_path,
                    **context
                },
                dependencies=[],  # Will be populated based on dependency names
                priority=self._parse_priority(subtask_def.get("priority", "medium")),
                estimated_complexity=subtask_def.get("complexity", "medium")
            )
            tasks.append(task)

        # Resolve dependencies (convert names to task IDs)
        task_by_subsystem = {t.target: t for t in tasks}
        for i, subtask_def in enumerate(plan.get("subsystem_tasks", [])):
            for dep_name in subtask_def.get("dependencies", []):
                if dep_name in task_by_subsystem:
                    tasks[i].dependencies.append(task_by_subsystem[dep_name].id)

        logger.info(
            "system_decomposition_complete",
            tasks=len(tasks),
            understanding=plan.get("understanding", "")
        )

        return tasks

    def _parse_priority(self, priority_str: str) -> TaskPriority:
        """Parse priority string to enum"""
        mapping = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
            "optional": TaskPriority.OPTIONAL
        }
        return mapping.get(priority_str.lower(), TaskPriority.MEDIUM)


class SubsystemDecomposer:
    """
    Decomposes subsystem tasks into module tasks

    Subsystem: "Implement JWT authentication service"
    → auth_service.py: Create AuthService class
    → token_service.py: Create TokenService for JWT generation
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def decompose(
        self,
        task: Task,
        existing_modules: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose subsystem task into module tasks

        Args:
            task: Subsystem-level task
            existing_modules: List of existing module files in subsystem
            context: Additional context

        Returns:
            List of module-level tasks
        """
        context = context or {}

        prompt = f"""You are decomposing a subsystem-level task into module-level changes.

Subsystem Task: {task.instruction}
Target Subsystem: {task.target}
Existing Modules: {', '.join(existing_modules) if existing_modules else 'None (new subsystem)'}

Your task:
1. Identify which modules need changes
2. Decide whether to create new modules or modify existing ones
3. Define what each module needs to do
4. Identify dependencies between modules

Respond in JSON format:
{{
  "module_tasks": [
    {{
      "module": "filename.py",
      "action": "create_new|modify_existing",
      "instruction": "What this module needs to do",
      "dependencies": ["other_module_names"],
      "complexity": "low|medium|high"
    }}
  ]
}}"""

        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1536,
            temperature=0.0
        )

        # Parse and create tasks (simplified)
        import json
        try:
            plan = json.loads(response.content)
        except:
            # Fallback: Use existing modules if available, otherwise create main.py
            if existing_modules:
                # Use first existing module (or could use all of them)
                module_name = existing_modules[0]

                # Prepend subsystem directory if not root
                if task.target != "root":
                    module_name = f"{task.target}/{module_name}"
            else:
                # No existing modules, create new one
                module_name = "main.py" if task.target == "root" else f"{task.target}/main.py"

            plan = {
                "module_tasks": [
                    {
                        "module": module_name,
                        "action": "modify_existing" if existing_modules else "create_new",
                        "instruction": task.instruction,
                        "dependencies": [],
                        "complexity": "medium"
                    }
                ]
            }

        tasks = []
        for module_def in plan.get("module_tasks", []):
            t = Task(
                id=f"T-MOD-{uuid.uuid4().hex[:8]}",
                parent_task_id=task.id,
                type=TaskType(module_def.get("action", "modify_existing")),
                scope="MODULE",
                target=module_def.get("module", "unknown.py"),
                instruction=module_def.get("instruction", ""),
                context={**task.context, **context},
                estimated_complexity=module_def.get("complexity", "medium")
            )
            tasks.append(t)

        return tasks


class ModuleDecomposer:
    """
    Decomposes module tasks into class/function tasks

    Module: "Create AuthService class"
    → AuthService class: Create class with login/verify methods
    → authenticate_user() function: Standalone helper function
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def decompose(
        self,
        task: Task,
        existing_classes: List[str],
        existing_functions: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose module task into class/function tasks

        Args:
            task: Module-level task
            existing_classes: Existing classes in module
            existing_functions: Existing functions in module
            context: Additional context

        Returns:
            List of class/function-level tasks
        """
        context = context or {}

        prompt = f"""You are decomposing a module-level task into classes and functions.

Module Task: {task.instruction}
Target Module: {task.target}
Existing Classes: {', '.join(existing_classes) if existing_classes else 'None'}
Existing Functions: {', '.join(existing_functions) if existing_functions else 'None'}

Your task:
1. Identify what classes need to be created or modified
2. Identify what standalone functions are needed
3. Define what each class/function needs to do

Respond in JSON format:
{{
  "class_tasks": [
    {{
      "class_name": "ClassName",
      "action": "create_new|modify_existing",
      "instruction": "What this class needs to do",
      "methods": ["method1", "method2"]
    }}
  ],
  "function_tasks": [
    {{
      "function_name": "function_name",
      "action": "create_new|modify_existing",
      "instruction": "What this function needs to do"
    }}
  ]
}}"""

        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1536,
            temperature=0.0
        )

        # Parse and create tasks
        import json
        import re
        try:
            plan = json.loads(response.content)
        except:
            # Fallback: Try to extract function/class names from instruction
            function_tasks = []
            class_tasks = []

            # Look for function patterns like "add multiply() function" or "create divide()"
            func_pattern = r'\b(\w+)\s*\([^)]*\)'  # Matches function_name()
            matches = re.findall(func_pattern, task.instruction)

            if matches:
                # Found function names in instruction
                for func_name in matches:
                    # Skip common words that aren't function names
                    if func_name.lower() not in ['if', 'when', 'then', 'with', 'for', 'while']:
                        function_tasks.append({
                            "function_name": func_name,
                            "action": "create_new",
                            "instruction": f"Implement {func_name} function"
                        })

            plan = {
                "class_tasks": class_tasks,
                "function_tasks": function_tasks
            }

        tasks = []

        # Create class tasks
        for class_def in plan.get("class_tasks", []):
            t = Task(
                id=f"T-CLS-{uuid.uuid4().hex[:8]}",
                parent_task_id=task.id,
                type=TaskType(class_def.get("action", "create_new")),
                scope="CLASS",
                target=f"{task.target}::{class_def.get('class_name', 'UnknownClass')}",
                instruction=class_def.get("instruction", ""),
                context={**task.context, "methods": class_def.get("methods", []), **context}
            )
            tasks.append(t)

        # Create function tasks
        for func_def in plan.get("function_tasks", []):
            t = Task(
                id=f"T-FNC-{uuid.uuid4().hex[:8]}",
                parent_task_id=task.id,
                type=TaskType(func_def.get("action", "create_new")),
                scope="FUNCTION",
                target=f"{task.target}::{func_def.get('function_name', 'unknown_function')}",
                instruction=func_def.get("instruction", ""),
                context={**task.context, **context}
            )
            tasks.append(t)

        return tasks


class ClassDecomposer:
    """
    Decomposes class tasks into method tasks

    Class: "Create AuthService with login/verify"
    → __init__() method: Initialize dependencies
    → login() method: Authenticate and generate token
    → verify_token() method: Validate JWT token
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def decompose(
        self,
        task: Task,
        existing_methods: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose class task into method tasks

        Args:
            task: Class-level task
            existing_methods: Existing methods in class
            context: Additional context

        Returns:
            List of method (function)-level tasks
        """
        context = context or {}

        # Get suggested methods from context or use defaults
        suggested_methods = task.context.get("methods", [])

        prompt = f"""You are decomposing a class-level task into methods.

Class Task: {task.instruction}
Target Class: {task.target}
Suggested Methods: {', '.join(suggested_methods) if suggested_methods else 'None'}
Existing Methods: {', '.join(existing_methods) if existing_methods else 'None'}

Your task:
1. Define what methods are needed
2. Specify method signatures
3. Define what each method needs to do

Respond in JSON format:
{{
  "methods": [
    {{
      "name": "method_name",
      "signature": "def method_name(self, param1: type) -> return_type",
      "instruction": "What this method needs to do",
      "action": "create_new|modify_existing"
    }}
  ]
}}"""

        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1536,
            temperature=0.0
        )

        # Parse and create tasks
        import json
        try:
            plan = json.loads(response.content)
        except:
            plan = {"methods": []}

        tasks = []
        for method_def in plan.get("methods", []):
            t = Task(
                id=f"T-MTH-{uuid.uuid4().hex[:8]}",
                parent_task_id=task.id,
                type=TaskType(method_def.get("action", "create_new")),
                scope="FUNCTION",
                target=f"{task.target}.{method_def.get('name', 'unknown_method')}",
                instruction=method_def.get("instruction", ""),
                context={
                    **task.context,
                    "signature": method_def.get("signature", ""),
                    **context
                }
            )
            tasks.append(t)

        return tasks


class FunctionPlanner:
    """
    Plans function implementation (leaf node - generates actual code)

    Function: "Authenticate user and return JWT token"
    → Generates actual Python code
    → Generates unit tests
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def generate_implementation(
        self,
        task: Task,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate actual code implementation for function

        Args:
            task: Function-level task
            context: Additional context (existing code, dependencies, etc.)

        Returns:
            Dict with 'code', 'tests', 'explanation'
        """
        context = context or {}

        signature = task.context.get("signature", "")
        module_path = task.target.split("::")[0]

        prompt = f"""You are generating Python code for a function.

Task: {task.instruction}
Function: {task.target}
{"Signature: " + signature if signature else ""}

Your task:
1. Generate the complete function implementation
2. Include proper error handling
3. Add docstring
4. Follow best practices

Respond in JSON format:
{{
  "code": "def function_name(...):\\n    '''Docstring'''\\n    # implementation",
  "explanation": "Brief explanation of the implementation"
}}"""

        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.0
        )

        # Parse response
        import json
        try:
            result = json.loads(response.content)
        except:
            result = {
                "code": f"def placeholder():\n    '''TODO: {task.instruction}'''\n    pass",
                "explanation": "Placeholder implementation"
            }

        return result

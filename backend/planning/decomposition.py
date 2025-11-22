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

# Phase 2.5 improvements: structured outputs and role-based prompting
from planning.agent_selector import IntelligentAgentSelector, AgentRole
from planning.prompt_templates import PromptTemplateLibrary
from planning.improved_decomposition import extract_json_from_response

logger = get_logger(__name__)


class SystemDecomposer:
    """
    Decomposes user requests into subsystem-level tasks

    User: "Add user authentication with JWT"
    → api subsystem: Add /login and /logout endpoints
    → services subsystem: Implement JWT authentication service
    → models subsystem: Add User model with password hashing
    """

    def __init__(self, llm_provider: LLMProvider, use_intelligent_selection: bool = True):
        """
        Initialize SystemDecomposer with Phase 2.5 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

    async def decompose(
        self,
        user_request: str,
        project_path: str,
        subsystems: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose user request into subsystem tasks using Phase 2.5 improvements

        Args:
            user_request: High-level feature request from user
            project_path: Path to project
            subsystems: List of subsystems (directories) in project
            context: Additional context

        Returns:
            List of subsystem-level tasks with dependencies
        """
        context = context or {}

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=user_request,
                    project_context={
                        "subsystems": subsystems,
                        "project_path": project_path
                    },
                    use_llm=True  # Use LLM-powered selection for better accuracy
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    reasoning=selection.get("reasoning", "")
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_system_decomposer_prompt(
            user_request=user_request,
            project_path=project_path,
            subsystems=subsystems,
            role=agent_role
        )

        # Phase 2.5 Step 3: Call LLM with structured output support
        try:
            # Try to use JSON mode if supported (OpenAI, Anthropic, some providers)
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=4096,
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported: {e}, using regular mode")
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=4096,
                temperature=0.0
            )

        # Phase 2.5 Step 4: Extract JSON with improved parsing
        plan = extract_json_from_response(response.content)

        if not plan or "subsystem_tasks" not in plan:
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

    def __init__(self, llm_provider: LLMProvider, use_intelligent_selection: bool = True):
        """
        Initialize SubsystemDecomposer with Phase 2.5 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

    async def decompose(
        self,
        task: Task,
        existing_modules: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose subsystem task into module tasks using Phase 2.5 improvements

        Args:
            task: Subsystem-level task
            existing_modules: List of existing module files in subsystem
            context: Additional context

        Returns:
            List of module-level tasks
        """
        context = context or {}

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "subsystem": task.target,
                        "existing_modules": existing_modules
                    },
                    use_llm=True
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    subsystem=task.target
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_subsystem_decomposer_prompt(
            subsystem_task=task.instruction,
            target_subsystem=task.target,
            existing_modules=existing_modules,
            role=agent_role
        )

        # Phase 2.5 Step 3: Call LLM with structured output support
        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported: {e}, using regular mode")
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0
            )

        # Phase 2.5 Step 4: Extract JSON with improved parsing
        plan = extract_json_from_response(response.content)

        if not plan or "module_tasks" not in plan:
            # Fallback: Use existing modules if available, otherwise create main.py
            logger.warning("Failed to parse LLM response, using fallback")
            if existing_modules:
                module_name = existing_modules[0]
                if task.target != "root":
                    module_name = f"{task.target}/{module_name}"
            else:
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

        # Create Task objects
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

        logger.info(
            "subsystem_decomposition_complete",
            subsystem=task.target,
            modules=len(tasks)
        )

        return tasks


class ModuleDecomposer:
    """
    Decomposes module tasks into class/function tasks

    Module: "Create AuthService class"
    → AuthService class: Create class with login/verify methods
    → authenticate_user() function: Standalone helper function
    """

    def __init__(self, llm_provider: LLMProvider, use_intelligent_selection: bool = True):
        """
        Initialize ModuleDecomposer with Phase 2.5 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

    async def decompose(
        self,
        task: Task,
        existing_classes: List[str],
        existing_functions: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose module task into class/function tasks using Phase 2.5 improvements

        Args:
            task: Module-level task
            existing_classes: Existing classes in module
            existing_functions: Existing functions in module
            context: Additional context

        Returns:
            List of class/function-level tasks
        """
        context = context or {}

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "module": task.target,
                        "existing_classes": existing_classes,
                        "existing_functions": existing_functions
                    },
                    use_llm=True
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    module=task.target
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_module_decomposer_prompt(
            module_task=task.instruction,
            target_module=task.target,
            existing_classes=existing_classes,
            existing_functions=existing_functions,
            role=agent_role
        )

        # Phase 2.5 Step 3: Call LLM with structured output support
        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported: {e}, using regular mode")
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0
            )

        # Phase 2.5 Step 4: Extract JSON with improved parsing
        plan = extract_json_from_response(response.content)

        if not plan or ("class_tasks" not in plan and "function_tasks" not in plan):
            # Fallback: Try to extract function/class names from instruction
            logger.warning("Failed to parse LLM response, using fallback")
            function_tasks = []
            class_tasks = []

            import re
            # Look for function patterns like "add multiply() function" or "create divide()"
            func_pattern = r'\b(\w+)\s*\([^)]*\)'  # Matches function_name()
            matches = re.findall(func_pattern, task.instruction)

            if matches:
                for func_name in matches:
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

        # Create Task objects
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

        logger.info(
            "module_decomposition_complete",
            module=task.target,
            classes=len(plan.get("class_tasks", [])),
            functions=len(plan.get("function_tasks", []))
        )

        return tasks


class ClassDecomposer:
    """
    Decomposes class tasks into method tasks

    Class: "Create AuthService with login/verify"
    → __init__() method: Initialize dependencies
    → login() method: Authenticate and generate token
    → verify_token() method: Validate JWT token
    """

    def __init__(self, llm_provider: LLMProvider, use_intelligent_selection: bool = True):
        """
        Initialize ClassDecomposer with Phase 2.5 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

    async def decompose(
        self,
        task: Task,
        existing_methods: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose class task into method tasks using Phase 2.5 improvements

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

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "class": task.target,
                        "suggested_methods": suggested_methods,
                        "existing_methods": existing_methods
                    },
                    use_llm=True
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    class_name=task.target
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_class_decomposer_prompt(
            class_task=task.instruction,
            target_class=task.target,
            suggested_methods=suggested_methods,
            existing_methods=existing_methods,
            role=agent_role
        )

        # Phase 2.5 Step 3: Call LLM with structured output support
        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported: {e}, using regular mode")
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0
            )

        # Phase 2.5 Step 4: Extract JSON with improved parsing
        plan = extract_json_from_response(response.content)

        if not plan or "methods" not in plan:
            logger.warning("Failed to parse LLM response, using fallback")
            plan = {"methods": []}

        # Create Task objects
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

        logger.info(
            "class_decomposition_complete",
            class_name=task.target,
            methods=len(tasks)
        )

        return tasks


class FunctionPlanner:
    """
    Plans function implementation (leaf node - generates actual code)

    Function: "Authenticate user and return JWT token"
    → Generates actual Python code
    → Generates unit tests
    """

    def __init__(self, llm_provider: LLMProvider, use_intelligent_selection: bool = True):
        """
        Initialize FunctionPlanner with Phase 2.5 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

    async def generate_implementation(
        self,
        task: Task,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate actual code implementation for function using Phase 2.5 improvements

        Args:
            task: Function-level task
            context: Additional context (existing code, dependencies, etc.)

        Returns:
            Dict with 'code', 'tests', 'explanation'
        """
        context = context or {}

        signature = task.context.get("signature", "")
        module_path = task.target.split("::")[0]
        function_name = task.target.split("::")[-1]

        # Phase 2.5 Step 1: Intelligent agent role selection
        # For code generation, default to IMPLEMENTATION role
        agent_role = AgentRole.IMPLEMENTATION
        if self.agent_selector:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "function": task.target,
                        "signature": signature,
                        "module": module_path
                    },
                    use_llm=False  # Use heuristic for speed (code gen is always IMPLEMENTATION)
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    function=function_name
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default IMPLEMENTATION role")
                agent_role = AgentRole.IMPLEMENTATION

        # Phase 2.5 Step 2: Get role-based prompts
        # Build module context string
        module_context = f"Module: {module_path}\n"
        if signature:
            module_context += f"Signature: {signature}\n"
        module_context += f"Task: {task.instruction}"

        prompts = PromptTemplateLibrary.get_function_generator_prompt(
            function_name=function_name,
            instruction=task.instruction,
            module_context=module_context,
            role=agent_role
        )

        # Phase 2.5 Step 3: Call LLM with structured output support
        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=3072,  # More tokens for code generation
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported: {e}, using regular mode")
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=3072,
                temperature=0.0
            )

        # Phase 2.5 Step 4: Extract JSON or code from response
        # For code generation, the response might be direct code OR JSON
        result = None

        # Try extracting JSON first
        plan = extract_json_from_response(response.content)
        if plan and "code" in plan:
            result = plan
        else:
            # If no JSON, treat entire response as code
            logger.warning("No JSON in response, treating as direct code")
            result = {
                "code": response.content.strip(),
                "explanation": "Generated implementation"
            }

        # Validate we got some code
        if not result or not result.get("code"):
            logger.error("Failed to generate code, using placeholder")
            result = {
                "code": f"def {function_name}():\n    '''TODO: {task.instruction}'''\n    pass",
                "explanation": "Placeholder implementation (code generation failed)"
            }

        logger.info(
            "function_implementation_complete",
            function=function_name,
            code_length=len(result.get("code", ""))
        )

        return result
